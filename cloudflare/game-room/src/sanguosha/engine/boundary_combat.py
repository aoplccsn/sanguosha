"""Mobile identity boundary combat skills on ordinary resolution frames."""

from dataclasses import dataclass

from sanguosha.model.enums import CardCategory, EquipmentSlot, Phase
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .events import (CardMovedEvent, CardResolvedEvent, CardUsedEvent, Event,
                     PhaseEndedEvent, PhaseStartedEvent, TurnStartedEvent,
                     phase_rule_discards)
from .requests import PendingRequest, RequestType


SLASH_IDS = ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash')
POJUN_PREFIX = 'committed:jie_pojun:'


def hand(state, player_id):
    return state.cards_in(ZoneRef(ZoneType.HAND, player_id))


def equipment(state, player_id):
    return tuple(cid for ref, zone in state.zones.items()
                 if ref.player_id == player_id and ref.zone_type is ZoneType.EQUIPMENT
                 for cid in zone.card_ids)


def owned_cards(state, player_id):
    return (*hand(state, player_id), *equipment(state, player_id))


def locate(state, card_id):
    return next((ref for ref, zone in state.zones.items() if card_id in zone.card_ids), None)


def slash_ignores_distance(state, player_id, skills):
    return bool(skills is not None and skills.has(state, player_id, 'jie_paoxiao')
                and state.current_player_id == player_id and state.current_phase is Phase.PLAY
                and state.players[player_id].marks.get('jie_paoxiao_slash', 0))


def damage_bonus(state, action, skills):
    source, target = action.source_id, action.target_id
    if (source is None or source == target or skills is None
            or not skills.has(state, source, 'jie_pojun')
            or getattr(action, 'propagated', False)):
        return 0
    from .damage_cards import damage_definition
    if damage_definition(state, action) not in SLASH_IDS and getattr(action, 'card_kind', '') != 'slash':
        return 0
    return int(len(hand(state, target)) <= len(hand(state, source))
               and len(equipment(state, target)) <= len(equipment(state, source)))


def slash_target_reaction(state, frame, skills):
    """Direct strike compatibility; normal uses were offered by CardUsedEvent."""
    action = frame.action
    if frame.step_index != 0 or frame.local.get('jie_pojun_target_checked'):
        return None
    frame.local['jie_pojun_target_checked'] = True
    virtual = getattr(action, 'virtual_card', None)
    materials = virtual.material_ids if virtual is not None else (action.card_id,)
    already_offered = False
    for record in state.metadata.get('t22_slash_uses', {}).values():
        if (record['source'] != action.source_id
                or not set(record['materials']).intersection(materials)):
            continue
        already_offered |= action.target_id in record['targets']
        if action.target_id not in record['targets']:
            record['targets'].append(action.target_id)
    if (already_offered or skills is None
            or not skills.has(state, action.source_id, 'jie_pojun')):
        return None
    if state.players[action.target_id].is_alive:
        return StepResult.push(BoundaryCombatAction(action.action_id + ':jie_pojun',
            action.source_id, 'jie_pojun', action.target_id))
    return None


def note_damage(state, action):
    """Call only after actual Slash damage, never for lost HP or prevention."""
    from .damage_cards import damage_definition
    if damage_definition(state, action) not in SLASH_IDS and getattr(action, 'card_kind', '') != 'slash':
        return
    virtual = getattr(action, 'virtual_card', None)
    materials = (getattr(action, 'material_card_ids', ())
                 or (virtual.material_ids if virtual is not None else ())
                 or ((action.card_id,) if action.card_id else ()))
    for record in state.metadata.get('t22_slash_uses', {}).values():
        if record['source'] == action.source_id and set(record['materials']).intersection(materials):
            if action.target_id not in record['damaged']:
                record['damaged'].append(action.target_id)


def clear_turn(state, moves, actor=None, action_id='t22-turn-cleanup'):
    """All Pojun removals expire with the containing turn, even after death."""
    for index, ref in enumerate(tuple(state.zones)):
        if ref.zone_type is not ZoneType.SPECIAL or not ref.special_key.startswith(POJUN_PREFIX):
            continue
        cards = state.cards_in(ref)
        if not cards:
            continue
        target = ref.player_id
        destination = (ZoneRef(ZoneType.HAND, target)
                       if state.players[target].is_alive else ZoneRef(ZoneType.DISCARD_PILE))
        moves.move(state, CardMove(action_id + ':pojun:' + str(index), cards, ref,
            destination, CardMoveReason.SYSTEM, actor, action_id))
        for cid in cards:
            state.metadata.get('revealed_committed', {}).pop(cid, None)
    state.metadata.pop('t22_slash_uses', None)
    for player in state.players.values():
        player.marks.pop('jie_paoxiao_slash', None)


@dataclass(frozen=True, slots=True)
class BoundaryCombatAction(Action):
    player_id: str
    skill: str
    target_id: str | None = None
    card_ids: tuple[str, ...] = ()
    event_id: str = ''


class BoundaryCombatHandler:
    def __init__(self, skills, moves, definitions):
        self.skills, self.moves, self.definitions = skills, moves, definitions

    def ask(self, frame, kind, prompt, **kwargs):
        action = frame.action
        return StepResult.ask(PendingRequest(
            action.action_id + ':request:' + str(frame.step_index) + ':' + str(frame.cursor),
            action.player_id, kind, prompt, action.action_id, frame.frame_id, **kwargs))

    def step(self, state, frame):
        action = frame.action
        if state.status is GameStatus.FINISHED or not state.players[action.player_id].is_alive:
            return StepResult.complete()
        if action.skill == 'collect_tishen':
            return self.collect_tishen(state, frame)
        if not self.skills.has(state, action.player_id, action.skill):
            return StepResult.complete()
        if action.skill == 'jie_pojun':
            return self.pojun(state, frame)
        if action.skill == 'jie_xuanfeng':
            return self.xuanfeng(state, frame)
        if action.skill == 'jie_tishen':
            return self.tishen(state, frame)
        raise InvalidCardUse('unknown boundary combat skill')

    def move_batch(self, state, groups, destination, reason, action, label):
        """A simultaneous loss across equipment slots publishes one departure fact."""
        departed = {}
        for index, (ref, cards) in enumerate(groups.items()):
            self.moves.move(state, CardMove(action.action_id + ':' + label + ':' + str(index),
                tuple(cards), ref, destination, reason, action.player_id,
                'equipment-departure:' + action.action_id))
            if ref.zone_type is ZoneType.EQUIPMENT:
                departed[ref.player_id] = departed.get(ref.player_id, 0) + len(cards)
        for owner, count in departed.items():
            self.moves.recorder.record(Event(action.action_id + ':' + label + ':equipment-left:' + owner,
                'equipment_departure_batch', owner, metadata={'count': count}))

    def pojun(self, state, frame):
        action = frame.action
        target = action.target_id
        if target is None or target == action.player_id or not state.players[target].is_alive:
            return StepResult.complete()
        available = owned_cards(state, target)
        maximum = min(max(0, state.players[target].hp), len(available))
        if frame.step_index == 0:
            if not maximum:
                return StepResult.complete()
            frame.step_index = 1
            return self.ask(frame, RequestType.YES_NO, '【破军】是否暂时扣置目标的牌？',
                            subject_player_id=target)
        if frame.step_index == 1:
            wanted, frame.decision = frame.decision is True, None
            if not wanted or not maximum:
                return StepResult.complete()
            frame.step_index = 2
            return self.ask(frame, RequestType.CHOOSE_CARDS, '【破军】选择至多等于目标体力值的牌扣置',
                            eligible_card_ids=available, min_count=0, max_count=maximum,
                            subject_player_id=target)
        selected, frame.decision = tuple(frame.decision), None
        if len(selected) > maximum or not set(selected).issubset(available):
            raise InvalidCardUse('破军选择的牌或数量已不合法')
        if selected:
            pile = ZoneRef(ZoneType.SPECIAL, target,
                special_key=POJUN_PREFIX + str(state.turn_number) + ':' + action.player_id)
            groups = {}
            for cid in selected:
                ref = locate(state, cid)
                groups.setdefault(ref, []).append(cid)
                if ref.zone_type is ZoneType.EQUIPMENT:
                    state.metadata.setdefault('revealed_committed', {})[cid] = True
            self.move_batch(state, groups, pile, CardMoveReason.SYSTEM, action, 'store')
            self.moves.recorder.record(Event(action.action_id + ':used', 'skill_jie_pojun',
                action.player_id, (target,), {'count': len(selected)}))
        return StepResult.complete()

    def move_pairs(self, state, player_id):
        pairs = []
        others = tuple(pid for pid in state.seat_order if pid != player_id and state.players[pid].is_alive)
        for source in others:
            for cid in equipment(state, source):
                ref = locate(state, cid)
                for target in others:
                    destination = ZoneRef(ZoneType.EQUIPMENT, target, ref.equipment_slot)
                    if (target != source and ref.equipment_slot not in state.players[target].abolished_equipment_slots
                            and not state.cards_in(destination)):
                        pairs.append((cid, source, target))
        return tuple(pairs)

    def xuanfeng(self, state, frame):
        action = frame.action
        pid = action.player_id
        targets = tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive
                        and owned_cards(state, q))
        pairs = self.move_pairs(state, pid)
        if frame.step_index == 0:
            choices = (*(('discard',) if targets else ()), *(('move',) if pairs else ()), 'cancel')
            if len(choices) == 1:
                return StepResult.complete()
            frame.step_index = 1
            return self.ask(frame, RequestType.CHOOSE_OPTION, '【旋风】弃置至多两名其他角色共计两张牌，或移动他人装备',
                            choices=choices)
        if frame.step_index == 1:
            mode, frame.decision = frame.decision, None
            if mode == 'cancel':
                return StepResult.complete()
            frame.local['mode'] = mode
            if mode == 'move':
                frame.step_index = 5
                return self.ask(frame, RequestType.CHOOSE_CARD, '【旋风】选择其他角色装备区的牌移动',
                                eligible_card_ids=tuple(dict.fromkeys(pair[0] for pair in pairs)))
            frame.step_index = 2
        if frame.step_index == 2:
            allowed = targets
            chosen = frame.local.get('targets', [])
            if len(chosen) >= 2:
                allowed = tuple(q for q in targets if q in chosen)
            if frame.cursor >= 2 or not allowed:
                return StepResult.complete()
            frame.step_index = 3
            return self.ask(frame, RequestType.CHOOSE_PLAYER, '【旋风】选择弃牌目标',
                            allowed_player_ids=allowed)
        if frame.step_index == 3:
            frame.local['target'], frame.decision = frame.decision, None
            target = frame.local['target']
            if target not in targets:
                return StepResult.complete()
            frame.step_index = 4
            return self.ask(frame, RequestType.CHOOSE_CARD, '【旋风】选择弃置目标的一张牌',
                            eligible_card_ids=owned_cards(state, target), subject_player_id=target)
        if frame.step_index == 4:
            cid, frame.decision = frame.decision, None
            target = frame.local['target']
            if cid in owned_cards(state, target):
                frame.local.setdefault('targets', []).append(target)
                self.moves.move(state, CardMove(action.action_id + ':discard:' + str(frame.cursor),
                    (cid,), locate(state, cid), ZoneRef(ZoneType.DISCARD_PILE),
                    CardMoveReason.DISCARD, pid, action.action_id))
            frame.cursor += 1
            frame.step_index = 2
            return StepResult.continue_()
        if frame.step_index == 5:
            cid, frame.decision = frame.decision, None
            frame.local['card'] = cid
            destinations = tuple(pair[2] for pair in self.move_pairs(state, pid) if pair[0] == cid)
            if not destinations:
                return StepResult.complete()
            frame.step_index = 6
            return self.ask(frame, RequestType.CHOOSE_PLAYER, '【旋风】选择另一名其他角色接收装备',
                            allowed_player_ids=destinations)
        target, frame.decision = frame.decision, None
        cid = frame.local['card']
        if not any(pair[0] == cid and pair[2] == target for pair in self.move_pairs(state, pid)):
            raise InvalidCardUse('旋风装备移动已不合法')
        ref = locate(state, cid)
        self.moves.move(state, CardMove(action.action_id + ':move', (cid,), ref,
            ZoneRef(ZoneType.EQUIPMENT, target, ref.equipment_slot), CardMoveReason.SYSTEM,
            pid, action.action_id))
        return StepResult.complete()

    def tishen(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            frame.step_index = 1
            return self.ask(frame, RequestType.YES_NO,
                '【替身】是否弃置所有锦囊牌和坐骑牌，直到下回合开始获得未对你造成伤害的杀？')
        wanted, frame.decision = frame.decision is True, None
        if not wanted:
            return StepResult.complete()
        cards = tuple(cid for cid in owned_cards(state, action.player_id)
                      if self.definitions.get(state.cards[cid].definition_id).category
                         in (CardCategory.TRICK, CardCategory.DELAYED_TRICK)
                      or self.definitions.get(state.cards[cid].definition_id).equipment_slot
                         in (EquipmentSlot.OFFENSIVE_HORSE, EquipmentSlot.DEFENSIVE_HORSE))
        state.players[action.player_id].marks['jie_tishen_active'] = 1
        groups = {}
        for cid in cards:
            groups.setdefault(locate(state, cid), []).append(cid)
        self.move_batch(state, groups, ZoneRef(ZoneType.DISCARD_PILE),
                        CardMoveReason.DISCARD, action, 'cost')
        self.moves.recorder.record(Event(action.action_id + ':used', 'skill_jie_tishen', action.player_id))
        return StepResult.complete()

    def collect_tishen(self, state, frame):
        action = frame.action
        if (not self.skills.has(state, action.player_id, 'jie_tishen')
                or not state.players[action.player_id].marks.get('jie_tishen_active')):
            return StepResult.complete()
        cards = tuple(cid for cid in action.card_ids
                      if locate(state, cid) is not None
                      and locate(state, cid).zone_type is ZoneType.DISCARD_PILE)
        if cards:
            self.moves.obtain_cards(state, cards, action.player_id, action.player_id, action.action_id)
        return StepResult.complete()


def register(registry, skills, moves, definitions, deck=None):
    registry.register(BoundaryCombatAction, BoundaryCombatHandler(skills, moves, definitions))


def event_reactions(state, event, skills, recorder, definitions=None):
    if skills is None:
        return []
    result = []
    if isinstance(event, TurnStartedEvent):
        state.players[event.player_id].marks.pop('jie_tishen_active', None)
    if isinstance(event, PhaseStartedEvent) and event.phase is Phase.PLAY:
        state.players[event.player_id].marks.pop('jie_paoxiao_slash', None)
    if isinstance(event, CardUsedEvent):
        definition = event.virtual_definition_id or (
            state.cards[event.card_id].definition_id if event.card_id in state.cards else '')
        if definition not in SLASH_IDS:
            return result
        if (skills.has(state, event.player_id, 'jie_paoxiao')
                and state.current_player_id == event.player_id and state.current_phase is Phase.PLAY):
            state.players[event.player_id].marks['jie_paoxiao_slash'] = 1
        materials = (event.virtual_card.material_ids if event.virtual_card is not None
                     else (event.card_id,) if event.card_id in state.cards else ())
        key = event.event_id.removesuffix(':used')
        state.metadata.setdefault('t22_slash_uses', {})[key] = {
            'source': event.player_id, 'targets': list(event.target_ids),
            'materials': tuple(materials), 'damaged': []}
        if skills.has(state, event.player_id, 'jie_pojun'):
            for index, target in enumerate(event.target_ids):
                if target != event.player_id and state.players[target].is_alive:
                    result.append(BoundaryCombatAction(event.event_id + ':pojun:' + str(index),
                        event.player_id, 'jie_pojun', target, event_id=key))
        return result
    if isinstance(event, CardMovedEvent):
        owner = event.from_zone.player_id
        if (event.from_zone.zone_type is ZoneType.EQUIPMENT and owner is not None
                and not (event.related_action_id or '').startswith(('equipment-exchange:', 'equipment-departure:'))
                and state.players[owner].is_alive and skills.has(state, owner, 'jie_xuanfeng')):
            result.append(BoundaryCombatAction(event.event_id + ':xuanfeng', owner, 'jie_xuanfeng'))
        if (event.from_zone.zone_type is ZoneType.PROCESSING
                and event.to_zone.zone_type is ZoneType.DISCARD_PILE
                and event.reason == CardMoveReason.USE.value):
            records = state.metadata.get('t22_slash_uses', {})
            for key, record in tuple(records.items()):
                materials = tuple(cid for cid in record['materials'] if cid in event.card_ids)
                if not materials:
                    continue
                for target in record['targets']:
                    if (target not in record['damaged'] and state.players[target].is_alive
                            and skills.has(state, target, 'jie_tishen')
                            and state.players[target].marks.get('jie_tishen_active')):
                        result.append(BoundaryCombatAction(event.event_id + ':tishen:' + target,
                            target, 'collect_tishen', card_ids=materials, event_id=key))
                if set(record['materials']).issubset(event.card_ids):
                    del records[key]
    elif isinstance(event, Event) and event.event_type == 'equipment_departure_batch':
        owner = event.source_id
        if state.players[owner].is_alive and skills.has(state, owner, 'jie_xuanfeng'):
            result.append(BoundaryCombatAction(event.event_id + ':xuanfeng', owner, 'jie_xuanfeng'))
    elif isinstance(event, PhaseEndedEvent):
        owner = event.player_id
        if event.phase is Phase.PLAY:
            if state.players[owner].is_alive and skills.has(state, owner, 'jie_tishen'):
                result.append(BoundaryCombatAction(event.event_id + ':tishen', owner, 'jie_tishen'))
        elif (event.phase is Phase.DISCARD and state.players[owner].is_alive
              and skills.has(state, owner, 'jie_xuanfeng')
              and len(phase_rule_discards(recorder.events, event.event_id.removesuffix(':end'), owner)) >= 2):
            result.append(BoundaryCombatAction(event.event_id + ':xuanfeng', owner, 'jie_xuanfeng'))
    elif isinstance(event, CardResolvedEvent):
        state.metadata.get('t22_slash_uses', {}).pop(event.event_id.removesuffix(':resolved'), None)
    return result

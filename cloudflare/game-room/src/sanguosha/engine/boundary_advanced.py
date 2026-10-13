"""Mainland mobile boundary Zhong Hui, Li Ru, Ju Shou and Cao Xiu.

All choices use the existing YJ skill frames and normal card movement/damage.
"""
from dataclasses import dataclass, replace
from .events import CardRespondedEvent

from sanguosha.model.enums import CardCategory, Color, DamageNature, Phase, Suit
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType
from .actions import StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .card_rules import InvalidCardUse
from .deck import DrawCardsAction
from .events import (AfterDamageEvent, CardMovedEvent, CardUsedEvent, CardResolvedEvent,
                     Event, EventRecorder, PhaseEndedEvent, PhaseStartedEvent, TurnStartedEvent)
from .hp import LoseHpAction, LoseMaxHpAction
from .military_basics import MilitaryDamageAction, MilitarySlashRule, SLASH_IDS, SlashSequence, WineAction
from .military_equipment import discardable
from .recovery import RecoverAction
from .requests import RequestType
from .suits import effective_color, effective_suit
from .yj2011_tier3 import YJSkillAction, YJSkillHandler, hand, locate
from .yj2012 import power_zone


@dataclass(frozen=True, slots=True)
class BoundaryAdvancedAction(YJSkillAction):
    definition_id: str = ''


def owned_cards(state, pid):
    return tuple(cid for ref, zone in state.zones.items()
                 if ref.player_id == pid and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                 for cid in zone.card_ids)


def is_trick(definitions, state, cid):
    return definitions.get(state.cards[cid].definition_id).category in (
        CardCategory.TRICK, CardCategory.DELAYED_TRICK)


def last_jianying(state, pid):
    return state.metadata.get('jie_jianying_previous', {}).get(pid, {})


def jianying_virtual(state, pid, cid, definition):
    previous = last_jianying(state, pid)
    suit = Suit(previous['suit']) if previous.get('suit') else effective_suit(state, cid, pid)
    color = Color.RED if suit in (Suit.HEART, Suit.DIAMOND) else Color.BLACK
    return VirtualCard(definition, (cid,), suit, color, 'jie_jianying')


def jianying_materials(state, pid, skills, definition='basic.slash'):
    from .card_limits import card_allowed
    from .qiaoshui import prohibited
    usage = state.play_usage
    if (skills is None or not skills.has(state, pid, 'jie_jianying')
            or not state.players[pid].is_alive or state.current_player_id != pid
            or state.current_phase is not Phase.PLAY or usage is None
            or usage.player_id != pid or usage.turn_number != state.turn_number
            or usage.count('skill.jie_jianying') or prohibited(state, pid, definition)):
        return ()
    return tuple(cid for cid in owned_cards(state, pid)
                 if card_allowed(state, pid, (cid,), jianying_virtual(state, pid, cid, definition)))


class BoundaryAdvancedHandler(YJSkillHandler):
    def validate_start(self, state, a):
        if a.skill in ('jie_paiyi', 'jie_mieji', 'jie_jianying', 'jie_fencheng'):
            self.validate_active(state, a)
            if a.skill == 'jie_fencheng' and state.players[a.player_id].marks.get('jie_fencheng_used'):
                raise InvalidCardUse('焚城限定技已消耗')
            if a.skill == 'jie_paiyi' and not state.cards_in(power_zone(a.player_id)):
                raise InvalidCardUse('排异需要权')
            if a.skill == 'jie_mieji' and (not self.mieji_costs(state, a.player_id)
                    or not self.mieji_targets(state, a.player_id)):
                raise InvalidCardUse('灭计成本或目标不可用')
            if a.skill == 'jie_jianying' and not self.jianying_definitions(state, a.player_id):
                raise InvalidCardUse('渐营没有可用的基本牌转化')

    def step(self, state, frame):
        a = frame.action
        if a.skill == 'jie_fencheng' and frame.step_index > 0:
            from sanguosha.model.state import GameStatus
            return (StepResult.complete() if state.status is GameStatus.FINISHED
                    else self.jie_fencheng(state, frame))
        required = 'jie_jianying' if a.skill == 'jie_jianying_draw' else a.skill
        if not state.players[a.player_id].is_alive or not self.skills.has(state, a.player_id, required):
            if frame.step_index == 0 and a.skill in ('jie_paiyi', 'jie_mieji', 'jie_jianying', 'jie_fencheng'):
                raise InvalidCardUse('角色不具有该主动技能')
            return StepResult.complete()
        return super().step(state, frame)

    def jie_quanji(self, state, f):
        a = f.action
        if f.cursor >= a.amount:
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【权计】是否摸一张牌，再将一张手牌置为权？')
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted:
                f.cursor += 1
                f.step_index = 0
                return StepResult.continue_()
            f.step_index = 2
            return StepResult.push(DrawCardsAction(a.action_id + f':draw:{f.cursor}', a.player_id, 1))
        if f.step_index == 2:
            cards = hand(state, a.player_id)
            if not cards:
                f.cursor += 1
                f.step_index = 0
                return StepResult.continue_()
            f.step_index = 3
            return self.ask(f, RequestType.CHOOSE_CARD, '【权计】选择一张手牌置为权', eligible_card_ids=cards)
        card, f.decision = f.decision, None
        if card not in hand(state, a.player_id):
            raise InvalidCardUse('权计材料已不可用')
        self.transfer(state, a, (card,), power_zone(a.player_id))
        state.players[a.player_id].marks['quan'] = len(state.cards_in(power_zone(a.player_id)))
        f.cursor += 1
        f.step_index = 0
        return StepResult.continue_()

    def jie_zili(self, state, f):
        a = f.action
        p = state.players[a.player_id]
        if f.step_index == 0:
            if (p.marks.get('jie_zili_awakened') or (len(state.cards_in(power_zone(a.player_id))) < 3
                    and not p.marks.get('ignore_awakening:jie_zili'))):
                return StepResult.complete()
            p.marks['jie_zili_awakened'] = 1
            f.step_index = 1
            choices = ('draw', 'recover') if p.hp < p.max_hp else ('draw',)
            return self.ask(f, RequestType.CHOOSE_OPTION, '【自立】先摸两张牌或回复一点体力，再减上限并获得排异', choices=choices)
        if f.step_index == 1:
            choice, f.decision = f.decision, None
            f.step_index = 2
            child = (RecoverAction(a.action_id + ':recover', a.player_id, a.player_id, 1)
                     if choice == 'recover' else DrawCardsAction(a.action_id + ':draw', a.player_id, 2))
            return StepResult.push(child)
        if f.step_index == 2:
            f.step_index = 3
            return StepResult.push(LoseMaxHpAction(a.action_id + ':cost', a.player_id, 1))
        from .skill_grants import add_grant
        add_grant(state, a.player_id, 'jie_paiyi', 'jie_zili')
        self.moves.recorder.record(Event(a.action_id + ':gain', 'skill_gained', a.player_id,
                                        metadata={'skill_id': 'jie_paiyi', 'source': 'jie_zili'}))
        return StepResult.complete()

    def jie_paiyi(self, state, f):
        a = f.action
        pid = a.player_id
        if f.step_index == 0:
            self.validate_active(state, a)
            cards = state.cards_in(power_zone(pid))
            if not cards:
                raise InvalidCardUse('排异需要权')
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_CARD, '【排异】选择弃置的一张权', eligible_card_ids=cards)
        if f.step_index == 1:
            f.local['power'], f.decision = f.decision, None
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【排异】选择摸两张牌的角色',
                            allowed_player_ids=tuple(q for q in state.seat_order if state.players[q].is_alive))
        if f.step_index == 2:
            target, f.decision = f.decision, None
            self.validate_active(state, a)
            if f.local['power'] not in state.cards_in(power_zone(pid)) or not state.players[target].is_alive:
                raise InvalidCardUse('排异权或目标已不可用')
            self.transfer(state, a, (f.local['power'],), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD)
            state.players[pid].marks['quan'] = len(state.cards_in(power_zone(pid)))
            state.play_usage.record('skill.jie_paiyi')
            f.local['target'] = target
            f.step_index = 3
            return StepResult.push(DrawCardsAction(a.action_id + ':draw', target, 2))
        target = f.local['target']
        if f.step_index == 3 and state.players[target].is_alive and len(hand(state, target)) > len(hand(state, pid)):
            f.step_index = 4
            return StepResult.push(MilitaryDamageAction(a.action_id + ':damage', pid, target, 1))
        return StepResult.complete()

    def jie_juece(self, state, f):
        a = f.action
        targets = tuple(q for q in state.seat_order if q != a.player_id and state.players[q].is_alive
                        and q in state.metadata.get('jie_juece_lost', ()))
        if f.step_index == 0:
            if not targets:
                return StepResult.complete()
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【绝策】是否对本回合失去过牌的其他角色造成一点伤害？')
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted or not targets:
                return StepResult.complete()
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【绝策】选择本回合失去过牌的角色', allowed_player_ids=targets)
        if f.step_index == 2:
            target, f.decision = f.decision, None
            f.step_index = 3
            if target in targets:
                return StepResult.push(MilitaryDamageAction(a.action_id + ':damage', a.player_id, target, 1))
        return StepResult.complete()

    def mieji_costs(self, state, pid):
        return tuple(c for c in hand(state, pid) if is_trick(self.definitions, state, c)
                     and effective_color(state, c, pid) is Color.BLACK)

    def mieji_targets(self, state, pid):
        return tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive and owned_cards(state, q))

    def jie_mieji(self, state, f):
        a = f.action
        pid = a.player_id
        if f.step_index == 0:
            self.validate_start(state, a)
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_CARD, '【灭计】展示一张黑色锦囊并置于牌堆顶', eligible_card_ids=self.mieji_costs(state, pid))
        if f.step_index == 1:
            f.local['card'], f.decision = f.decision, None
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【灭计】选择有牌的其他角色', allowed_player_ids=self.mieji_targets(state, pid))
        if f.step_index == 2:
            target, f.decision = f.decision, None
            card = f.local['card']
            self.validate_active(state, a)
            if card not in self.mieji_costs(state, pid) or target not in self.mieji_targets(state, pid):
                raise InvalidCardUse('灭计材料或目标已不可用')
            f.local['target'] = target
            state.play_usage.record('skill.jie_mieji')
            self.moves.recorder.record(Event(a.action_id + ':reveal', 'card_revealed', pid, metadata={'card_id': card}))
            self.moves.move(state, CardMove(a.action_id + ':top', (card,), ZoneRef(ZoneType.HAND, pid),
                ZoneRef(ZoneType.DRAW_PILE), CardMoveReason.SYSTEM, pid, a.action_id, to_top=True))
            f.step_index = 3
            return StepResult.continue_()
        target = f.local['target']
        if not state.players[target].is_alive:
            return StepResult.complete()
        if f.step_index == 3:
            tricks = tuple(c for c in hand(state, target) if is_trick(self.definitions, state, c))
            other = tuple(c for c in discardable(state, target) if not is_trick(self.definitions, state, c))
            choices = tuple(key for key, eligible in (('give_trick', tricks), ('discard_nontricks', other)) if eligible)
            if not choices:
                return StepResult.complete()
            f.step_index = 4
            return self.ask(f, RequestType.CHOOSE_OPTION, '【灭计】交给李儒一张锦囊，或依次弃置两张非锦囊', player=target, choices=choices)
        if f.step_index == 4:
            choice, f.decision = f.decision, None
            f.local['branch'] = choice
            f.step_index = 5
        if f.step_index == 5:
            if f.local['branch'] == 'give_trick':
                cards = tuple(c for c in hand(state, target) if is_trick(self.definitions, state, c))
                prompt = '【灭计】选择交给李儒的一张锦囊'
            else:
                cards = tuple(c for c in discardable(state, target) if not is_trick(self.definitions, state, c))
                prompt = f'【灭计】选择第 {f.cursor + 1} 张非锦囊弃置'
                if f.cursor >= 2:
                    return StepResult.complete()
            if not cards:
                return StepResult.complete()
            f.step_index = 6
            return self.ask(f, RequestType.CHOOSE_CARD, prompt, player=target, eligible_card_ids=cards)
        card, f.decision = f.decision, None
        if f.local['branch'] == 'give_trick':
            if card not in hand(state, target) or not is_trick(self.definitions, state, card):
                raise InvalidCardUse('灭计交牌已不可用')
            self.transfer(state, a, (card,), ZoneRef(ZoneType.HAND, pid), actor=target)
            return StepResult.complete()
        if card not in discardable(state, target) or is_trick(self.definitions, state, card):
            raise InvalidCardUse('灭计弃牌已不可用')
        self.transfer(state, a, (card,), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, actor=target)
        f.cursor += 1
        f.step_index = 5
        return StepResult.continue_()

    def jie_fencheng(self, state, f):
        a = f.action
        pid = a.player_id
        if f.step_index == 0:
            self.validate_start(state, a)
            state.players[pid].marks['jie_fencheng_used'] = 1
            start = state.seat_order.index(pid)
            f.local['targets'] = state.seat_order[start + 1:] + state.seat_order[:start]
            f.local['threshold'] = 1
            f.step_index = 1
        targets = f.local['targets']
        if f.step_index == 2:
            paid, f.decision = tuple(f.decision), None
            target = targets[f.cursor]
            if paid:
                if len(paid) < f.local['threshold'] or any(cid not in discardable(state, target) for cid in paid):
                    raise InvalidCardUse('焚城弃牌已不可用')
                self.transfer(state, a, paid, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, actor=target)
                f.local['threshold'] = len(paid) + 1
                f.cursor += 1
                f.step_index = 1
                return StepResult.continue_()
            f.local['threshold'] = 1
            f.cursor += 1
            f.step_index = 1
            return StepResult.push(MilitaryDamageAction(a.action_id + ':damage:' + target, pid, target, 2, DamageNature.FIRE))
        while f.cursor < len(targets) and not state.players[targets[f.cursor]].is_alive:
            f.cursor += 1
        if f.cursor >= len(targets):
            return StepResult.complete()
        target = targets[f.cursor]
        cards = discardable(state, target)
        threshold = f.local['threshold']
        if len(cards) < threshold:
            f.local['threshold'] = 1
            f.cursor += 1
            return StepResult.push(MilitaryDamageAction(a.action_id + ':damage:' + target, pid, target, 2, DamageNature.FIRE))
        f.step_index = 2
        return self.ask(f, RequestType.CHOOSE_CARDS,
            f'【焚城】弃置至少{threshold}张牌，否则受到两点火焰伤害', player=target,
            eligible_card_ids=cards, min_count=0, max_count=len(cards), minimum_nonempty_count=threshold)

    def jie_jianying_draw(self, state, f):
        a = f.action
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【渐营】与本阶段上一张牌花色或点数相同，是否摸一张牌？')
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            f.step_index = 2
            if wanted:
                return StepResult.push(DrawCardsAction(a.action_id + ':draw', a.player_id, 1))
        return StepResult.complete()

    def jianying_targets(self, state, pid, cid):
        preview = replace(state, zones={ref: CardZone(ref, list(zone.card_ids)) for ref, zone in state.zones.items()})
        CardMoveService(EventRecorder()).move_owned_materials(preview, (cid,), pid,
            ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE, 'jianying-preview')
        rule = MilitarySlashRule(self.authorized.distance, self.skills)
        if not rule.can_use(preview, pid):
            return ()
        limit = rule.usage_limit(preview, pid)
        if limit is not None and preview.play_usage.count('basic.slash') >= limit:
            return ()
        return rule.target_candidates(preview, pid)

    def jianying_definitions(self, state, pid):
        result = []
        for definition in (*SLASH_IDS, 'basic.peach', 'basic.wine'):
            cards = jianying_materials(state, pid, self.skills, definition)
            if not cards:
                continue
            if definition in SLASH_IDS and not any(self.jianying_targets(state, pid, cid) for cid in cards):
                continue
            if definition == 'basic.peach' and state.players[pid].hp >= state.players[pid].max_hp:
                continue
            if definition == 'basic.wine' and state.play_usage.count('basic.wine'):
                continue
            result.append(definition)
        return tuple(result)

    def jie_jianying(self, state, f):
        a = f.action
        pid = a.player_id
        if f.step_index == 0:
            self.validate_start(state, a)
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_OPTION, '【渐营】选择转化的基本牌', choices=self.jianying_definitions(state, pid))
        if f.step_index == 1:
            definition, f.decision = f.decision, None
            if definition not in self.jianying_definitions(state, pid):
                raise InvalidCardUse('渐营基本牌已不可用')
            f.local['definition'] = definition
            cards = jianying_materials(state, pid, self.skills, definition)
            if definition in SLASH_IDS:
                cards = tuple(cid for cid in cards if self.jianying_targets(state, pid, cid))
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_CARD, '【渐营】选择一张牌作为素材', eligible_card_ids=cards)
        if f.step_index == 2:
            cid, f.decision = f.decision, None
            f.local['card'] = cid
            definition = f.local['definition']
            if cid not in jianying_materials(state, pid, self.skills, definition):
                raise InvalidCardUse('渐营素材已不可用')
            f.step_index = 3
            if definition in SLASH_IDS:
                rule = MilitarySlashRule(self.authorized.distance, self.skills)
                # Preview removes an equipment cost before determining target count.
                preview = replace(state, zones={ref: CardZone(ref, list(zone.card_ids)) for ref, zone in state.zones.items()})
                CardMoveService(EventRecorder()).move_owned_materials(preview, (cid,), pid,
                    ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE, 'jianying-bounds-preview')
                low, high = rule.target_bounds(preview, pid, None)
                f.local['bounds'] = (low, high)
                return self.ask(f, RequestType.CHOOSE_PLAYERS, '【渐营】选择杀的目标',
                    allowed_player_ids=self.jianying_targets(state, pid, cid), min_count=low, max_count=high)
            f.decision = ()
        if f.step_index == 3:
            definition = f.local['definition']
            cid = f.local['card']
            targets, f.decision = tuple(f.decision), None
            if definition not in self.jianying_definitions(state, pid) or cid not in jianying_materials(state, pid, self.skills, definition):
                raise InvalidCardUse('渐营转化已不可用')
            if definition in SLASH_IDS and (not f.local['bounds'][0] <= len(targets) <= f.local['bounds'][1] or len(set(targets)) != len(targets)
                    or any(q not in self.jianying_targets(state, pid, cid) for q in targets)):
                raise InvalidCardUse('渐营杀目标已不可用')
            virtual = jianying_virtual(state, pid, cid, definition)
            self.moves.move_owned_materials(state, (cid,), pid, ZoneRef(ZoneType.PROCESSING), CardMoveReason.USE, a.action_id)
            state.play_usage.record('skill.jie_jianying')
            from .yj2011_tier3 import record_slash_use
            counted = record_slash_use(state, pid, targets) if definition in SLASH_IDS else False
            if definition == 'basic.wine':
                state.play_usage.record('basic.wine')
            actual_targets = targets if definition in SLASH_IDS else (pid,)
            self.moves.recorder.record(CardUsedEvent(a.action_id + ':used', pid, cid, actual_targets,
                                                     definition, counted, virtual))
            f.step_index = 4
            if definition in SLASH_IDS:
                return StepResult.push(SlashSequence(a.action_id + ':effect', pid, cid, targets, virtual))
            if definition == 'basic.peach':
                return StepResult.push(RecoverAction(a.action_id + ':effect', pid, pid, 1, cid))
            return StepResult.push(WineAction(a.action_id + ':effect', pid))
        cid = f.local['card']
        if cid in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
            self.transfer(state, a, (cid,), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.USE)
        self.moves.recorder.record(CardResolvedEvent(a.action_id + ':resolved', pid, cid))
        return StepResult.complete()

    def jie_shibei(self, state, f):
        if f.step_index == 0:
            f.step_index = 1
            a = f.action
            if a.amount == 1:
                return StepResult.push(RecoverAction(a.action_id + ':recover', a.player_id, a.player_id, 1))
            return StepResult.push(LoseHpAction(a.action_id + ':lose-hp', a.player_id, 1))
        return StepResult.complete()

    def jie_qingxi(self, state, f):
        a = f.action
        pid = a.player_id
        target = a.target_id
        if target not in state.players or target == pid or not state.players[target].is_alive:
            return StepResult.complete(0)
        if f.step_index == 0:
            if state.players[pid].marks.get('jie_qingxi_turn') == state.turn_number:
                return StepResult.complete(0)
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, f'【倾袭】是否令伤害目标弃置 {a.amount} 张手牌，否则此伤害加一？', subject_player_id=target)
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted:
                return StepResult.complete(0)
            state.players[pid].marks['jie_qingxi_turn'] = state.turn_number
            cards = hand(state, target)
            if len(cards) < a.amount:
                return StepResult.complete(1)
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_CARDS,
                f'【倾袭】弃置 {a.amount} 张手牌，否则伤害加一', player=target,
                eligible_card_ids=cards, min_count=0, max_count=a.amount,
                minimum_nonempty_count=a.amount)
        paid, f.decision = tuple(f.decision), None
        if not paid:
            return StepResult.complete(1)
        if len(paid) != a.amount or any(cid not in hand(state, target) for cid in paid):
            raise InvalidCardUse('倾袭弃牌已不可用')
        self.transfer(state, a, paid, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, actor=target)
        return StepResult.complete(0)


def prepare_damage(state, frame, skills, distance):
    a = frame.action
    if frame.local.pop('jie_qingxi_wait', False):
        frame.local['jie_qingxi_bonus'] = int(frame.child_result or 0)
        frame.child_result = None
    if frame.local.get('jie_qingxi_done'):
        return None
    frame.local['jie_qingxi_done'] = True
    if (skills is not None and a.source_id is not None and a.source_id != a.target_id
            and state.players[a.source_id].is_alive and skills.has(state, a.source_id, 'jie_qingxi')
            and state.players[a.source_id].marks.get('jie_qingxi_turn') != state.turn_number):
        frame.local['jie_qingxi_wait'] = True
        amount = max(1, 4 - distance.distance_between(state, a.source_id, a.target_id))
        return StepResult.push(BoundaryAdvancedAction(a.action_id + ':jie-qingxi', a.source_id,
                                                      'jie_qingxi', a.target_id, amount=amount))
    return None


def damage_reaction(state, frame, skills):
    if frame.step_index != 1 or skills is None:
        return None
    a = frame.action
    if not frame.local.get('jie_shibei_done'):
        frame.local['jie_shibei_done'] = True
        if state.players[a.target_id].is_alive and skills.has(state, a.target_id, 'jie_shibei'):
            count = state.metadata.get('jie_shibei_order', {}).pop(a.action_id, 1)
            return StepResult.push(BoundaryAdvancedAction(a.action_id + ':jie-shibei', a.target_id,
                                                          'jie_shibei', amount=count))
    if not frame.local.get('jie_quanji_done'):
        frame.local['jie_quanji_done'] = True
        if state.players[a.target_id].is_alive and skills.has(state, a.target_id, 'jie_quanji'):
            return StepResult.push(BoundaryAdvancedAction(a.action_id + ':jie-quanji', a.target_id,
                                                          'jie_quanji', amount=int(frame.local['amount'])))
    return None


def event_reactions(state, event, skills, recorder=None):
    result = []
    if isinstance(event, TurnStartedEvent):
        clear_turn(state)
    elif isinstance(event, AfterDamageEvent):
        counts = state.metadata.setdefault('jie_shibei_counts', {})
        counts[event.target_id] = counts.get(event.target_id, 0) + 1
        state.metadata.setdefault('jie_shibei_order', {})[event.event_id.removesuffix(':after')] = counts[event.target_id]
    elif isinstance(event, CardMovedEvent) and event.card_ids and event.triggers_rules:
        owner = event.from_zone.player_id
        # Loss follows departure from the personal hand/equipment area. A
        # private pile still has an owner but its cards have left that area.
        if (owner is not None and event.from_zone.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                and not (event.to_zone.player_id == owner and event.to_zone.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT))):
            lost = state.metadata.setdefault('jie_juece_lost', [])
            if owner not in lost:
                lost.append(owner)
    elif isinstance(event, PhaseStartedEvent):
        pid = event.player_id
        if event.phase is Phase.PLAY:
            state.metadata.setdefault('jie_jianying_previous', {}).pop(pid, None)
        if skills is not None and state.players[pid].is_alive:
            if event.phase is Phase.PREPARATION and skills.has(state, pid, 'jie_zili'):
                result.append(BoundaryAdvancedAction(event.event_id + ':jie-zili', pid, 'jie_zili'))
            elif event.phase is Phase.FINISH and skills.has(state, pid, 'jie_juece'):
                result.append(BoundaryAdvancedAction(event.event_id + ':jie-juece', pid, 'jie_juece'))
    elif isinstance(event, PhaseEndedEvent):
        pid = event.player_id
        if (event.phase is Phase.PLAY and skills is not None and state.players[pid].is_alive
                and skills.has(state, pid, 'jie_quanji') and len(hand(state, pid)) > state.players[pid].hp):
            result.append(BoundaryAdvancedAction(event.event_id + ':jie-quanji', pid, 'jie_quanji'))
    elif isinstance(event, CardRespondedEvent) and event.response_definition_id in ('basic.dodge', 'basic.peach'):
        # These are uses in mobile rules even when carried by a response request.
        return event_reactions(state, CardUsedEvent(event.event_id + ':basic-use',
            event.player_id, event.card_id, (), event.response_definition_id), skills, recorder)
    elif (isinstance(event, CardUsedEvent) and state.current_player_id == event.player_id
          and state.current_phase is Phase.PLAY):
        pid = event.player_id
        suit = event.virtual_card.suit if event.virtual_card is not None else (
            effective_suit(state, event.card_id, pid) if event.card_id in state.cards else None)
        materials = event.virtual_card.material_ids if event.virtual_card is not None else (event.card_id,)
        rank = state.cards[materials[0]].rank if len(materials) == 1 and materials[0] in state.cards else None
        previous = last_jianying(state, pid)
        if (skills is not None and skills.has(state, pid, 'jie_jianying') and previous
                and ((suit is not None and previous.get('suit') == suit.value)
                     or (rank is not None and previous.get('rank') == rank))):
            result.append(BoundaryAdvancedAction(event.event_id + ':jie-jianying', pid, 'jie_jianying_draw'))
        state.metadata.setdefault('jie_jianying_previous', {})[pid] = {
            'suit': suit.value if suit is not None else None, 'rank': rank}
    return tuple(result)


def play_options(state, pid, skills, definitions=None):
    if state.play_usage is None or state.current_player_id != pid or state.current_phase is not Phase.PLAY:
        return []
    options = []
    if (skills.has(state, pid, 'jie_paiyi') and not state.play_usage.count('skill.jie_paiyi')
            and state.cards_in(power_zone(pid))):
        options.append('skill:jie_paiyi')
    if skills.has(state, pid, 'jie_fencheng') and not state.players[pid].marks.get('jie_fencheng_used'):
        options.append('skill:jie_fencheng')
    if definitions is not None:
        handler = BoundaryAdvancedHandler(skills, CardMoveService(EventRecorder()), definitions, None)
        if (skills.has(state, pid, 'jie_mieji') and not state.play_usage.count('skill.jie_mieji')
                and handler.mieji_costs(state, pid) and handler.mieji_targets(state, pid)):
            options.append('skill:jie_mieji')
        if handler.jianying_definitions(state, pid):
            options.append('skill:jie_jianying')
    return options


def clear_turn(state):
    for key in ('jie_shibei_counts', 'jie_shibei_order', 'jie_juece_lost', 'jie_jianying_previous'):
        state.metadata.pop(key, None)
    for player in state.players.values():
        player.marks.pop('jie_qingxi_turn', None)


def register(registry, skills, moves, definitions, deck):
    registry.register(BoundaryAdvancedAction, BoundaryAdvancedHandler(skills, moves, definitions, deck))



def response_options(state, action, skills):
    """Use-method basic cards during the owner's play phase, never plain Slash replies."""
    definition = action.required_definition_id
    if definition not in ('basic.dodge', 'basic.peach', 'basic.slash'):
        return ()
    if definition == 'basic.slash' and not action.use_card:
        return ()
    if definition == 'basic.slash' and state.players[action.player_id].marks.get('slash_prohibited'):
        return ()
    return tuple('virtual:jie_jianying:' + cid for cid in
                 jianying_materials(state, action.player_id, skills, definition))


def commit_response(state, action, choice, moves, recorder, skills):
    """Return the existing VirtualCard result expected by normal response parents."""
    if choice not in response_options(state, action, skills):
        raise InvalidCardUse('渐营响应素材或时机已不可用')
    cid = choice.split(':', 2)[2]
    virtual = jianying_virtual(state, action.player_id, cid, action.required_definition_id)
    state.play_usage.record('skill.jie_jianying')
    moves.move_owned_materials(state, (cid,), action.player_id, ZoneRef(ZoneType.PROCESSING),
                              CardMoveReason.USE, action.action_id + ':jie-jianying')
    # A forced-use parent publishes its own CardUsedEvent after confirming the
    # target. Jink and rescue Peach are uses represented by response requests.
    if not action.use_card:
        targets = (action.subject_player_id,) if action.required_definition_id == 'basic.peach' and action.subject_player_id is not None else ()
        recorder.record(CardUsedEvent(action.action_id + ':jie-jianying-used', action.player_id,
            cid, targets, action.required_definition_id, False, virtual))
        moves.move(state, CardMove(action.action_id + ':jie-jianying-discard', (cid,),
            ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.USE,
            action.player_id, action.action_id))
        recorder.record(CardResolvedEvent(action.action_id + ':jie-jianying-resolved', action.player_id, cid))
    return virtual

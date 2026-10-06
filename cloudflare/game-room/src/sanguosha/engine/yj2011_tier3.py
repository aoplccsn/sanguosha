"""Locked classic YJ2011 skills, implemented as resumable authoritative actions."""
from dataclasses import dataclass

from sanguosha.model.enums import Phase, Suit, CardCategory, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard
from .actions import Action, StepResult
from .requests import PendingRequest, RequestType
from .card_moves import CardMove, CardMoveReason, EquipmentExchangeTransaction
from .card_rules import InvalidCardUse
from .deck import DrawCardsAction
from .recovery import RecoverAction
from .hp import LoseHpAction
from .turnover import TurnoverAction
from .pindian import PindianAction
from .events import Event, CardMovedEvent, CardUsedEvent
from .distance import DistanceSystem
from .military_equipment import discardable

SLASH = ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash')


def hand(state, pid):
    return state.cards_in(ZoneRef(ZoneType.HAND, pid))


def locate(state, cid):
    return next(ref for ref, zone in state.zones.items() if cid in zone.card_ids)


def equipped_cards(state, pid):
    return tuple(cid for ref, z in state.zones.items()
                 if ref.player_id == pid and ref.zone_type is ZoneType.EQUIPMENT for cid in z.card_ids)


def scoped_target(state, source, target):
    return state.players[source].marks.get('yj_xianzhen:' + target) == state.turn_number


def record_slash_use(state, source, targets):
    if not targets or not all(scoped_target(state, source, target) for target in targets):
        state.play_usage.record('basic.slash')
        return True
    return False


def protected(state, target):
    return state.players[target].marks.get('yj_zhichi') == state.turn_number


def clear_zhichi(state):
    for player in state.players.values():
        player.marks.pop('yj_zhichi', None)


def clear_turn(state):
    state.metadata.pop('longyin_ignored_events',None)
    for player in state.players.values():
        for key in tuple(player.marks):
            if key.startswith('yj_xianzhen:') or key in ('yj_zhichi', 'yj_xianzhen_loss','qiaoshui_success','qiaoshui_trick_lock'):
                player.marks.pop(key)


def canonical_definition(state, skills, pid, definition, card_id=None):
    from .gods import wushen_applies
    if wushen_applies(state, skills, pid, card_id):
        return 'basic.slash'
    from .longnu import longnu_definition
    converted=longnu_definition(state,skills,pid,definition,card_id)
    return ('basic.slash' if converted == 'basic.wine' and skills is not None
            and skills.has(state, pid, 'jinjiu') else converted)


@dataclass(frozen=True, slots=True)
class YJSkillAction(Action):
    player_id: str
    skill: str
    target_id: str | None = None
    card_ids: tuple[str, ...] = ()
    amount: int = 1


@dataclass(frozen=True, slots=True)
class AuthorizedVirtualUse(Action):
    player_id: str
    target_ids: tuple[str, ...]
    virtual_card: VirtualCard


class AuthorizedVirtualUseHandler:
    """A skill grants a normal virtual Slash, outside play quota, inside range."""
    def __init__(self, skills, definitions, recorder):
        self.skills, self.distance, self.recorder = skills, DistanceSystem(definitions), recorder

    def candidates(self, state, pid):
        if not state.players[pid].is_alive or state.players[pid].marks.get('slash_prohibited'):
            return ()
        if state.players[pid].marks.get('yj_xianzhen_loss') == state.turn_number:
            return ()
        from .fuhuanghou import target_allowed
        return tuple(q for q in state.seat_order if q != pid and state.players[q].is_alive and target_allowed(state,pid,q)
                     and self.distance.can_reach_with_slash(state, pid, q)
                     and not (self.skills.has(state, q, 'kongcheng') and not hand(state, q)))

    def step(self, state, frame):
        from .military_basics import SlashSequence
        a = frame.action
        if frame.step_index == 0:
            if (a.virtual_card.definition_id != 'basic.slash' or a.virtual_card.material_ids
                    or len(a.target_ids) != 1 or a.target_ids[0] not in self.candidates(state, a.player_id)):
                raise InvalidCardUse('authorized virtual Slash is unavailable')
            frame.step_index = 1
            self.recorder.record(CardUsedEvent(a.action_id + ':used', a.player_id,
                a.action_id, a.target_ids, 'basic.slash', virtual_card=a.virtual_card))
            return StepResult.push(SlashSequence(a.action_id + ':slash', a.player_id,
                a.action_id, a.target_ids, a.virtual_card))
        return StepResult.complete(frame.child_result)


class YJSkillHandler:
    def __init__(self, skills, moves, definitions, deck):
        self.skills, self.moves, self.definitions, self.deck = skills, moves, definitions, deck
        self.authorized = AuthorizedVirtualUseHandler(skills, definitions, moves.recorder)

    def ask(self, f, kind, prompt, player=None, **kwargs):
        a = f.action
        return StepResult.ask(PendingRequest(f'{a.action_id}:request:{f.step_index}:{f.cursor}',
            player or a.player_id, kind, prompt, a.action_id, f.frame_id, **kwargs))

    def transfer(self, state, a, cards, destination, reason=CardMoveReason.SYSTEM, actor=None):
        if destination.zone_type is ZoneType.HAND and reason is CardMoveReason.SYSTEM and len(cards) > 1:
            self.moves.obtain_cards(state, tuple(cards), destination.player_id, actor or a.player_id,
                                    a.action_id + ':obtain')
            return
        groups = {}
        for cid in cards:
            groups.setdefault(locate(state, cid), []).append(cid)
        for index, (ref, ids) in enumerate(groups.items()):
            self.moves.move(state, CardMove(f'{a.action_id}:move:{index}:{ids[0]}', tuple(ids),
                ref, destination, reason, actor or a.player_id, a.action_id))

    def step(self, state, f):
        a = f.action
        if not state.players[a.player_id].is_alive:
            return StepResult.complete()
        return getattr(self, a.skill)(state, f)

    def luoying(self, state, f):
        a = f.action
        candidates = tuple(cid for cid in a.card_ids if cid in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
                           and state.cards[cid].suit is Suit.CLUB)
        if not candidates or not self.skills.has(state, a.player_id, 'luoying'):
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【落英】是否获得此批弃置或判定的梅花牌？')
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted:
                return StepResult.complete()
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_CARDS, '【落英】选择至少一张梅花牌',
                            eligible_card_ids=candidates, min_count=1, max_count=len(candidates))
        selected, f.decision = tuple(f.decision), None
        if any(cid not in candidates for cid in selected):
            raise InvalidCardUse('落英候选已不可用')
        self.transfer(state, a, selected, ZoneRef(ZoneType.HAND, a.player_id))
        return StepResult.complete()

    def jiushi(self, state, f):
        from .military_basics import WineAction
        a = f.action
        if f.step_index == 0:
            if (not self.skills.has(state, a.player_id, 'jiushi') or not state.players[a.player_id].face_up
                    or state.current_player_id != a.player_id or state.current_phase is not Phase.PLAY
                    or state.play_usage is None or state.play_usage.count('basic.wine')):
                raise InvalidCardUse('酒诗需要合法的酒使用窗口')
            state.play_usage.record('basic.wine')
            f.step_index = 1
            return StepResult.push(TurnoverAction(a.action_id + ':turn', a.player_id))
        if f.step_index == 1:
            f.step_index = 2
            self.moves.recorder.record(CardUsedEvent(a.action_id + ':used', a.player_id,
                a.action_id, (), 'basic.wine'))
            return StepResult.push(WineAction(a.action_id + ':wine', a.player_id))
        return StepResult.complete()

    def jiushi_return(self, state, f):
        a = f.action
        if not self.skills.has(state, a.player_id, 'jiushi'):
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【酒诗】伤害结算后是否翻至正面？')
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            f.step_index = 2
            if wanted and not state.players[a.player_id].face_up:
                return StepResult.push(TurnoverAction(a.action_id + ':return', a.player_id))
        return StepResult.complete()

    def enyuan_gain(self, state, f):
        a = f.action
        if not state.players[a.target_id].is_alive:
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【恩怨】是否令给牌者摸一张牌？',
                            subject_player_id=a.target_id)
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            f.step_index = 2
            if wanted:
                return StepResult.push(DrawCardsAction(a.action_id + ':draw', a.target_id, 1))
        return StepResult.complete()

    def enyuan_damage(self, state, f):
        a = f.action
        if f.cursor >= a.amount or not state.players[a.target_id].is_alive:
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【恩怨】是否要求伤害来源交牌或失去体力？',
                            subject_player_id=a.target_id)
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted:
                f.cursor += 1
                f.step_index = 0
                return StepResult.continue_()
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_OPTION, '【恩怨】交一张手牌，或失去一点体力',
                player=a.target_id, choices=('give', 'lose_hp') if hand(state, a.target_id) else ('lose_hp',))
        if f.step_index == 2:
            choice, f.decision = f.decision, None
            if choice == 'lose_hp':
                f.step_index = 4
                return StepResult.push(LoseHpAction(f'{a.action_id}:hp:{f.cursor}', a.target_id, 1))
            f.step_index = 3
            return self.ask(f, RequestType.CHOOSE_CARD, '【恩怨】选择交出的手牌',
                            player=a.target_id, eligible_card_ids=hand(state, a.target_id))
        if f.step_index == 3:
            cid, f.decision = f.decision, None
            if cid not in hand(state, a.target_id):
                raise InvalidCardUse('恩怨手牌已不可用')
            self.transfer(state, a, (cid,), ZoneRef(ZoneType.HAND, a.player_id), actor=a.target_id)
        f.cursor += 1
        f.step_index = 0
        return StepResult.continue_()

    def xuanhuo(self, state, f):
        from .card_use import UseCardAction
        a = f.action
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【眩惑】是否放弃正常摸牌并令另一角色摸两张？')
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted:
                return StepResult.complete(False)
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【眩惑】选择摸牌角色',
                allowed_player_ids=tuple(q for q in state.seat_order if q != a.player_id and state.players[q].is_alive))
        if f.step_index == 2:
            f.local['recipient'], f.decision = f.decision, None
            f.step_index = 3
            return StepResult.push(DrawCardsAction(a.action_id + ':draw', f.local['recipient'], 2))
        pid = f.local['recipient']
        if not state.players[pid].is_alive:
            return StepResult.complete(True)
        if f.step_index == 3:
            targets = self.authorized.candidates(state, pid)
            if targets:
                f.step_index = 4
                return self.ask(f, RequestType.CHOOSE_PLAYER, '【眩惑】选择其攻击范围内的杀目标',
                                allowed_player_ids=targets)
            f.step_index = 7
            return StepResult.continue_()
        if f.step_index == 4:
            f.local['victim'], f.decision = f.decision, None
            cards = tuple(cid for cid in hand(state, pid)
                if canonical_definition(state, self.skills, pid, state.cards[cid].definition_id,cid) in SLASH)
            f.step_index = 5
            return self.ask(f, RequestType.CHOOSE_OPTION, '【眩惑】使用一张杀，或让法正获得两张牌',
                            player=pid, choices=(*cards, 'decline'))
        if f.step_index == 5:
            choice, f.decision = f.decision, None
            if choice != 'decline':
                f.step_index = 6
                return StepResult.push(UseCardAction(a.action_id + ':forced', pid, choice,
                    (f.local['victim'],), forced=True))
            f.step_index = 7
        if f.step_index == 6:
            return StepResult.complete(True)
        if f.step_index == 7:
            selected = f.local.setdefault('selected', [])
            cards = tuple(cid for cid in discardable(state, pid) if cid not in selected)
            if f.cursor >= 2 or not cards:
                if selected:
                    self.transfer(state, a, tuple(selected), ZoneRef(ZoneType.HAND, a.player_id))
                return StepResult.complete(True)
            f.step_index = 8
            return self.ask(f, RequestType.CHOOSE_CARD, '【眩惑】获得该角色一张牌',
                            eligible_card_ids=cards, subject_player_id=pid)
        cid, f.decision = f.decision, None
        if cid not in discardable(state, pid) or cid in f.local['selected']:
            raise InvalidCardUse('眩惑获得牌不可用')
        f.local['selected'].append(cid)
        f.cursor += 1
        f.step_index = 7
        return StepResult.continue_()

    def xinzhan(self, state, f):
        a = f.action
        private = ZoneRef(ZoneType.SPECIAL, a.player_id, special_key='committed:xinzhan:' + a.action_id)
        if f.step_index == 0:
            self.validate_active(state, a)
            if len(hand(state, a.player_id)) <= state.players[a.player_id].max_hp:
                raise InvalidCardUse('心战手牌必须大于体力上限')
            state.play_usage.record('skill.xinzhan')
            for i in range(3):
                if not self.deck.ensure_draw(state, a.action_id + f':top:{i}'):
                    break
                cid = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
                self.transfer(state, a, (cid,), private)
            hearts = tuple(cid for cid in state.cards_in(private) if state.cards[cid].suit is Suit.HEART)
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_CARDS, '【心战】可选择红桃牌展示并获得，或不取',
                            eligible_card_ids=hearts, min_count=0, max_count=len(hearts))
        if f.step_index == 1:
            selected, f.decision = tuple(f.decision), None
            for cid in selected:
                if cid not in state.cards_in(private) or state.cards[cid].suit is not Suit.HEART:
                    raise InvalidCardUse('心战只能获得所看的红桃牌')
                self.moves.recorder.record(Event(a.action_id + ':reveal:' + cid, 'card_revealed',
                    a.player_id, metadata={'card_id': cid, 'skill_id': 'xinzhan'}))
            if selected:
                self.transfer(state, a, selected, ZoneRef(ZoneType.HAND, a.player_id))
            remaining = state.cards_in(private)
            if not remaining:
                return StepResult.complete()
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_CARDS, '【心战】排列剩余牌，第一张位于牌堆顶',
                            eligible_card_ids=remaining, min_count=len(remaining), max_count=len(remaining))
        ordered, f.decision = tuple(f.decision), None
        if set(ordered) != set(state.cards_in(private)):
            raise InvalidCardUse('心战必须归还全部剩余牌')
        self.moves.move(state, CardMove(a.action_id + ':return', ordered, private,
            ZoneRef(ZoneType.DRAW_PILE), CardMoveReason.SYSTEM, a.player_id, a.action_id, to_top=True))
        return StepResult.complete()

    def validate_active(self, state, a):
        if (not self.skills.has(state, a.player_id, a.skill) or state.current_player_id != a.player_id
                or state.current_phase is not Phase.PLAY or state.play_usage is None
                or state.play_usage.count('skill.' + a.skill)):
            raise InvalidCardUse('技能发动时机或次数不合法')

    def ganlu_pairs(self, state, pid):
        living = tuple(q for q in state.seat_order if state.players[q].is_alive)
        lost = max(0, state.players[pid].max_hp - state.players[pid].hp)
        return tuple((a, b) for i, a in enumerate(living) for b in living[i+1:]
                     if abs(len(equipped_cards(state, a)) - len(equipped_cards(state, b))) <= lost
                     and not any(locate(state,c).equipment_slot in state.players[b].abolished_equipment_slots for c in equipped_cards(state,a))
                     and not any(locate(state,c).equipment_slot in state.players[a].abolished_equipment_slots for c in equipped_cards(state,b)))

    def ganlu(self, state, f):
        a = f.action
        if f.step_index == 0:
            self.validate_active(state, a)
            pairs = self.ganlu_pairs(state, a.player_id)
            if not pairs:
                raise InvalidCardUse('甘露没有合法目标')
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【甘露】选择第一名交换装备的角色',
                            allowed_player_ids=tuple(dict.fromkeys(q for pair in pairs for q in pair)))
        if f.step_index == 1:
            f.local['first'], f.decision = f.decision, None
            first = f.local['first']
            partners = tuple(b if a0 == first else a0 for a0, b in self.ganlu_pairs(state, a.player_id)
                             if first in (a0, b))
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【甘露】选择第二名交换装备的角色',
                            allowed_player_ids=partners, subject_player_id=first)
        second, f.decision = f.decision, None
        first = f.local['first']
        if not any(set(pair) == {first, second} for pair in self.ganlu_pairs(state, a.player_id)):
            raise InvalidCardUse('甘露装备数量差不合法')
        for pid in (first, second):
            for cid in equipped_cards(state, pid):
                if self.definitions.get(state.cards[cid].definition_id).equipment_slot != locate(state, cid).equipment_slot:
                    raise InvalidCardUse('装备槽不合法')
        self.moves.exchange_equipment(state, EquipmentExchangeTransaction(a.action_id, (first, second), a.player_id))
        state.play_usage.record('skill.ganlu')
        return StepResult.complete()

    def buyi(self, state, f):
        a = f.action
        if (not self.skills.has(state, a.player_id, 'buyi') or not state.players[a.target_id].is_alive
                or state.players[a.target_id].hp > 0 or not hand(state, a.target_id)):
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index = 1
            return self.ask(f, RequestType.YES_NO, '【补益】是否展示濒死角色一张手牌？',
                            subject_player_id=a.target_id)
        if f.step_index == 1:
            wanted, f.decision = f.decision is True, None
            if not wanted:
                return StepResult.complete()
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_CARD, '【补益】选择展示一张手牌',
                            eligible_card_ids=hand(state, a.target_id), subject_player_id=a.target_id)
        if f.step_index == 2:
            cid, f.decision = f.decision, None
            if cid not in hand(state, a.target_id):
                raise InvalidCardUse('补益手牌不可用')
            self.moves.recorder.record(Event(a.action_id + ':reveal', 'card_revealed', a.target_id,
                metadata={'card_id': cid, 'skill_id': 'buyi'}))
            if self.definitions.get(state.cards[cid].definition_id).category is CardCategory.BASIC:
                return StepResult.complete()
            self.transfer(state, a, (cid,), ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, a.target_id)
            f.step_index = 3
            return StepResult.push(RecoverAction(a.action_id + ':recover', a.player_id, a.target_id, 1))
        return StepResult.complete()

    def mingce_materials(self, state, pid):
        return tuple(cid for cid in discardable(state, pid)
                     if self.definitions.get(state.cards[cid].definition_id).category is CardCategory.EQUIPMENT
                     or canonical_definition(state, self.skills, pid, state.cards[cid].definition_id,cid) in SLASH)

    def mingce(self, state, f):
        a = f.action
        if f.step_index == 0:
            self.validate_active(state, a)
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_CARD, '【明策】选择交出的装备牌或杀',
                            eligible_card_ids=self.mingce_materials(state, a.player_id))
        if f.step_index == 1:
            f.local['material'], f.decision = f.decision, None
            f.step_index = 2
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【明策】选择受赠者',
                allowed_player_ids=tuple(q for q in state.seat_order if q != a.player_id and state.players[q].is_alive))
        if f.step_index == 2:
            pid, f.decision = f.decision, None
            f.local['recipient'] = pid
            if f.local['material'] not in self.mingce_materials(state, a.player_id):
                raise InvalidCardUse('明策材料不可用')
            self.transfer(state, a, (f.local['material'],), ZoneRef(ZoneType.HAND, pid))
            state.play_usage.record('skill.mingce')
            f.step_index = 3
            return StepResult.continue_()
        pid = f.local['recipient']
        if not state.players[pid].is_alive:
            return StepResult.complete()
        if f.step_index == 3:
            candidates = self.authorized.candidates(state, pid)
            if not candidates:
                f.step_index = 6
                return StepResult.push(DrawCardsAction(a.action_id + ':draw', pid, 1))
            f.step_index = 4
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【明策】指定受赠者攻击范围内的杀目标',
                            allowed_player_ids=candidates)
        if f.step_index == 4:
            f.local['victim'], f.decision = f.decision, None
            f.step_index = 5
            return self.ask(f, RequestType.CHOOSE_OPTION, '【明策】视为使用杀或摸一张牌',
                            player=pid, choices=('use_slash', 'draw'), subject_player_id=f.local['victim'])
        if f.step_index == 5:
            choice, f.decision = f.decision, None
            f.step_index = 6
            if choice == 'draw':
                return StepResult.push(DrawCardsAction(a.action_id + ':draw', pid, 1))
            return StepResult.push(AuthorizedVirtualUse(a.action_id + ':virtual', pid,
                (f.local['victim'],), VirtualCard('basic.slash', (), None, None)))
        return StepResult.complete()

    def xianzhen(self, state, f):
        a = f.action
        if f.step_index == 0:
            self.validate_active(state, a)
            if not hand(state, a.player_id):
                raise InvalidCardUse('陷阵需要手牌')
            f.step_index = 1
            return self.ask(f, RequestType.CHOOSE_PLAYER, '【陷阵】选择拼点目标',
                allowed_player_ids=tuple(q for q in state.seat_order if q != a.player_id
                    and state.players[q].is_alive and hand(state, q)))
        if f.step_index == 1:
            target, f.decision = f.decision, None
            f.local['opponent'] = target
            state.play_usage.record('skill.xianzhen')
            f.step_index = 2
            return StepResult.push(PindianAction(a.action_id + ':pindian', a.player_id, target))
        key = 'yj_xianzhen:' + f.local['opponent'] if f.child_result is True else 'yj_xianzhen_loss'
        state.players[a.player_id].marks[key] = state.turn_number
        return StepResult.complete()


def play_options(state, pid, skills):
    result = []
    p = state.players[pid]
    if skills.has(state, pid, 'jiushi') and p.face_up and not state.play_usage.count('basic.wine'):
        result.append('skill:jiushi')
    for name, legal in (
        ('xinzhan', len(hand(state, pid)) > p.max_hp),
        ('ganlu', any(q != pid and state.players[q].is_alive for q in state.seat_order)),
        ('mingce', any(state.cards[cid].definition_id in SLASH or str(state.cards[cid].definition_id).startswith('equipment.')
                       for cid in discardable(state, pid))),
        ('xianzhen', bool(hand(state, pid)) and any(q != pid and state.players[q].is_alive and hand(state, q) for q in state.seat_order)),
    ):
        if legal and skills.has(state, pid, name) and not state.play_usage.count('skill.' + name):
            result.append('skill:' + name)
    return result


def reactions(state, event, skills):
    result = []
    qualifying = ()
    owner = None
    if isinstance(event, CardMovedEvent):
        owner = event.from_zone.player_id
        if (event.to_zone.zone_type is ZoneType.DISCARD_PILE and event.reason == 'discard'
                and owner is not None):
            qualifying = event.card_ids
        recipient = event.to_zone.player_id
        if (event.to_zone.zone_type is ZoneType.HAND and recipient is not None
                and owner is not None and owner != recipient and len(event.card_ids) >= 2
                and not (event.related_action_id or '').startswith('acquisition:')
                and state.players[recipient].is_alive and skills.has(state, recipient, 'enyuan')):
            result.append(YJSkillAction(event.event_id + ':enyuan', recipient, 'enyuan_gain', owner))
    elif isinstance(event, Event) and event.event_type == 'cards_obtained':
        owner, recipient = event.metadata['from_player_id'], event.source_id
        if owner != recipient and event.metadata['count'] >= 2 and state.players[recipient].is_alive and skills.has(state, recipient, 'enyuan'):
            result.append(YJSkillAction(event.event_id + ':enyuan', recipient, 'enyuan_gain', owner))
    elif isinstance(event, Event) and event.event_type == 'after_judgment':
        owner = event.source_id
        qualifying = (event.metadata['card_id'],)
    if qualifying:
        for pid in state.seat_order:
            if pid != owner and state.players[pid].is_alive and skills.has(state, pid, 'luoying'):
                cards = tuple(cid for cid in qualifying if state.cards[cid].suit is Suit.CLUB
                              and cid in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
                if cards:
                    result.append(YJSkillAction(event.event_id + ':luoying:' + pid, pid, 'luoying', card_ids=cards))
    return result


def damage_reaction(state, f, skills):
    if f.step_index != 1 or skills is None:
        return None
    a = f.action
    if not state.players[a.target_id].is_alive:
        return None
    if not f.local.get('yj_enyuan_done'):
        f.local['yj_enyuan_done'] = True
        if a.source_id is not None and a.source_id != a.target_id and skills.has(state, a.target_id, 'enyuan'):
            return StepResult.push(YJSkillAction(a.action_id + ':enyuan', a.target_id, 'enyuan_damage',
                a.source_id, amount=int(f.local['amount'])))
    if not f.local.get('yj_jiushi_done'):
        f.local['yj_jiushi_done'] = True
        if f.local.get('yj_face_down_before') and skills.has(state, a.target_id, 'jiushi'):
            return StepResult.push(YJSkillAction(a.action_id + ':jiushi-return', a.target_id, 'jiushi_return'))
    return None


def register(registry, skills, moves, definitions, deck):
    registry.register(YJSkillAction, YJSkillHandler(skills, moves, definitions, deck))
    registry.register(AuthorizedVirtualUse, AuthorizedVirtualUseHandler(skills, definitions, moves.recorder))

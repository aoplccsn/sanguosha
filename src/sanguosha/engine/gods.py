"""Classic God general rules using the shared card and death pipelines."""

from dataclasses import dataclass
from itertools import combinations

from sanguosha.model.enums import DamageNature, Phase, Suit
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard

from .yj2011_tier3 import record_slash_use
from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .judgment import JudgmentAction, JudgmentPattern
from .deck import RevealTopCardsAction
from .recovery import RecoverAction
from .hp import LoseHpAction
from .hp import LoseMaxHpAction
from .military_basics import MilitaryDamageAction
from .forced_cards import discardable_cards
from .military_basics import SlashSequence
from .requests import PendingRequest, RequestType
from .suits import effective_color, effective_suit
from .events import CardUsedEvent


@dataclass(frozen=True, slots=True)
class WushenUse(Action):
    player_id: str
    material_id: str


class WushenHandler:
    def __init__(self, skills, moves, slash_rule):
        self.skills = skills
        self.moves = moves
        self.slash_rule = slash_rule

    def materials(self, state, player_id):
        return tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                     if effective_suit(state, cid, player_id) is Suit.HEART)

    def targets(self, state, player_id):
        return tuple(pid for pid in state.seat_order
                     if pid != player_id and state.players[pid].is_alive
                     and not (self.skills.has(state, pid, 'kongcheng')
                              and not state.cards_in(ZoneRef(ZoneType.HAND, pid))))

    def available(self, state, player_id, material_id=None):
        limit = self.slash_rule.usage_limit(state, player_id)
        return (self.skills.has(state, player_id, 'wushen')
                and state.current_player_id == player_id
                and state.current_phase is Phase.PLAY
                and state.play_usage is not None
                and (limit is None or state.play_usage.count('basic.slash') < limit)
                and (material_id is None and bool(self.materials(state, player_id))
                     or material_id in self.materials(state, player_id))
                and bool(self.targets(state, player_id)))

    def step(self, state, frame):
        action = frame.action
        actor = action.player_id
        if frame.step_index == 0:
            if not self.available(state, actor, action.material_id):
                raise InvalidCardUse('武神当前不可用')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':target', actor, RequestType.CHOOSE_PLAYER,
                '武神：选择一名【杀】的目标（无距离限制）',
                action.action_id, frame.frame_id,
                allowed_player_ids=self.targets(state, actor)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            if not self.available(state, actor, action.material_id) or target not in self.targets(state, actor):
                raise InvalidCardUse('武神目标不合法')
            virtual = VirtualCard('basic.slash', (action.material_id,),
                                  effective_suit(state, action.material_id, actor),
                                  effective_color(state, action.material_id, actor))
            self.moves.move(state, CardMove(
                action.action_id + ':processing', (action.material_id,),
                ZoneRef(ZoneType.HAND, actor), ZoneRef(ZoneType.PROCESSING),
                CardMoveReason.USE, actor, action.action_id))
            record_slash_use(state, actor, (target,))
            frame.step_index = 2
            return StepResult.push(SlashSequence(
                action.action_id + ':slash', actor, action.material_id,
                (target,), virtual))
        if action.material_id in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
            self.moves.move(state, CardMove(
                action.action_id + ':discard', (action.material_id,),
                ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.USE, actor, action.action_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class WuhunDeathAction(Action):
    player_id: str


class WuhunDeathHandler:
    def __init__(self, skills):
        self.skills = skills

    def candidates(self, state):
        living = tuple(pid for pid in state.seat_order if state.players[pid].is_alive)
        maximum = max((state.players[pid].marks.get('nightmare', 0) for pid in living), default=0)
        return tuple(pid for pid in living
                     if maximum > 0 and state.players[pid].marks.get('nightmare', 0) == maximum)

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            candidates = self.candidates(state)
            if not candidates:
                return StepResult.complete()
            if len(candidates) == 1:
                frame.local['target'] = candidates[0]
                frame.step_index = 2
            else:
                frame.step_index = 1
                return StepResult.ask(PendingRequest(
                    action.action_id + ':tie', action.player_id, RequestType.CHOOSE_PLAYER,
                    '武魂：选择梦魇标记最多的角色', action.action_id,
                    frame.frame_id, allowed_player_ids=candidates))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            if target not in self.candidates(state):
                raise InvalidCardUse('武魂目标不合法')
            frame.local['target'] = target
            frame.step_index = 2
        if frame.step_index == 2:
            target = frame.local['target']
            if not state.players[target].is_alive:
                return StepResult.complete()
            frame.step_index = 3
            return StepResult.push(JudgmentAction(
                action.action_id + ':judgment', target,
                JudgmentPattern(), return_card_id=True))
        if frame.step_index == 3:
            card_id = frame.child_result
            if state.cards[card_id].definition_id == 'basic.peach':
                return StepResult.complete()
            target = frame.local['target']
            if state.players[target].is_alive:
                from .death import DeathAction
                frame.step_index = 4
                return StepResult.push(DeathAction(
                    action.action_id + ':death', target, None))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class ShelieAction(Action):
    player_id: str


class ShelieHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def step(self, state, frame):
        actor = frame.action.player_id
        if not self.skills.has(state, actor, 'shelie') or not state.players[actor].is_alive:
            return StepResult.complete()
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':offer', actor, RequestType.YES_NO,
                '是否发动【涉猎】替代摸牌？', frame.action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            state.players[actor].marks['skip_draw'] = 1
            frame.step_index = 2
            return StepResult.push(RevealTopCardsAction(
                frame.action.action_id + ':reveal', actor, 5))
        if frame.step_index == 2:
            frame.local['remaining'] = tuple(frame.child_result or ())
            frame.local['selected_suits'] = ()
            frame.step_index = 3
        if frame.step_index == 3:
            remaining = frame.local['remaining']
            suits = frame.local['selected_suits']
            choices = tuple(cid for cid in remaining
                            if effective_suit(state, cid, actor).value not in suits)
            if not choices:
                for index, cid in enumerate(remaining):
                    if cid in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
                        self.moves.move(state, CardMove(
                            f'{frame.action.action_id}:discard:{index}', (cid,),
                            ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.DISCARD_PILE),
                            CardMoveReason.SYSTEM, actor, frame.action.action_id))
                return StepResult.complete()
            frame.step_index = 4
            return StepResult.ask(PendingRequest(
                frame.action.action_id + f':pick:{len(suits)}', actor,
                RequestType.CHOOSE_OPTION, '涉猎：每种花色最多获得一张牌',
                frame.action.action_id, frame.frame_id, choices=(*choices, 'done')))
        choice = frame.decision
        frame.decision = None
        if choice == 'done':
            frame.local['selected_suits'] = ('heart', 'diamond', 'club', 'spade')
            frame.step_index = 3
            return StepResult.continue_()
        if (choice not in frame.local['remaining']
                or effective_suit(state, choice, actor).value in frame.local['selected_suits']):
            raise InvalidCardUse('涉猎选择不合法')
        self.moves.move(state, CardMove(
            frame.action.action_id + f':gain:{len(frame.local["selected_suits"])}',
            (choice,), ZoneRef(ZoneType.PROCESSING), ZoneRef(ZoneType.HAND, actor),
            CardMoveReason.SYSTEM, actor, frame.action.action_id))
        frame.local['remaining'] = tuple(cid for cid in frame.local['remaining'] if cid != choice)
        frame.local['selected_suits'] = (*frame.local['selected_suits'],
                                         effective_suit(state, choice, actor).value)
        frame.step_index = 3
        return StepResult.continue_()


@dataclass(frozen=True, slots=True)
class GongxinAction(Action):
    player_id: str


class GongxinHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def targets(self, state, actor):
        return tuple(pid for pid in state.seat_order
                     if pid != actor and state.players[pid].is_alive
                     and state.cards_in(ZoneRef(ZoneType.HAND, pid)))

    def available(self, state, actor):
        return (self.skills.has(state, actor, 'gongxin')
                and state.current_player_id == actor
                and state.current_phase is Phase.PLAY
                and state.play_usage is not None
                and not state.play_usage.count('skill.gongxin')
                and bool(self.targets(state, actor)))

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 0:
            if not self.available(state, actor):
                raise InvalidCardUse('攻心当前不可用')
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':target', actor, RequestType.CHOOSE_PLAYER,
                '攻心：选择要查看手牌的角色', frame.action.action_id,
                frame.frame_id, allowed_player_ids=self.targets(state, actor)))
        if frame.step_index == 1:
            target = frame.decision
            frame.decision = None
            if not self.available(state, actor) or target not in self.targets(state, actor):
                raise InvalidCardUse('攻心目标不合法')
            state.play_usage.record('skill.gongxin')
            frame.local['target'] = target
            state.metadata['gongxin_reveal'] = {'actor': actor, 'target': target}
            heart = tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, target))
                          if effective_suit(state, cid, target) is Suit.HEART)
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':heart', actor, RequestType.CHOOSE_OPTION,
                '攻心：查看目标手牌，选择一张红桃或放弃',
                frame.action.action_id, frame.frame_id,
                choices=(*heart, 'done'), subject_player_id=target))
        if frame.step_index == 2:
            choice = frame.decision
            frame.decision = None
            if choice == 'done':
                state.metadata.pop('gongxin_reveal', None)
                return StepResult.complete()
            target = frame.local['target']
            if (choice not in state.cards_in(ZoneRef(ZoneType.HAND, target))
                    or effective_suit(state, choice, target) is not Suit.HEART):
                raise InvalidCardUse('攻心所选红桃牌已不可用')
            frame.local['card'] = choice
            frame.step_index = 3
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':mode', actor, RequestType.CHOOSE_OPTION,
                '攻心：弃置或置于牌堆顶', frame.action.action_id,
                frame.frame_id, choices=('discard', 'top')))
        target = frame.local['target']
        card = frame.local['card']
        mode = frame.decision
        frame.decision = None
        if card not in state.cards_in(ZoneRef(ZoneType.HAND, target)):
            raise InvalidCardUse('攻心红桃牌已离开手牌')
        destination = (ZoneRef(ZoneType.DISCARD_PILE) if mode == 'discard'
                       else ZoneRef(ZoneType.DRAW_PILE))
        self.moves.move(state, CardMove(
            frame.action.action_id + ':move', (card,), ZoneRef(ZoneType.HAND, target),
            destination, CardMoveReason.SYSTEM, actor, frame.action.action_id,
            to_top=mode == 'top'))
        state.metadata.pop('gongxin_reveal', None)
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class QinyinAction(Action):
    player_id: str


class QinyinHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 0:
            if not state.players[actor].is_alive or not self.skills.has(state, actor, 'qinyin'):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':offer', actor, RequestType.YES_NO,
                '弃牌阶段弃置至少两张牌，是否发动【琴音】？',
                frame.action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':mode', actor, RequestType.CHOOSE_OPTION,
                '琴音：所有角色回复一点体力或失去一点体力',
                frame.action.action_id, frame.frame_id,
                choices=('recover', 'lose_hp')))
        if frame.step_index == 2:
            frame.local['mode'] = frame.decision
            frame.decision = None
            frame.local['targets'] = tuple(pid for pid in state.seat_order
                                           if state.players[pid].is_alive)
            frame.step_index = 3
        if frame.step_index == 3:
            targets = frame.local['targets']
            if frame.cursor >= len(targets):
                return StepResult.complete()
            target = targets[frame.cursor]
            frame.cursor += 1
            if not state.players[target].is_alive:
                return StepResult.continue_()
            if frame.local['mode'] == 'recover':
                return StepResult.push(RecoverAction(
                    frame.action.action_id + f':recover:{frame.cursor}', actor, target, 1))
            return StepResult.push(LoseHpAction(
                frame.action.action_id + f':lose:{frame.cursor}', target, 1))
        return StepResult.continue_()


@dataclass(frozen=True, slots=True)
class YeyanAction(Action):
    player_id: str


class YeyanHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def targets(self, state, actor):
        return tuple(pid for pid in state.seat_order
                     if pid != actor and state.players[pid].is_alive)

    def suit_costs(self, state, actor):
        cards = discardable_cards(state, actor)
        return {suit: tuple(cid for cid in cards
                            if effective_suit(state, cid, actor) is suit)
                for suit in (Suit.HEART, Suit.DIAMOND, Suit.CLUB, Suit.SPADE)}

    def available(self, state, actor):
        targets = self.targets(state, actor)
        can_great = all(self.suit_costs(state, actor).values())
        return (self.skills.has(state, actor, 'yeyan')
                and state.current_player_id == actor
                and state.current_phase is Phase.PLAY
                and state.play_usage is not None
                and not state.players[actor].marks.get('yeyan_used')
                and bool(targets) and (len(targets) >= 3 or can_great))

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 0:
            if not self.available(state, actor):
                raise InvalidCardUse('业炎当前不可用')
            frame.step_index = 1
            modes = (('small',) if len(self.targets(state, actor)) >= 3 else ())
            if all(self.suit_costs(state, actor).values()):
                modes += ('great',)
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':mode', actor, RequestType.CHOOSE_OPTION,
                '业炎：选择小业炎或大业炎', frame.action.action_id,
                frame.frame_id, choices=modes))
        if frame.step_index == 1:
            mode = frame.decision
            frame.decision = None
            frame.local['mode'] = mode
            if mode == 'small':
                targets = self.targets(state, actor)
                if len(targets) < 3:
                    raise InvalidCardUse('小业炎需要三名目标')
                frame.step_index = 2
                return StepResult.ask(PendingRequest(
                    frame.action.action_id + ':small-targets', actor,
                    RequestType.CHOOSE_PLAYERS, '小业炎：选择三名目标，各造成一点火焰伤害',
                    frame.action.action_id, frame.frame_id,
                    allowed_player_ids=targets, min_count=3, max_count=3))
            if mode != 'great' or not all(self.suit_costs(state, actor).values()):
                raise InvalidCardUse('大业炎花色代价不足')
            frame.step_index = 3
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':great-first', actor, RequestType.CHOOSE_PLAYER,
                '大业炎：选择受到两点火焰伤害的角色',
                frame.action.action_id, frame.frame_id,
                allowed_player_ids=self.targets(state, actor)))
        if frame.step_index == 2:
            targets = tuple(frame.decision)
            frame.decision = None
            if len(set(targets)) != 3 or any(pid not in self.targets(state, actor) for pid in targets):
                raise InvalidCardUse('小业炎目标不合法')
            frame.local['damage_targets'] = targets
            frame.step_index = 8
        if frame.step_index == 3:
            first = frame.decision
            frame.decision = None
            if first not in self.targets(state, actor):
                raise InvalidCardUse('大业炎目标不合法')
            frame.local['first'] = first
            frame.step_index = 4
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':great-second', actor, RequestType.CHOOSE_PLAYER,
                '大业炎：选择受到剩余一点火焰伤害的角色',
                frame.action.action_id, frame.frame_id,
                allowed_player_ids=self.targets(state, actor)))
        if frame.step_index == 4:
            second = frame.decision
            frame.decision = None
            if second not in self.targets(state, actor):
                raise InvalidCardUse('大业炎第二目标不合法')
            frame.local['damage_targets'] = (frame.local['first'], frame.local['first'], second)
            frame.local['cost_cards'] = ()
            frame.local['suit_index'] = 0
            frame.step_index = 5
        if frame.step_index == 5:
            suits = (Suit.HEART, Suit.DIAMOND, Suit.CLUB, Suit.SPADE)
            index = frame.local['suit_index']
            if index >= len(suits):
                frame.step_index = 7
            else:
                suit = suits[index]
                choices = self.suit_costs(state, actor)[suit]
                if not choices:
                    raise InvalidCardUse('大业炎花色代价已不可用')
                frame.step_index = 6
                return StepResult.ask(PendingRequest(
                    frame.action.action_id + f':cost:{suit.value}', actor,
                    RequestType.CHOOSE_CARD, f'大业炎：弃置一张{suit.value}牌',
                    frame.action.action_id, frame.frame_id,
                    eligible_card_ids=choices))
        if frame.step_index == 6:
            card_id = frame.decision
            frame.decision = None
            suits = (Suit.HEART, Suit.DIAMOND, Suit.CLUB, Suit.SPADE)
            suit = suits[frame.local['suit_index']]
            if card_id not in self.suit_costs(state, actor)[suit]:
                raise InvalidCardUse('大业炎花色代价不合法')
            source = next(ref for ref, zone in state.zones.items()
                          if ref.player_id == actor and card_id in zone.card_ids)
            self.moves.move(state, CardMove(
                frame.action.action_id + f':cost:{suit.value}', (card_id,), source,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
                actor, frame.action.action_id))
            frame.local['suit_index'] += 1
            frame.step_index = 5
            return StepResult.continue_()
        if frame.step_index == 7:
            frame.step_index = 8
            return StepResult.push(LoseHpAction(
                frame.action.action_id + ':hp-cost', actor, 3))
        if frame.step_index == 8:
            state.players[actor].marks['yeyan_used'] = 1
            state.play_usage.record('skill.yeyan')
            frame.step_index = 9
        if frame.step_index == 9:
            targets = frame.local['damage_targets']
            if frame.cursor >= len(targets) or state.status.value == 'finished':
                return StepResult.complete()
            target = targets[frame.cursor]
            frame.cursor += 1
            amount = 1
            while frame.cursor < len(targets) and targets[frame.cursor] == target:
                amount += 1
                frame.cursor += 1
            if not state.players[target].is_alive:
                return StepResult.continue_()
            return StepResult.push(MilitaryDamageAction(
                frame.action.action_id + f':fire:{frame.cursor}', actor, target,
                amount, DamageNature.FIRE))
        return StepResult.continue_()


@dataclass(frozen=True, slots=True)
class GuixinAction(Action):
    player_id: str


class GuixinHandler:
    def __init__(self, skills, moves):
        self.skills = skills
        self.moves = moves

    def candidates(self, state, actor, target):
        return tuple(cid for ref, zone in state.zones.items()
                     if ref.player_id == target and ref.zone_type in
                     (ZoneType.HAND, ZoneType.EQUIPMENT, ZoneType.JUDGMENT)
                     for cid in zone.card_ids)

    def step(self, state, frame):
        actor = frame.action.player_id
        if frame.step_index == 0:
            if not state.players[actor].is_alive or not self.skills.has(state, actor, 'guixin'):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':offer', actor, RequestType.YES_NO,
                '是否发动【归心】，从每名其他角色处获得一张牌并翻面？',
                frame.action.action_id, frame.frame_id))
        if frame.step_index == 1:
            wanted = frame.decision is True
            frame.decision = None
            if not wanted:
                return StepResult.complete()
            frame.local['targets'] = tuple(pid for pid in state.seat_order
                                           if pid != actor and state.players[pid].is_alive)
            frame.step_index = 2
        if frame.step_index == 2:
            targets = frame.local['targets']
            if frame.cursor >= len(targets):
                frame.step_index = 4
            else:
                target = targets[frame.cursor]
                if not state.players[target].is_alive or not self.candidates(state, actor, target):
                    frame.cursor += 1
                    return StepResult.continue_()
                frame.local['target'] = target
                frame.step_index = 3
                return StepResult.ask(PendingRequest(
                    frame.action.action_id + f':card:{frame.cursor}', actor,
                    RequestType.CHOOSE_CARD, '归心：选择获得该角色的一张牌',
                    frame.action.action_id, frame.frame_id,
                    eligible_card_ids=self.candidates(state, actor, target),
                    subject_player_id=target))
        if frame.step_index == 3:
            target = frame.local['target']
            card = frame.decision
            frame.decision = None
            if card not in self.candidates(state, actor, target):
                raise InvalidCardUse('归心目标牌已不可用')
            source = next(ref for ref, zone in state.zones.items()
                          if ref.player_id == target and card in zone.card_ids)
            self.moves.move(state, CardMove(
                frame.action.action_id + f':gain:{frame.cursor}', (card,), source,
                ZoneRef(ZoneType.HAND, actor), CardMoveReason.SYSTEM,
                actor, frame.action.action_id))
            frame.cursor += 1
            frame.step_index = 2
            return StepResult.continue_()
        if frame.step_index == 4:
            from .turnover import TurnoverAction
            frame.step_index = 5
            return StepResult.push(TurnoverAction(frame.action.action_id + ':turnover', actor))
        return StepResult.complete()


def star_zone(player_id):
    return ZoneRef(ZoneType.SPECIAL, player_id, special_key='star')


LONGHUN_SUIT = {
    'basic.peach': Suit.HEART,
    'basic.fire_slash': Suit.DIAMOND,
    'basic.dodge': Suit.CLUB,
    'trick.nullification': Suit.SPADE,
}


def longhun_materials(state, actor, definition_id):
    suit = LONGHUN_SUIT[definition_id]
    required = max(1, state.players[actor].hp)
    cards = tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, actor))
                  if effective_suit(state, cid, actor) is suit)
    return tuple(combinations(cards, required))


def longhun_option(cards):
    return 'virtual:longhun:' + ':'.join(cards)


@dataclass(frozen=True, slots=True)
class LonghunUse(Action):
    player_id: str
    material_ids: tuple[str, ...]
    definition_id: str


class LonghunUseHandler:
    def __init__(self, skills, moves, recorder, slash_rule):
        self.skills, self.moves, self.recorder, self.slash_rule = (
            skills, moves, recorder, slash_rule)

    def available(self, state, actor, definition_id, materials):
        if (not self.skills.has(state, actor, 'longhun')
                or state.current_player_id != actor
                or state.current_phase is not Phase.PLAY
                or state.play_usage is None
                or tuple(materials) not in longhun_materials(state, actor, definition_id)):
            return False
        if definition_id == 'basic.peach':
            return state.players[actor].hp < state.players[actor].max_hp
        if definition_id != 'basic.fire_slash':
            return False
        limit = self.slash_rule.usage_limit(state, actor)
        return ((limit is None or state.play_usage.count('basic.slash') < limit)
                and bool(self.slash_rule.target_candidates(state, actor)))

    def step(self, state, frame):
        action = frame.action
        actor = action.player_id
        hand = ZoneRef(ZoneType.HAND, actor)
        processing = ZoneRef(ZoneType.PROCESSING)
        if frame.step_index == 0:
            if not self.available(state, actor, action.definition_id, action.material_ids):
                raise InvalidCardUse('龙魂出牌不可用')
            if action.definition_id == 'basic.fire_slash':
                frame.step_index = 1
                return StepResult.ask(PendingRequest(
                    action.action_id + ':target', actor, RequestType.CHOOSE_PLAYER,
                    '龙魂：选择火杀目标', action.action_id, frame.frame_id,
                    allowed_player_ids=self.slash_rule.target_candidates(state, actor)))
            frame.step_index = 1
            frame.local['target'] = actor
        if frame.step_index == 1:
            target = frame.local.get('target', frame.decision)
            frame.decision = None
            if not self.available(state, actor, action.definition_id, action.material_ids):
                raise InvalidCardUse('龙魂材料已失效')
            if action.definition_id == 'basic.fire_slash':
                self.slash_rule.validate_targets(state, actor, (target,))
                record_slash_use(state, actor, (target,))
            frame.local['target'] = target
            self.moves.move(state, CardMove(action.action_id + ':processing',
                action.material_ids, hand, processing, CardMoveReason.USE,
                actor, action.action_id))
            self.recorder.record(CardUsedEvent(action.action_id + ':used', actor,
                action.material_ids[0], (target,), action.definition_id))
            frame.step_index = 2
            if action.definition_id == 'basic.peach':
                return StepResult.push(RecoverAction(
                    action.action_id + ':recover', actor, actor, 1))
            virtual = VirtualCard(action.definition_id, action.material_ids,
                effective_suit(state, action.material_ids[0], actor),
                effective_color(state, action.material_ids[0], actor))
            return StepResult.push(SlashSequence(
                action.action_id + ':slash', actor, action.material_ids[0],
                (target,), virtual))
        still_processing = tuple(cid for cid in action.material_ids
                                 if cid in state.cards_in(processing))
        if still_processing:
            self.moves.move(state, CardMove(action.action_id + ':discard',
                still_processing, processing, ZoneRef(ZoneType.DISCARD_PILE),
                CardMoveReason.USE, actor, action.action_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class QixingExchangeAction(Action):
    player_id: str


class QixingExchangeHandler:
    def __init__(self, skills, moves):
        self.skills, self.moves = skills, moves

    def step(self, state, frame):
        actor = frame.action.player_id
        hand = ZoneRef(ZoneType.HAND, actor)
        stars = star_zone(actor)
        if frame.step_index == 0:
            if not self.skills.has(state, actor, 'qixing') or not state.cards_in(stars):
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':hand', actor, RequestType.CHOOSE_CARDS,
                '七星：选择要与星交换的手牌，可不交换',
                frame.action.action_id, frame.frame_id,
                eligible_card_ids=state.cards_in(hand), min_count=0,
                max_count=min(len(state.cards_in(hand)), len(state.cards_in(stars)))))
        if frame.step_index == 1:
            selected = tuple(frame.decision)
            frame.decision = None
            if not selected:
                return StepResult.complete()
            if len(set(selected)) != len(selected) or any(cid not in state.cards_in(hand) for cid in selected):
                raise InvalidCardUse('七星手牌选择不合法')
            frame.local['hand_cards'] = selected
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':stars', actor, RequestType.CHOOSE_CARDS,
                '七星：选择等量的星牌换入手牌',
                frame.action.action_id, frame.frame_id,
                eligible_card_ids=state.cards_in(stars),
                min_count=len(selected), max_count=len(selected)))
        selected_stars = tuple(frame.decision)
        selected_hand = frame.local['hand_cards']
        frame.decision = None
        if (len(selected_stars) != len(selected_hand) or len(set(selected_stars)) != len(selected_stars)
                or any(cid not in state.cards_in(stars) for cid in selected_stars)
                or any(cid not in state.cards_in(hand) for cid in selected_hand)):
            raise InvalidCardUse('七星交换牌已失效')
        self.moves.move(state, CardMove(frame.action.action_id + ':out', selected_hand,
            hand, stars, CardMoveReason.SYSTEM, actor, frame.action.action_id))
        self.moves.move(state, CardMove(frame.action.action_id + ':in', selected_stars,
            stars, hand, CardMoveReason.SYSTEM, actor, frame.action.action_id))
        return StepResult.complete()


@dataclass(frozen=True, slots=True)
class StarWeatherAction(Action):
    player_id: str


class StarWeatherHandler:
    def __init__(self, skills, moves):
        self.skills, self.moves = skills, moves

    def step(self, state, frame):
        actor = frame.action.player_id
        stars = star_zone(actor)
        if not self.skills.has(state, actor, 'qixing') or not state.players[actor].is_alive:
            return StepResult.complete()
        if frame.step_index == 0:
            available = []
            if state.cards_in(stars):
                if not frame.local.get('wind_used'):
                    available.append('wind')
                if not frame.local.get('fog_used'):
                    available.append('fog')
            if not available:
                return StepResult.complete()
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                frame.action.action_id + f':mode:{len(frame.local)}', actor,
                RequestType.CHOOSE_OPTION, '七星：发动狂风或大雾',
                frame.action.action_id, frame.frame_id,
                choices=(*available, 'done')))
        if frame.step_index == 1:
            mode = frame.decision
            frame.decision = None
            if mode == 'done':
                return StepResult.complete()
            if mode not in ('wind', 'fog') or frame.local.get(mode + '_used'):
                raise InvalidCardUse('七星天气选择不合法')
            frame.local['mode'] = mode
            targets = tuple(pid for pid in state.seat_order if state.players[pid].is_alive)
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                frame.action.action_id + f':targets:{mode}', actor,
                RequestType.CHOOSE_PLAYERS, '狂风指定一名角色；大雾指定至多星数名角色',
                frame.action.action_id, frame.frame_id,
                allowed_player_ids=targets, min_count=1,
                max_count=1 if mode == 'wind' else min(len(targets), len(state.cards_in(stars)))))
        if frame.step_index == 2:
            targets = tuple(frame.decision)
            frame.decision = None
            living = {pid for pid in state.seat_order if state.players[pid].is_alive}
            if (not targets or len(set(targets)) != len(targets)
                    or any(pid not in living for pid in targets)
                    or len(targets) > len(state.cards_in(stars))
                    or (frame.local['mode'] == 'wind' and len(targets) != 1)):
                raise InvalidCardUse('七星天气目标不合法')
            frame.local['targets'] = targets
            frame.step_index = 3
            return StepResult.ask(PendingRequest(
                frame.action.action_id + ':cost:' + frame.local['mode'], actor,
                RequestType.CHOOSE_CARDS, '弃置与目标数量相同的星牌',
                frame.action.action_id, frame.frame_id,
                eligible_card_ids=state.cards_in(stars),
                min_count=len(targets), max_count=len(targets)))
        cards = tuple(frame.decision)
        frame.decision = None
        targets = frame.local['targets']
        if (len(cards) != len(targets) or len(set(cards)) != len(cards)
                or any(cid not in state.cards_in(stars) for cid in cards)):
            raise InvalidCardUse('七星天气星牌代价不合法')
        self.moves.move(state, CardMove(
            frame.action.action_id + ':discard:' + frame.local['mode'], cards,
            stars, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
            actor, frame.action.action_id))
        for target in targets:
            state.players[target].marks[frame.local['mode'] + ':' + actor] = 1
        frame.local[frame.local['mode'] + '_used'] = True
        frame.step_index = 0
        return StepResult.continue_()


@dataclass(frozen=True, slots=True)
class BaiyinAction(Action):
    player_id: str


class BaiyinHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        actor = frame.action.player_id
        player = state.players[actor]
        if frame.step_index == 0:
            if (not player.is_alive or not self.skills.has(state, actor, 'baoyin')
                    or player.marks.get('awakened_baiyin')
                    or player.marks.get('ren', 0) < 4):
                return StepResult.complete(False)
            player.marks['awakened_baiyin'] = 1
            frame.step_index = 1
            return StepResult.push(LoseMaxHpAction(
                frame.action.action_id + ':max-hp', actor, 1))
        if player.is_alive:
            player.granted_skills['jilue'] = 'baoyin'
        return StepResult.complete(player.is_alive)


@dataclass(frozen=True, slots=True)
class JiluePlayAction(Action):
    player_id: str
    mode: str


class JiluePlayHandler:
    def __init__(self, skills):
        self.skills = skills

    def step(self, state, frame):
        action = frame.action
        actor = action.player_id
        player = state.players[actor]
        if frame.step_index == 0:
            if (not self.skills.has(state, actor, 'jilue')
                    or player.marks.get('ren', 0) < 1
                    or state.current_player_id != actor
                    or state.current_phase is not Phase.PLAY
                    or state.play_usage is None):
                raise InvalidCardUse('极略当前不可用')
            if action.mode == 'zhiheng':
                if state.play_usage.count('skill.zhiheng'):
                    raise InvalidCardUse('极略制衡本阶段已用')
                player.marks['ren'] -= 1
                from .skills import ZhihengAction
                frame.step_index = 1
                return StepResult.push(ZhihengAction(action.action_id + ':zhiheng', actor))
            if action.mode == 'wansha':
                if player.marks.get('jilue_wansha'):
                    raise InvalidCardUse('本回合已发动极略完杀')
                player.marks['ren'] -= 1
                player.marks['jilue_wansha'] = 1
                return StepResult.complete()
            raise InvalidCardUse('极略模式不合法')
        return StepResult.complete(frame.child_result)

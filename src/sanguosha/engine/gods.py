"""Classic God general rules using the shared card and death pipelines."""

from dataclasses import dataclass

from sanguosha.model.enums import Phase, Suit
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .judgment import JudgmentAction, JudgmentPattern
from .deck import RevealTopCardsAction
from .recovery import RecoverAction
from .hp import LoseHpAction
from .military_basics import SlashSequence
from .requests import PendingRequest, RequestType
from .suits import effective_color, effective_suit


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
            state.play_usage.record('basic.slash')
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
            heart = tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND, target))
                          if effective_suit(state, cid, target) is Suit.HEART)
            if not heart:
                return StepResult.complete()
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

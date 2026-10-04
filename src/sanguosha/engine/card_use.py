"""Generic active card-use lifecycle and play option adapter."""

from dataclasses import dataclass

from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.enums import CardCategory, Identity
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .card_rules import CardRule, CardUseValidator, InvalidCardUse
from .events import CardResolvedEvent, CardUsedEvent, EventRecorder
from .deck import DrawCardsAction
from .requests import PendingRequest, RequestType
from .resolution import ResolutionFrame


@dataclass(frozen=True, slots=True)
class UseCardAction(Action):
    user_id: PlayerId
    card_id: CardInstanceId
    target_ids: tuple[PlayerId, ...] = ()
    forced: bool = False
    targets_confirmed: bool = False


class UseCardActionHandler:
    def __init__(self, validator: CardUseValidator, moves: CardMoveService, recorder: EventRecorder,
                 skills=None) -> None:
        self.validator = validator
        self.moves = moves
        self.recorder = recorder
        self.skills = skills

    def _rule_for_action(self, state: GameState, action: UseCardAction):
        if not action.forced:
            return self.validator.validate_card(state, action.user_id, action.card_id)
        if (action.user_id not in state.players or not state.players[action.user_id].is_alive
                or action.card_id not in state.cards_in(ZoneRef(ZoneType.HAND, action.user_id))):
            raise InvalidCardUse('forced-use card is unavailable')
        rule = self.validator.rule_for(state, action.card_id, action.user_id)
        if not rule.can_use(state, action.user_id):
            raise InvalidCardUse('forced-use card condition is not met')
        return rule

    def validate_start(self, state: GameState, action: Action) -> None:
        assert isinstance(action, UseCardAction)
        rule = self._rule_for_action(state, action)
        if action.target_ids:
            self.validator.validate_targets_for_card(rule, state, action.user_id,
                                                     action.card_id, action.target_ids)
        elif not rule.requires_target_selection or action.targets_confirmed:
            self.validator.validate_targets_for_card(rule, state, action.user_id,
                                                     action.card_id, ())
        elif not self.validator.target_candidates(state, action.user_id, action.card_id):
            raise InvalidCardUse("no legal target")

    def _commit(self, state: GameState, action: UseCardAction, targets: tuple[PlayerId, ...]) -> StepResult:
        rule = self._rule_for_action(state, action)
        self.validator.validate_targets_for_card(rule, state, action.user_id,
                                                 action.card_id, targets)
        effect = rule.effect_action(f"{action.action_id}:effect", action.user_id, action.card_id, targets)
        hand = ZoneRef(ZoneType.HAND, action.user_id)
        processing = ZoneRef(ZoneType.PROCESSING)
        self.moves.move(state, CardMove(
            f"{action.action_id}:to-processing", (action.card_id,), hand, processing,
            CardMoveReason.USE, action.user_id, action.action_id,
        ))
        if not action.forced:
            usage = state.play_usage
            assert usage is not None
            from .yj2011_tier3 import record_slash_use
            usage_key = getattr(rule, 'usage_key', state.cards[action.card_id].definition_id)
            if usage_key == 'basic.slash':
                record_slash_use(state, action.user_id, targets)
            else:
                usage.record(usage_key)
        from .yj2011_tier3 import canonical_definition
        physical = state.cards[action.card_id].definition_id
        canonical = canonical_definition(state, self.skills, action.user_id, physical)
        self.recorder.record(CardUsedEvent(f"{action.action_id}:used", action.user_id, action.card_id, targets,
            canonical if canonical != physical else ''))
        if (any(state.players[pid].identity is Identity.LORD for pid in targets)
                and str(state.cards[action.card_id].definition_id) in
                ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash',
                 'trick.duel', 'trick.snatch', 'trick.dismantlement')):
            hostility = state.metadata.setdefault('public_hostility_to_lord', {})
            hostility[action.user_id] = int(hostility.get(action.user_id, 0)) + 1
        return StepResult.push(effect)

    def _commit_with_jizhi(self, state, frame, action, targets, committed_effect=None):
        outcome = StepResult.push(committed_effect) if committed_effect is not None else self._commit(state, action, targets)
        definition = self.validator.definitions.get(state.cards[action.card_id].definition_id)
        native_jizhi = self.skills is not None and self.skills.has(state, action.user_id, 'jizhi')
        jilue_jizhi = (self.skills is not None and self.skills.has(state, action.user_id, 'jilue')
                       and state.players[action.user_id].marks.get('ren', 0) > 0)
        if (native_jizhi or jilue_jizhi) and definition.category is CardCategory.TRICK:
            frame.local['jizhi_targets'] = tuple(targets)
            frame.local['jilue_jizhi'] = not native_jizhi
            frame.step_index = 3
            return StepResult.ask(PendingRequest(
                f"{action.action_id}:jizhi", action.user_id, RequestType.YES_NO,
                '是否弃一枚忍标记发动【极略·集智】摸一张牌？' if not native_jizhi
                else '是否发动【集智】摸一张牌？', action.action_id, frame.frame_id))
        return outcome

    def _commit_with_wumou(self, state, frame, action, targets):
        definition = self.validator.definitions.get(state.cards[action.card_id].definition_id)
        if (self.skills is not None and self.skills.has(state, action.user_id, 'wumou')
                and definition.category is CardCategory.TRICK):
            committed = self._commit(state, action, targets)
            frame.local['wumou_targets'] = tuple(targets)
            frame.local['wumou_effect'] = committed.child
            frame.step_index = 5
            choices = ('lose_hp', 'rage') if state.players[action.user_id].marks.get('rage', 0) else ('lose_hp',)
            return StepResult.ask(PendingRequest(
                f'{action.action_id}:wumou', action.user_id, RequestType.CHOOSE_OPTION,
                '无谋：弃一枚怒标记或失去一点体力', action.action_id,
                frame.frame_id, choices=choices))
        return self._commit_with_jizhi(state, frame, action, targets)

    def _jizhi_effect(self, state, frame, action):
        targets = frame.local['jizhi_targets']
        rule = self.validator.rule_for(state, action.card_id, action.user_id)
        return rule.effect_action(f"{action.action_id}:effect", action.user_id, action.card_id, targets)

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, UseCardAction)
        if frame.step_index == 0:
            self.validate_start(state, action)
            rule = self.validator.rule_for(state, action.card_id, action.user_id)
            if rule.requires_target_selection and not action.target_ids and not action.targets_confirmed:
                frame.step_index = 1
                low, high = rule.target_bounds(state, action.user_id, action.card_id) if hasattr(rule, 'target_bounds') else (1, 1)
                return StepResult.ask(PendingRequest(
                    f"{action.action_id}:target", action.user_id, RequestType.CHOOSE_PLAYERS if high > 1 else RequestType.CHOOSE_PLAYER,
                    "Choose a target", action.action_id, frame.frame_id,
                    allowed_player_ids=self.validator.target_candidates(state, action.user_id,
                                                                        action.card_id),
                    min_count=low, max_count=high,
                ))
            frame.step_index = 2
            return self._commit_with_wumou(state, frame, action, action.target_ids)
        if frame.step_index == 1:
            target = frame.decision
            if not isinstance(target, (str, tuple)):
                raise InvalidCardUse("target choice is missing")
            frame.decision = None
            frame.step_index = 2
            return self._commit_with_wumou(state, frame, action,
                                           tuple(map(PlayerId, target)) if isinstance(target, tuple) else (PlayerId(target),))
        if frame.step_index == 5:
            choice = frame.decision
            frame.decision = None
            if choice == 'rage':
                if state.players[action.user_id].marks.get('rage', 0) < 1:
                    raise InvalidCardUse('无谋怒标记不足')
                state.players[action.user_id].marks['rage'] -= 1
            elif choice == 'lose_hp':
                from .hp import LoseHpAction
                frame.step_index = 6
                return StepResult.push(LoseHpAction(
                    f'{action.action_id}:wumou-hp', action.user_id, 1))
            else:
                raise InvalidCardUse('无谋代价不合法')
        if frame.step_index in (5, 6):
            if not state.players[action.user_id].is_alive:
                frame.step_index = 2
                return StepResult.continue_()
            frame.step_index = 2
            return self._commit_with_jizhi(state, frame, action,
                                           frame.local['wumou_targets'],
                                           frame.local['wumou_effect'])
        if frame.step_index == 3:
            draw = frame.decision is True
            frame.decision = None
            if draw:
                if frame.local.get('jilue_jizhi'):
                    if state.players[action.user_id].marks.get('ren', 0) < 1:
                        raise InvalidCardUse('极略忍标记不足')
                    state.players[action.user_id].marks['ren'] -= 1
                frame.step_index = 4
                return StepResult.push(DrawCardsAction(f"{action.action_id}:jizhi-draw", action.user_id, 1))
            frame.step_index = 2
            return StepResult.push(self._jizhi_effect(state, frame, action))
        if frame.step_index == 4:
            frame.step_index = 2
            return StepResult.push(self._jizhi_effect(state, frame, action))
        if frame.step_index == 2:
            processing = ZoneRef(ZoneType.PROCESSING)
            discard = ZoneRef(ZoneType.DISCARD_PILE)
            if action.card_id in state.cards_in(processing):
                self.moves.move(state, CardMove(
                    f"{action.action_id}:to-discard", (action.card_id,), processing, discard,
                    CardMoveReason.USE, action.user_id, action.action_id,
                ))
                if (self.skills is not None
                        and state.cards[action.card_id].definition_id == 'trick.savage_assault'):
                    owner = next((pid for pid in state.seat_order if pid != action.user_id
                                  and state.players[pid].is_alive
                                  and self.skills.has(state, pid, 'juxiang')), None)
                    if owner is not None and action.card_id in state.cards_in(discard):
                        self.moves.move(state, CardMove(
                            f'{action.action_id}:juxiang', (action.card_id,), discard,
                            ZoneRef(ZoneType.HAND, owner), CardMoveReason.SYSTEM,
                            owner, action.action_id))
            self.recorder.record(CardResolvedEvent(f"{action.action_id}:resolved", action.user_id, action.card_id))
            return StepResult.complete(frame.child_result)
        raise InvalidCardUse(f"invalid card use step {frame.step_index}")


class LegalPlayActionProvider:
    """Derives ordered card choices from hand zones and registered rules."""

    def __init__(self, validator: CardUseValidator) -> None:
        self.validator = validator

    def options(self, state: GameState, player_id: PlayerId) -> tuple[str, ...]:
        hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
        return tuple(f"use:{card_id}" for card_id in hand if self.validator.can_offer(state, player_id, card_id))

    def build_action(self, state: GameState, player_id: PlayerId, option: str, request_id: str) -> Action:
        if option not in self.options(state, player_id) or not option.startswith("use:"):
            raise InvalidCardUse(f"play option is no longer legal: {option!r}")
        return UseCardAction(f"{request_id}:use", player_id, CardInstanceId(option[4:]))

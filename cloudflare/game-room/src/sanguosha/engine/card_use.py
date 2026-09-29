"""Generic active card-use lifecycle and play option adapter."""

from dataclasses import dataclass

from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.enums import CardCategory
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


class UseCardActionHandler:
    def __init__(self, validator: CardUseValidator, moves: CardMoveService, recorder: EventRecorder,
                 skills=None) -> None:
        self.validator = validator
        self.moves = moves
        self.recorder = recorder
        self.skills = skills

    def validate_start(self, state: GameState, action: Action) -> None:
        assert isinstance(action, UseCardAction)
        rule = self.validator.validate_card(state, action.user_id, action.card_id)
        if action.target_ids:
            self.validator.targets.validate(rule, state, action.user_id, action.target_ids)
        elif not rule.requires_target_selection:
            self.validator.targets.validate(rule, state, action.user_id, ())
        elif not rule.target_candidates(state, action.user_id):
            raise InvalidCardUse("no legal target")

    def _commit(self, state: GameState, action: UseCardAction, targets: tuple[PlayerId, ...]) -> StepResult:
        rule = self.validator.validate_final(state, action.user_id, action.card_id, targets)
        effect = rule.effect_action(f"{action.action_id}:effect", action.user_id, action.card_id, targets)
        hand = ZoneRef(ZoneType.HAND, action.user_id)
        processing = ZoneRef(ZoneType.PROCESSING)
        self.moves.move(state, CardMove(
            f"{action.action_id}:to-processing", (action.card_id,), hand, processing,
            CardMoveReason.USE, action.user_id, action.action_id,
        ))
        usage = state.play_usage
        assert usage is not None
        usage.record(getattr(rule, 'usage_key', state.cards[action.card_id].definition_id))
        self.recorder.record(CardUsedEvent(f"{action.action_id}:used", action.user_id, action.card_id, targets))
        return StepResult.push(effect)

    def _commit_with_jizhi(self, state, frame, action, targets):
        outcome = self._commit(state, action, targets)
        definition = self.validator.definitions.get(state.cards[action.card_id].definition_id)
        if (self.skills is not None and self.skills.has(state, action.user_id, 'jizhi')
                and definition.category is CardCategory.TRICK):
            frame.local['jizhi_targets'] = tuple(targets)
            frame.step_index = 3
            return StepResult.ask(PendingRequest(
                f"{action.action_id}:jizhi", action.user_id, RequestType.YES_NO,
                '是否发动【集智】摸一张牌？', action.action_id, frame.frame_id))
        return outcome

    def _jizhi_effect(self, state, frame, action):
        targets = frame.local['jizhi_targets']
        rule = self.validator.rule_for(state, action.card_id)
        return rule.effect_action(f"{action.action_id}:effect", action.user_id, action.card_id, targets)

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, UseCardAction)
        if frame.step_index == 0:
            self.validate_start(state, action)
            rule = self.validator.rule_for(state, action.card_id)
            if rule.requires_target_selection and not action.target_ids:
                frame.step_index = 1
                low, high = rule.target_bounds(state, action.user_id, action.card_id) if hasattr(rule, 'target_bounds') else (1, 1)
                return StepResult.ask(PendingRequest(
                    f"{action.action_id}:target", action.user_id, RequestType.CHOOSE_PLAYERS if high > 1 else RequestType.CHOOSE_PLAYER,
                    "Choose a target", action.action_id, frame.frame_id,
                    allowed_player_ids=rule.target_candidates(state, action.user_id),
                    min_count=low, max_count=high,
                ))
            frame.step_index = 2
            return self._commit_with_jizhi(state, frame, action, action.target_ids)
        if frame.step_index == 1:
            target = frame.decision
            if not isinstance(target, (str, tuple)):
                raise InvalidCardUse("target choice is missing")
            frame.decision = None
            frame.step_index = 2
            return self._commit_with_jizhi(state, frame, action,
                                           tuple(map(PlayerId, target)) if isinstance(target, tuple) else (PlayerId(target),))
        if frame.step_index == 3:
            draw = frame.decision is True
            frame.decision = None
            if draw:
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

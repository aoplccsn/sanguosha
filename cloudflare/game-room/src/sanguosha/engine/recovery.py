"""HP recovery action, independent of card-specific rules."""

from dataclasses import dataclass

from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState

from .actions import Action, StepResult
from .errors import EngineError
from .events import EventRecorder, HpRecoveredEvent
from .resolution import ResolutionFrame


class InvalidRecovery(EngineError):
    pass


@dataclass(frozen=True, slots=True)
class RecoverAction(Action):
    source_id: PlayerId | None
    target_id: PlayerId
    amount: int
    related_card_id: CardInstanceId | None = None


class RecoverActionHandler:
    def __init__(self, recorder: EventRecorder) -> None:
        self.recorder = recorder

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, RecoverAction)
        if action.amount <= 0 or action.target_id not in state.players:
            raise InvalidRecovery("recovery requires a living target and positive amount")
        target = state.players[action.target_id]
        if not target.is_alive or target.hp >= target.max_hp:
            return StepResult.complete(0)
        previous = target.hp
        target.hp = min(target.max_hp, target.hp + action.amount)
        actual = target.hp - previous
        self.recorder.record(HpRecoveredEvent(f"{action.action_id}:recovered", action.source_id, action.target_id, actual, target.hp))
        return StepResult.complete(actual)

"""Minimal normal damage action; dying resolution is a later stage."""

from dataclasses import dataclass
from typing import Callable

from sanguosha.model.enums import DamageNature
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState

from .actions import Action, StepResult
from .errors import EngineError
from .events import AfterDamageEvent, BeforeDamageEvent, DamageDealtEvent, DyingRequiredEvent, EventRecorder
from .resolution import ResolutionFrame


class InvalidDamage(EngineError):
    pass


@dataclass(frozen=True, slots=True)
class DamageAction(Action):
    source_id: PlayerId | None
    target_id: PlayerId
    amount: int
    nature: DamageNature = DamageNature.NORMAL
    card_id: CardInstanceId | None = None
    related_action_id: str | None = None


def normalize_damage_source(state, action):
    """A dead source cannot be credited with a newly applied damage packet."""
    if action.source_id is not None and not state.players[action.source_id].is_alive:
        from dataclasses import replace
        return replace(action, source_id=None)
    return action


class DamageActionHandler:
    def __init__(self, recorder: EventRecorder, dying_factory: Callable[[DamageAction], Action] | None = None) -> None:
        self.recorder = recorder
        self.dying_factory = dying_factory

    def validate_start(self, state: GameState, action: Action) -> None:
        assert isinstance(action, DamageAction)
        if action.amount <= 0 or action.nature is not DamageNature.NORMAL:
            raise InvalidDamage("T4 supports positive normal damage only")
        if action.target_id not in state.players or not state.players[action.target_id].is_alive:
            raise InvalidDamage("damage target must be living")

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, DamageAction)
        if frame.step_index == 1:
            return StepResult.complete(action.amount)
        self.validate_start(state, action)
        action = frame.action = normalize_damage_source(state, action)
        target = state.players[action.target_id]
        self.recorder.record(BeforeDamageEvent(f"{action.action_id}:before", action.source_id, action.target_id, action.amount))
        target.hp -= action.amount
        self.recorder.record(DamageDealtEvent(f"{action.action_id}:dealt", action.source_id, action.target_id, action.amount, target.hp))
        self.recorder.record(AfterDamageEvent(f"{action.action_id}:after", action.source_id, action.target_id, action.amount))
        if target.hp <= 0:
            self.recorder.record(DyingRequiredEvent(f"{action.action_id}:dying", action.target_id, target.hp))
            if self.dying_factory is not None:
                frame.step_index = 1
                return StepResult.push(self.dying_factory(action))
        return StepResult.complete(action.amount)

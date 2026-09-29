"""Non-damage health loss with the ordinary dying pipeline."""

from dataclasses import dataclass

from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState

from .actions import Action, StepResult
from .dying import DyingAction
from .events import Event, EventRecorder


@dataclass(frozen=True, slots=True)
class LoseHpAction(Action):
    player_id: PlayerId
    amount: int = 1


class LoseHpHandler:
    def __init__(self, events: EventRecorder):
        self.events = events

    def validate_start(self, state: GameState, action: LoseHpAction) -> None:
        if action.amount <= 0 or not state.players[action.player_id].is_alive:
            raise ValueError('health loss requires a living player and positive amount')

    def step(self, state: GameState, frame) -> StepResult:
        action = frame.action
        if frame.step_index == 1:
            return StepResult.complete(action.amount)
        self.validate_start(state, action)
        player = state.players[action.player_id]
        player.hp -= action.amount
        self.events.record(Event(action.action_id + ':lost', 'hp_lost', action.player_id,
                                 metadata={'amount': action.amount, 'hp': player.hp}))
        if player.hp <= 0:
            frame.step_index = 1
            return StepResult.push(DyingAction(action.action_id + ':dying', action.player_id, None))
        return StepResult.complete(action.amount)

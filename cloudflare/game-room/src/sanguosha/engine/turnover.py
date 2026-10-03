"""General face-up/face-down transition used by skill resolution."""
from dataclasses import dataclass

from .actions import Action, StepResult
from .events import Event


@dataclass(frozen=True, slots=True)
class TurnoverAction(Action):
    player_id: str


class TurnoverHandler:
    def __init__(self, events):
        self.events = events

    def validate_start(self, state, action):
        if action.player_id not in state.players or not state.players[action.player_id].is_alive:
            raise ValueError('turnover requires a living player')

    def step(self, state, frame):
        action = frame.action
        self.validate_start(state, action)
        player = state.players[action.player_id]
        player.face_up = not player.face_up
        self.events.record(Event(action.action_id + ':turned', 'player_turned_over',
                                 action.player_id, metadata={'face_up': player.face_up}))
        return StepResult.complete(player.face_up)

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


@dataclass(frozen=True, slots=True)
class LoseMaxHpAction(Action):
    player_id: PlayerId
    amount: int = 1


class LoseMaxHpHandler:
    def __init__(self, events: EventRecorder):
        self.events = events

    def validate_start(self, state: GameState, action: LoseMaxHpAction) -> None:
        if action.amount <= 0 or not state.players[action.player_id].is_alive:
            raise ValueError('max health loss requires a living player and positive amount')

    def step(self, state: GameState, frame) -> StepResult:
        action = frame.action
        if frame.step_index == 1:
            return StepResult.complete(frame.local['lost'])
        self.validate_start(state, action)
        player = state.players[action.player_id]
        old_max = player.max_hp
        player.max_hp = max(0, old_max - action.amount)
        player.hp = min(player.hp, player.max_hp)
        frame.local['lost'] = old_max - player.max_hp
        self.events.record(Event(action.action_id + ':lost', 'max_hp_lost', action.player_id,
                                 metadata={'amount': frame.local['lost'],
                                           'max_hp': player.max_hp, 'hp': player.hp}))
        if player.hp <= 0:
            frame.step_index = 1
            return StepResult.push(DyingAction(action.action_id + ':dying', action.player_id, None))
        return StepResult.complete(frame.local['lost'])


@dataclass(frozen=True, slots=True)
class GainMaxHpAction(Action):
    player_id: PlayerId
    amount: int = 1


class GainMaxHpHandler:
    def __init__(self, events: EventRecorder):
        self.events = events

    def step(self, state: GameState, frame) -> StepResult:
        action = frame.action
        if action.amount <= 0 or not state.players[action.player_id].is_alive:
            raise ValueError('max health gain requires a living player and positive amount')
        player = state.players[action.player_id]
        player.max_hp += action.amount
        self.events.record(Event(action.action_id + ':gained', 'max_hp_gained', action.player_id,
                                 metadata={'amount': action.amount, 'max_hp': player.max_hp}))
        return StepResult.complete(action.amount)

"""A turn schedules phase child actions on the existing resolution stack."""

from dataclasses import dataclass

from sanguosha.model.enums import Phase
from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState, GameStatus

from .actions import Action, StepResult
from .events import EventRecorder, PhaseSkippedEvent, TurnEndedEvent, TurnStartedEvent
from .phases import PhaseAction
from .resolution import ResolutionFrame
from .turn_order import InvalidTurn


STANDARD_PHASE_ORDER: tuple[Phase, ...] = (
    Phase.PREPARATION, Phase.JUDGMENT, Phase.DRAW,
    Phase.PLAY, Phase.DISCARD, Phase.FINISH,
)


@dataclass(frozen=True, slots=True)
class TurnAction(Action):
    player_id: PlayerId
    phases: tuple[Phase, ...] = STANDARD_PHASE_ORDER
    skipped_phases: frozenset[Phase] = frozenset()


class TurnActionHandler:
    def __init__(self, recorder: EventRecorder) -> None:
        self.recorder = recorder

    def validate_start(self, state: GameState, action: Action) -> None:
        assert isinstance(action, TurnAction)
        if action.player_id not in state.players or not state.players[action.player_id].is_alive:
            raise InvalidTurn(f"player {action.player_id!r} cannot start a turn")
        if any(phase not in STANDARD_PHASE_ORDER for phase in action.phases):
            raise InvalidTurn("turn schedule contains an unsupported phase")
        if len(action.phases) != len(set(action.phases)):
            raise InvalidTurn("turn schedule repeats a phase")
        if not action.phases:
            raise InvalidTurn("turn schedule is empty")

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, TurnAction)
        if frame.step_index == 0:
            state.current_player_id = action.player_id
            state.current_phase = None
            state.turn_number += 1
            self.recorder.record(TurnStartedEvent(f"{action.action_id}:start", action.player_id, state.turn_number))
            frame.step_index = 1
            return StepResult.continue_()
        if frame.cursor == len(action.phases) or state.status is GameStatus.FINISHED:
            if state.ruleset_id == 'classic-military':
                state.players[action.player_id].marks.pop('wine', None)
            state.current_phase = None
            self.recorder.record(TurnEndedEvent(f"{action.action_id}:end", action.player_id, state.turn_number))
            return StepResult.complete()
        phase = action.phases[frame.cursor]
        frame.cursor += 1
        marked_skip = phase in (Phase.PLAY, Phase.DRAW) and state.players[action.player_id].marks.pop('skip_' + phase.value, 0)
        if phase in action.skipped_phases or marked_skip:
            self.recorder.record(PhaseSkippedEvent(f"{action.action_id}:{frame.cursor}:skipped", action.player_id, phase))
            return StepResult.continue_()
        return StepResult.push(PhaseAction(f"{action.action_id}:phase:{frame.cursor}:{phase.value}", action.player_id, phase))

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
    def __init__(self, recorder: EventRecorder, before_phase=None) -> None:
        self.recorder = recorder
        self.before_phase = before_phase

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
            if not state.players[action.player_id].face_up:
                state.players[action.player_id].face_up = True
                frame.cursor = len(action.phases)
            frame.step_index = 1
            return StepResult.continue_()
        # A player who dies during a phase must not continue the rest of the turn.
        if (frame.cursor == len(action.phases) or state.status is GameStatus.FINISHED
                or not state.players[action.player_id].is_alive):
            if state.ruleset_id == 'classic-military':
                state.players[action.player_id].marks.pop('wine', None)
                for key in ('slash_quota_bonus', 'slash_ignore_distance',
                            'slash_extra_targets', 'slash_prohibited',
                            'shuangxiong_color'):
                    state.players[action.player_id].marks.pop(key, None)
                if state.players[action.player_id].character_id == 'forest_god_lvbu':
                    state.players[action.player_id].marks.pop('wuwei', None)
                    for other in state.players.values():
                        other.marks.pop('wuwei_target_' + action.player_id, None)
            state.current_phase = None
            self.recorder.record(TurnEndedEvent(f"{action.action_id}:end", action.player_id, state.turn_number))
            return StepResult.complete()
        phase = action.phases[frame.cursor]
        if self.before_phase is not None and frame.local.get('before_phase_cursor') != frame.cursor:
            frame.local['before_phase_cursor'] = frame.cursor
            offer = self.before_phase(state, action.player_id, phase,
                                      f'{action.action_id}:before:{frame.cursor}')
            if offer is not None:
                return StepResult.push(offer)
        frame.cursor += 1
        marked_skip = state.players[action.player_id].marks.pop('skip_' + phase.value, 0)
        if phase in action.skipped_phases or marked_skip:
            self.recorder.record(PhaseSkippedEvent(f"{action.action_id}:{frame.cursor}:skipped", action.player_id, phase))
            return StepResult.continue_()
        return StepResult.push(PhaseAction(f"{action.action_id}:phase:{frame.cursor}:{phase.value}", action.player_id, phase))

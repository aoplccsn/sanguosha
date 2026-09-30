"""Phase actions and pluggable phase bodies using T2 frames."""

from dataclasses import dataclass
from typing import Protocol

from sanguosha.model.enums import Phase
from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState, GameStatus
from sanguosha.model.usage import PlayUsageState

from .actions import Action, StepKind, StepResult
from .errors import ResolutionError
from .events import EventRecorder, PhaseEndedEvent, PhaseStartedEvent
from .requests import PendingRequest, RequestType
from .resolution import ResolutionFrame


END_PLAY_PHASE = "end_play_phase"


@dataclass(frozen=True, slots=True)
class PhaseAction(Action):
    player_id: PlayerId
    phase: Phase


class PhaseBody(Protocol):
    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult: ...


class PhaseBodyRegistry:
    def __init__(self) -> None:
        self._bodies: dict[Phase, PhaseBody] = {}

    def register(self, phase: Phase, body: PhaseBody) -> None:
        self._bodies[phase] = body

    def body_for(self, phase: Phase) -> PhaseBody:
        try:
            return self._bodies[phase]
        except KeyError as exc:
            raise ResolutionError(f"no body for phase {phase}") from exc


class NoOpPhaseBody:
    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        return StepResult.complete()


class PlayOptionProvider(Protocol):
    def options(self, state: GameState, player_id: PlayerId) -> tuple[str, ...]: ...

    def build_action(self, state: GameState, player_id: PlayerId, option: str, request_id: str) -> Action: ...


class EndOnlyPlayOptions:
    """Default T3 provider; content/rules can replace it later."""

    def options(self, state: GameState, player_id: PlayerId) -> tuple[str, ...]:
        return ()

    def build_action(self, state: GameState, player_id: PlayerId, option: str, request_id: str) -> Action:
        raise ResolutionError(f"no action for option {option!r}")


class PlayPhaseBody:
    def __init__(self, provider: PlayOptionProvider) -> None:
        self.provider = provider

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, PhaseAction)
        if state.status is GameStatus.FINISHED:
            return StepResult.complete()
        if frame.step_index == 1:
            options = self.provider.options(state, action.player_id)
            if END_PLAY_PHASE in options or len(options) != len(set(options)):
                raise ResolutionError("provider options must be unique and exclude end_play_phase")
            request_id = f"{frame.frame_id}-play-{frame.cursor}"
            frame.cursor += 1
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                request_id, action.player_id, RequestType.CHOOSE_OPTION,
                "Choose a play action or end the play phase", action.action_id,
                frame.frame_id, choices=(*options, END_PLAY_PHASE),
            ))
        if frame.step_index == 2:
            choice = frame.decision
            frame.decision = None
            if choice == END_PLAY_PHASE:
                return StepResult.complete()
            if not isinstance(choice, str):
                raise ResolutionError("play choice is missing")
            frame.step_index = 3
            return StepResult.push(self.provider.build_action(state, action.player_id, choice, f"{frame.frame_id}-play-{frame.cursor-1}"))
        if frame.step_index == 3:
            frame.step_index = 1
            return StepResult.continue_()
        raise ResolutionError(f"invalid play phase step {frame.step_index}")


class PhaseActionHandler:
    def __init__(self, bodies: PhaseBodyRegistry, recorder: EventRecorder) -> None:
        self.bodies = bodies
        self.recorder = recorder

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, PhaseAction)
        if frame.step_index == 0:
            if state.current_player_id != action.player_id:
                raise ResolutionError("phase player differs from current turn player")
            # A dead player can have a phase already queued by a parent turn.
            if state.status is GameStatus.FINISHED or not state.players[action.player_id].is_alive:
                return StepResult.complete()
            state.current_phase = action.phase
            if action.phase is Phase.PLAY:
                state.play_usage = PlayUsageState(action.player_id, state.turn_number)
            self.recorder.record(PhaseStartedEvent(f"{action.action_id}:start", action.player_id, action.phase))
            frame.step_index = 1
            return StepResult.continue_()
        if frame.step_index == 4:
            self.recorder.record(PhaseEndedEvent(f"{action.action_id}:end", action.player_id, action.phase))
            state.current_phase = None
            return StepResult.complete()
        if state.status is GameStatus.FINISHED or not state.players[action.player_id].is_alive:
            frame.step_index = 4
            return StepResult.continue_()
        outcome = self.bodies.body_for(action.phase).step(state, frame)
        if outcome.kind is StepKind.COMPLETE:
            frame.step_index = 4
            return StepResult.continue_()
        return outcome


def standard_phase_bodies(provider: PlayOptionProvider) -> PhaseBodyRegistry:
    bodies = PhaseBodyRegistry()
    for phase in (Phase.PREPARATION, Phase.JUDGMENT, Phase.DRAW, Phase.DISCARD, Phase.FINISH):
        bodies.register(phase, NoOpPhaseBody())
    bodies.register(Phase.PLAY, PlayPhaseBody(provider))
    return bodies

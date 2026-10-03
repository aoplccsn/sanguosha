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
    def __init__(self, bodies: PhaseBodyRegistry, recorder: EventRecorder, skills=None) -> None:
        self.bodies = bodies
        self.recorder = recorder
        self.skills = skills

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
            if action.phase is Phase.PREPARATION:
                for player in state.players.values():
                    player.marks.pop('wind:' + action.player_id, None)
                    player.marks.pop('fog:' + action.player_id, None)
            if action.phase is Phase.PLAY:
                state.play_usage = PlayUsageState(action.player_id, state.turn_number)
            self.recorder.record(PhaseStartedEvent(f"{action.action_id}:start", action.player_id, action.phase))
            frame.step_index = 1
            return StepResult.continue_()
        if frame.step_index == 4:
            if (action.phase is Phase.DRAW and self.skills is not None
                    and not frame.local.get('juejing_drawn')
                    and self.skills.has(state, action.player_id, 'juejing')
                    and state.players[action.player_id].is_alive):
                from .deck import DrawCardsAction
                frame.local['juejing_drawn'] = True
                missing = max(0, state.players[action.player_id].max_hp
                              - state.players[action.player_id].hp)
                if missing:
                    return StepResult.push(DrawCardsAction(
                        f'{action.action_id}:juejing', action.player_id, missing))
            if (action.phase is Phase.FINISH and self.skills is not None
                    and not frame.local.get('star_weather_offered')
                    and self.skills.has(state, action.player_id, 'qixing')
                    and state.players[action.player_id].is_alive):
                from .gods import StarWeatherAction
                frame.local['star_weather_offered'] = True
                return StepResult.push(StarWeatherAction(
                    f'{action.action_id}:weather', action.player_id))
            if (action.phase is Phase.DRAW and self.skills is not None
                    and not frame.local.get('qixing_exchanged')
                    and self.skills.has(state, action.player_id, 'qixing')
                    and state.players[action.player_id].is_alive):
                from .gods import QixingExchangeAction
                frame.local['qixing_exchanged'] = True
                return StepResult.push(QixingExchangeAction(
                    f'{action.action_id}:qixing', action.player_id))
            if not frame.local.get('phase_end_recorded'):
                self.recorder.record(PhaseEndedEvent(f"{action.action_id}:end", action.player_id, action.phase))
                state.current_phase = None
                frame.local['phase_end_recorded'] = True
                if action.phase is Phase.DISCARD and self.skills is not None:
                    from .events import phase_rule_discards
                    cards = phase_rule_discards(self.recorder.events, action.action_id, action.player_id)
                    if (len(cards) >= 2 and self.skills.has(state, action.player_id, 'qinyin')
                            and state.players[action.player_id].is_alive):
                        frame.local['qinyin_pending'] = True
                    frame.local['guzheng_cards'] = cards
                    frame.local['guzheng_owners'] = tuple(pid for pid in state.seat_order
                        if pid != action.player_id and state.players[pid].is_alive
                        and self.skills.has(state, pid, 'guzheng')) if cards else ()
                    frame.local['guzheng_cursor'] = 0
            if frame.local.pop('qinyin_pending', False):
                from .gods import QinyinAction
                return StepResult.push(QinyinAction(
                    f'{action.action_id}:qinyin', action.player_id))
            owners = frame.local.get('guzheng_owners', ())
            index = frame.local.get('guzheng_cursor', 0)
            if index < len(owners):
                frame.local['guzheng_cursor'] = index + 1
                from .mountain import GuzhengAction
                return StepResult.push(GuzhengAction(
                    f'{action.action_id}:guzheng:{index}', owners[index],
                    action.player_id, frame.local['guzheng_cards']))
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

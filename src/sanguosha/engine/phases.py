"""Phase actions and pluggable phase bodies using T2 frames."""

from dataclasses import dataclass, replace
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
        if state.status is GameStatus.FINISHED or state.players[action.player_id].marks.pop('poxi_end_play',0):
            return StepResult.complete()
        if frame.step_index == 1:
            options = self.provider.options(state, action.player_id)
            if END_PLAY_PHASE in options or len(options) != len(set(options)):
                raise ResolutionError("provider options must be unique and exclude end_play_phase")
            request_id = f"{frame.frame_id}-play-{frame.cursor}"
            play_card_targets = {}
            validator = getattr(self.provider, 'validator', None)
            if validator is not None:
                for option in options:
                    if not option.startswith('use:'):
                        continue
                    card_id = option[4:]
                    rule = validator.rule_for(state, card_id)
                    if rule.requires_target_selection:
                        low, high = rule.target_bounds(state, action.player_id, card_id) if hasattr(rule, 'target_bounds') else (1, 1)
                        targets = validator.target_candidates(state, action.player_id, card_id)
                    else:
                        low, high, targets = 0, 0, ()
                    play_card_targets[option] = (targets, low, high)
            frame.cursor += 1
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                request_id, action.player_id, RequestType.CHOOSE_OPTION,
                "Choose a play action or end the play phase", action.action_id,
                frame.frame_id, choices=(*options, END_PLAY_PHASE),
                play_card_targets=play_card_targets,
            ))
        if frame.step_index == 2:
            choice = frame.decision
            frame.decision = None
            if isinstance(choice, dict):
                from .card_use import UseCardAction
                option = choice['option']
                if option not in self.provider.options(state, action.player_id):
                    raise ResolutionError('play option is no longer legal')
                built = self.provider.build_action(state, action.player_id, option,
                                                   f"{frame.frame_id}-play-{frame.cursor-1}")
                if not isinstance(built, UseCardAction):
                    raise ResolutionError('combined decision requires a physical card')
                frame.step_index = 3
                return StepResult.push(replace(built, target_ids=tuple(choice['targets']),
                                               targets_confirmed=True))
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
            if (action.phase is Phase.PLAY and self.skills is not None
                    and not frame.local.get('jingce_offered')
                    and self.skills.has(state, action.player_id, 'jingce')
                    and state.players[action.player_id].is_alive):
                frame.local['jingce_offered'] = True
                from .yj2013 import YJ2013Action
                return StepResult.push(YJ2013Action(action.action_id + ':jingce', action.player_id, 'jingce'))
            if not frame.local.get('phase_end_recorded'):
                if action.phase is Phase.PLAY:state.players[action.player_id].marks.pop('longnu_form',None)
                self.recorder.record(PhaseEndedEvent(f"{action.action_id}:end", action.player_id, action.phase))
                state.current_phase = None
                frame.local['phase_end_recorded'] = True
                if action.phase is Phase.DISCARD and self.skills is not None:
                    from .events import phase_rule_discards
                    cards = phase_rule_discards(self.recorder.events, action.action_id, action.player_id)
                    if self.skills.has(state, action.player_id, 'renjie'):
                        player = state.players[action.player_id]
                        player.marks['ren'] = player.marks.get('ren', 0) + len(cards)
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
        if action.phase is Phase.PLAY and self.skills is not None and self.skills.has(state,action.player_id,'longnu') and not frame.local.get('longnu_started'):
            from .remaining_gods import RemainingGodAction
            frame.local['longnu_started']=True
            return StepResult.push(RemainingGodAction(action.action_id+':longnu',action.player_id,'longnu'))
        if action.phase is Phase.PLAY and self.skills is not None and self.skills.has(state,action.player_id,'cuike') and not frame.local.get('cuike_offered'):
            from .remaining_gods import RemainingGodAction
            frame.local['cuike_offered']=True
            return StepResult.push(RemainingGodAction(action.action_id+':cuike',action.player_id,'cuike'))
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

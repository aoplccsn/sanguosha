from dataclasses import dataclass

import pytest

from sanguosha.engine import (
    Action, ActionHandlerRegistry, Decision, END_PLAY_PHASE, EngineStatus,
    EventRecorder, GameEngine, InvalidDecision, InvalidEngineState, InvalidTurn,
    PhaseAction, PhaseActionHandler,
    PhaseEndedEvent, PhaseSkippedEvent, PhaseStartedEvent,
    STANDARD_PHASE_ORDER, StepResult, TurnAction,
    TurnActionHandler, TurnStartedEvent, next_alive_player,
    standard_phase_bodies,
)
from sanguosha.engine.phases import EndOnlyPlayOptions
from sanguosha.model.enums import Identity, Phase, PlayerStatus
from sanguosha.model.ids import CharacterId, PlayerId
from sanguosha.model.player import PlayerState
from sanguosha.model.state import GameState


P = tuple(PlayerId(f"p{i}") for i in range(1, 6))


@dataclass(frozen=True, slots=True)
class MockPlayAction(Action):
    name: str


@dataclass(frozen=True, slots=True)
class MockPromptChild(Action):
    pass


class PlayActionHandler:
    def __init__(self, trace):
        self.trace = trace

    def step(self, state, frame):
        action = frame.action
        self.trace.append((action.name, state.current_player_id, state.current_phase))
        return StepResult.complete(action.name)


class PromptActionHandler:
    def step(self, state, frame):
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.push(MockPromptChild(f"{frame.action.action_id}:child"))
        return StepResult.complete(frame.child_result)


class PromptChildHandler:
    def step(self, state, frame):
        from sanguosha.engine import PendingRequest, RequestType
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                f"{frame.frame_id}:answer", state.current_player_id,
                RequestType.YES_NO, "Continue?", frame.action.action_id, frame.frame_id,
            ))
        return StepResult.complete(frame.decision)


class MockOptions:
    def __init__(self, names=("test_action_a", "test_action_b")):
        self.names = names

    def options(self, state, player_id):
        return self.names

    def build_action(self, state, player_id, option, request_id):
        if option == "test_prompt_action":
            return MockPromptAction(f"{request_id}:action")
        return MockPlayAction(f"{request_id}:action", option)


@dataclass(frozen=True, slots=True)
class MockPromptAction(Action):
    pass


def state():
    players = {
        pid: PlayerState(pid, index, CharacterId("test"), Identity.LORD if index == 0 else Identity.REBEL, 4, 4)
        for index, pid in enumerate(P)
    }
    return GameState("test", players=players, seat_order=P)


def setup(provider=None, draw_body=None):
    game = state()
    recorder = EventRecorder()
    trace = []
    bodies = standard_phase_bodies(provider or EndOnlyPlayOptions())
    if draw_body is not None:
        bodies.register(Phase.DRAW, draw_body)
    registry = ActionHandlerRegistry()
    registry.register(TurnAction, TurnActionHandler(recorder))
    registry.register(PhaseAction, PhaseActionHandler(bodies, recorder))
    registry.register(MockPlayAction, PlayActionHandler(trace))
    registry.register(MockPromptAction, PromptActionHandler())
    registry.register(MockPromptChild, PromptChildHandler())
    return GameEngine(game, registry), recorder, trace


def answer(e, value):
    request = e.pending_request
    assert request is not None
    return e.submit_decision(Decision(request.request_id, request.player_id, value))


def event_names(recorder):
    return [type(e).__name__ + (f":{e.phase.value}" if hasattr(e, "phase") else "") for e in recorder.events]


def test_full_empty_turn_order_and_state():
    e, recorder, _ = setup()
    assert e.start_action(TurnAction("turn-1", P[0])) is EngineStatus.WAITING_FOR_DECISION
    assert e.stack.depth == 2 and e.state.current_phase is Phase.PLAY
    assert e.state.current_player_id == P[0] and e.state.turn_number == 1
    assert e.pending_request.choices == (END_PLAY_PHASE,)
    assert answer(e, END_PLAY_PHASE) is EngineStatus.COMPLETED
    assert e.state.current_phase is None and e.state.current_player_id == P[0]
    assert event_names(recorder) == [
        "TurnStartedEvent",
        "PhaseStartedEvent:preparation", "PhaseEndedEvent:preparation",
        "PhaseStartedEvent:judgment", "PhaseEndedEvent:judgment",
        "PhaseStartedEvent:draw", "PhaseEndedEvent:draw",
        "PhaseStartedEvent:play", "PhaseEndedEvent:play",
        "PhaseStartedEvent:discard", "PhaseEndedEvent:discard",
        "PhaseStartedEvent:finish", "PhaseEndedEvent:finish",
        "TurnEndedEvent",
    ]
    assert [event.event_id for event in recorder.events] == list(dict.fromkeys(event.event_id for event in recorder.events))


def test_dead_player_ends_turn_after_phase_resolution():
    class KillInJudgment:
        def step(self, game, frame):
            game.players[P[0]].status = PlayerStatus.DEAD
            return StepResult.complete()

    e, recorder, _ = setup()
    phase_handler = e.registry.handler_for(PhaseAction("probe", P[0], Phase.JUDGMENT))
    phase_handler.bodies.register(Phase.JUDGMENT, KillInJudgment())

    assert e.start_action(TurnAction("turn", P[0])) is EngineStatus.COMPLETED
    assert [type(event).__name__ for event in recorder.events] == [
        "TurnStartedEvent",
        "PhaseStartedEvent", "PhaseEndedEvent",
        "PhaseStartedEvent", "PhaseEndedEvent",
        "TurnEndedEvent",
    ]
    assert e.state.current_phase is None
    assert e.state.players[P[0]].status is PlayerStatus.DEAD


def test_multiple_play_actions_and_repeat_requests():
    e, recorder, trace = setup(MockOptions())
    e.start_action(TurnAction("turn", P[0]))
    first = e.pending_request.request_id
    assert answer(e, "test_action_a") is EngineStatus.WAITING_FOR_DECISION
    second = e.pending_request.request_id
    assert second != first
    assert answer(e, "test_action_b") is EngineStatus.WAITING_FOR_DECISION
    third = e.pending_request.request_id
    assert third not in (first, second)
    assert answer(e, END_PLAY_PHASE) is EngineStatus.COMPLETED
    assert trace == [("test_action_a", P[0], Phase.PLAY), ("test_action_b", P[0], Phase.PLAY)]
    assert event_names(recorder).count("PhaseStartedEvent:play") == 1


def test_play_child_nested_pause_resume():
    e, _, _ = setup(MockOptions(("test_prompt_action",)))
    e.start_action(TurnAction("turn", P[0]))
    assert answer(e, "test_prompt_action") is EngineStatus.WAITING_FOR_DECISION
    assert e.stack.depth == 4
    assert e.state.current_phase is Phase.PLAY
    assert answer(e, True) is EngineStatus.WAITING_FOR_DECISION
    assert e.stack.depth == 2 and e.pending_request.choices == ("test_prompt_action", END_PLAY_PHASE)
    assert answer(e, END_PLAY_PHASE) is EngineStatus.COMPLETED


class DrawRecorder:
    def __init__(self):
        self.calls = 0

    def step(self, state, frame):
        self.calls += 1
        assert state.current_phase is Phase.DRAW
        return StepResult.complete()


def test_skip_draw_has_only_skip_event_and_no_body():
    draw = DrawRecorder()
    e, recorder, _ = setup(draw_body=draw)
    e.start_action(TurnAction("turn", P[0], skipped_phases=frozenset({Phase.DRAW})))
    assert draw.calls == 0
    assert e.state.current_phase is Phase.PLAY
    assert event_names(recorder) == [
        "TurnStartedEvent",
        "PhaseStartedEvent:preparation", "PhaseEndedEvent:preparation",
        "PhaseStartedEvent:judgment", "PhaseEndedEvent:judgment",
        "PhaseSkippedEvent:draw", "PhaseStartedEvent:play",
    ]
    answer(e, END_PLAY_PHASE)
    assert e.status is EngineStatus.COMPLETED


def test_skip_multiple_phases():
    e, recorder, _ = setup()
    e.start_action(TurnAction("turn", P[0], skipped_phases=frozenset({Phase.JUDGMENT, Phase.DRAW})))
    answer(e, END_PLAY_PHASE)
    assert [event.phase for event in recorder.events if isinstance(event, PhaseSkippedEvent)] == [Phase.JUDGMENT, Phase.DRAW]
    assert [event.phase for event in recorder.events if isinstance(event, PhaseStartedEvent)] == [
        Phase.PREPARATION, Phase.PLAY, Phase.DISCARD, Phase.FINISH,
    ]


def test_next_alive_player_skips_dead_and_wraps():
    s = state()
    s.players[P[1]].status = PlayerStatus.DEAD
    assert next_alive_player(s, P[0]) == P[2]
    assert next_alive_player(s, P[4]) == P[0]


def test_two_turns_increment_number_and_switch_current_player():
    e, recorder, _ = setup()
    e.start_action(TurnAction("turn-1", P[0]))
    answer(e, END_PLAY_PHASE)
    second = next_alive_player(e.state, P[0])
    e.start_action(TurnAction("turn-2", second))
    assert e.state.turn_number == 2 and e.state.current_player_id == P[1]
    assert e.state.current_phase is Phase.PLAY
    answer(e, END_PLAY_PHASE)
    assert [event.turn_number for event in recorder.events if isinstance(event, TurnStartedEvent)] == [1, 2]
    assert e.state.current_phase is None and e.state.current_player_id == P[1]


def test_dead_player_rejected_before_frame_or_state_change():
    e, recorder, _ = setup()
    e.state.players[P[1]].status = PlayerStatus.DEAD
    with pytest.raises(InvalidTurn):
        e.start_action(TurnAction("dead-turn", P[1]))
    assert e.stack.depth == 0 and e.state.turn_number == 0 and recorder.events == []
    e.start_action(TurnAction("valid-turn", P[0]))
    answer(e, END_PLAY_PHASE)


def test_concurrent_top_level_turn_rejected_without_damage():
    e, recorder, _ = setup()
    e.start_action(TurnAction("first", P[0]))
    before = e.stack.snapshot()
    request = e.pending_request
    with pytest.raises(InvalidEngineState):
        e.start_action(TurnAction("second", P[1]))
    assert e.stack.snapshot() == before and e.pending_request == request and e.state.turn_number == 1
    answer(e, END_PLAY_PHASE)
    assert e.status is EngineStatus.COMPLETED


def test_illegal_play_choice_preserves_request():
    e, _, trace = setup(MockOptions())
    e.start_action(TurnAction("turn", P[0]))
    request = e.pending_request
    before = e.stack.snapshot()
    with pytest.raises(InvalidDecision):
        answer(e, "invalid-option")
    assert e.pending_request == request and e.stack.snapshot() == before and trace == []
    assert answer(e, END_PLAY_PHASE) is EngineStatus.COMPLETED


def test_custom_draw_body_extension_without_engine_change():
    draw = DrawRecorder()
    e, recorder, _ = setup(draw_body=draw)
    e.start_action(TurnAction("turn", P[0]))
    assert draw.calls == 1
    answer(e, END_PLAY_PHASE)
    assert any(isinstance(event, PhaseStartedEvent) and event.phase is Phase.DRAW for event in recorder.events)


def test_deterministic_turn_replay():
    def run():
        e, recorder, trace = setup(MockOptions())
        e.start_action(TurnAction("turn", P[0]))
        answer(e, "test_action_a")
        answer(e, END_PLAY_PHASE)
        return event_names(recorder), [event.event_id for event in recorder.events], trace, e.state.turn_number
    assert run() == run()


def test_standard_schedule_excludes_start_marker():
    assert STANDARD_PHASE_ORDER == (
        Phase.PREPARATION, Phase.JUDGMENT, Phase.DRAW,
        Phase.PLAY, Phase.DISCARD, Phase.FINISH,
    )
    assert Phase.START not in STANDARD_PHASE_ORDER


def test_every_phase_event_sees_consistent_current_state():
    class StateCheckingRecorder(EventRecorder):
        def __init__(self, game):
            super().__init__()
            self.game = game

        def record(self, event):
            if isinstance(event, (PhaseStartedEvent, PhaseEndedEvent)):
                assert self.game.current_player_id == event.player_id
                assert self.game.current_phase is event.phase
            if isinstance(event, PhaseSkippedEvent):
                assert self.game.current_phase is None
            super().record(event)

    game = state()
    recorder = StateCheckingRecorder(game)
    registry = ActionHandlerRegistry()
    registry.register(TurnAction, TurnActionHandler(recorder))
    registry.register(PhaseAction, PhaseActionHandler(standard_phase_bodies(EndOnlyPlayOptions()), recorder))
    e = GameEngine(game, registry)
    e.start_action(TurnAction("turn", P[0], skipped_phases=frozenset({Phase.DRAW})))
    answer(e, END_PLAY_PHASE)
    assert e.state.current_phase is None

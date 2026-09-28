from dataclasses import dataclass

import pytest

from sanguosha.engine import (
    Action, ActionHandlerRegistry, Decision, EngineStatus, GameEngine,
    InvalidDecision, PendingRequest, RequestType, ResolutionError,
    StepResult, UnknownActionHandler, UnknownRequest,
)
from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState


P1, P2, P3, P4 = (PlayerId(f"p{i}") for i in range(1, 5))


@dataclass(frozen=True, slots=True)
class Simple(Action):
    pass


@dataclass(frozen=True, slots=True)
class Ask(Action):
    player: PlayerId = P1
    kind: RequestType = RequestType.YES_NO


@dataclass(frozen=True, slots=True)
class Parent(Action):
    child: Action = Ask("child")


@dataclass(frozen=True, slots=True)
class Multi(Action):
    targets: tuple[PlayerId, ...] = (P2, P3, P4)


@dataclass(frozen=True, slots=True)
class Target(Action):
    player: PlayerId = P1


@dataclass(frozen=True, slots=True)
class Counter(Action):
    level: int = 1


class SimpleHandler:
    def step(self, state, frame):
        state.metadata["count"] = int(state.metadata.get("count", 0)) + 1
        return StepResult.complete("done")


class AskHandler:
    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                f"request-{action.action_id}", action.player, action.kind, "test prompt",
                action.action_id, frame.frame_id,
                choices=("alpha", "beta"), allowed_player_ids=(P1, P2, P3, P4),
            ))
        assert frame.decision is not None
        return StepResult.complete(frame.decision)


class ParentHandler:
    def __init__(self, trace):
        self.trace = trace

    def step(self, state, frame):
        if frame.step_index == 0:
            self.trace.append(f"{frame.action.action_id}-start")
            frame.step_index = 1
            return StepResult.push(frame.action.child)
        self.trace.append(f"{frame.action.action_id}-end")
        return StepResult.complete(frame.child_result)


class TargetHandler:
    def __init__(self, trace):
        self.trace = trace

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            self.trace.append(str(action.player))
            if action.player == P3:
                frame.step_index = 1
                return StepResult.push(Ask(f"dying-{action.action_id}", P3))
            return StepResult.complete("ok")
        return StepResult.complete(frame.child_result)


class MultiHandler:
    def step(self, state, frame):
        action = frame.action
        if frame.cursor == len(action.targets):
            return StepResult.complete("all targets")
        target = action.targets[frame.cursor]
        frame.cursor += 1
        return StepResult.push(Target(f"target-{target}", target))


class CounterHandler:
    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            frame.step_index = 1
            return StepResult.push(Ask(f"counter-choice-{action.level}", P1))
        if frame.step_index == 1:
            if frame.child_result and action.level < 3:
                frame.step_index = 2
                return StepResult.push(Counter(f"counter-{action.level+1}", action.level+1))
            return StepResult.complete(bool(frame.child_result))
        return StepResult.complete(not bool(frame.child_result))


def engine(*handlers):
    registry = ActionHandlerRegistry()
    for action_type, handler in handlers:
        registry.register(action_type, handler)
    return GameEngine(GameState("test"), registry)


def test_simple_action_completes_and_modifies_test_state():
    e = engine((Simple, SimpleHandler()))
    assert e.start_action(Simple("simple")) is EngineStatus.COMPLETED
    assert e.stack.depth == 0 and e.last_result == "done"
    assert e.state.metadata["count"] == 1


def test_yes_no_pause_and_resume():
    e = engine((Ask, AskHandler()))
    assert e.start_action(Ask("ask")) is EngineStatus.WAITING_FOR_DECISION
    assert e.stack.depth == 1 and e.pending_request is not None
    assert e.submit_decision(Decision("request-ask", P1, True)) is EngineStatus.COMPLETED
    assert e.last_result is True


def test_parent_child_order_and_result():
    trace = []
    class TracedChild:
        def step(self, state, frame):
            trace.extend(["child-start", "child-end"])
            return StepResult.complete("child-result")
    e = engine((Parent, ParentHandler(trace)), (Simple, TracedChild()))
    assert e.start_action(Parent("parent", Simple("child"))) is EngineStatus.COMPLETED
    assert trace == ["parent-start", "child-start", "child-end", "parent-end"]
    assert e.last_result == "child-result"


def test_child_pending_and_three_levels_resume():
    trace = []
    e = engine((Parent, ParentHandler(trace)), (Ask, AskHandler()))
    action = Parent("a", Parent("b", Ask("c")))
    assert e.start_action(action) is EngineStatus.WAITING_FOR_DECISION
    assert [f.action.action_id for f in e.stack.snapshot()] == ["a", "b", "c"]
    assert e.submit_decision(Decision("request-c", P1, False)) is EngineStatus.COMPLETED
    assert trace == ["a-start", "b-start", "b-end", "a-end"]
    assert e.last_result is False


@pytest.mark.parametrize("decision,error", [
    (Decision("wrong", P1, True), UnknownRequest),
    (Decision("request-choose", P2, "alpha"), InvalidDecision),
    (Decision("request-choose", P1, "gamma"), InvalidDecision),
])
def test_invalid_decision_preserves_request_and_stack(decision, error):
    e = engine((Ask, AskHandler()))
    e.start_action(Ask("choose", P1, RequestType.CHOOSE_OPTION))
    before = e.stack.snapshot()
    with pytest.raises(error):
        e.submit_decision(decision)
    assert e.status is EngineStatus.WAITING_FOR_DECISION
    assert e.pending_request is not None and e.stack.snapshot() == before
    e.submit_decision(Decision("request-choose", P1, "alpha"))
    with pytest.raises(UnknownRequest):
        e.submit_decision(Decision("request-choose", P1, "alpha"))


def test_player_choice_and_no_pending_rejection():
    e = engine((Ask, AskHandler()))
    with pytest.raises(UnknownRequest):
        e.submit_decision(Decision("missing", P1, True))
    e.start_action(Ask("player", P1, RequestType.CHOOSE_PLAYER))
    with pytest.raises(InvalidDecision):
        e.submit_decision(Decision("request-player", P1, PlayerId("outside")))
    e.submit_decision(Decision("request-player", P1, P3))
    assert e.last_result == P3


def test_registry_unknown_handler():
    e = engine((Simple, SimpleHandler()))
    with pytest.raises(UnknownActionHandler):
        e.start_action(Ask("unknown"))
    assert e.stack.depth == 0


def test_deterministic_replay():
    def run():
        e = engine((Parent, ParentHandler([])), (Ask, AskHandler()))
        e.start_action(Parent("parent", Ask("child")))
        request = e.pending_request
        e.submit_decision(Decision(request.request_id, P1, True))
        return e.last_result, e.stack.depth, e.state.metadata
    assert run() == run()


def test_mock_attack_response_branches():
    @dataclass(frozen=True, slots=True)
    class MockAttack(Action):
        pass

    class Handler:
        def step(self, state, frame):
            if frame.step_index == 0:
                frame.step_index = 1
                return StepResult.push(Ask("response", P2))
            if frame.step_index == 1:
                if frame.child_result:
                    return StepResult.complete("avoided")
                frame.step_index = 2
                return StepResult.push(Simple("mock-damage"))
            return StepResult.complete("hit")

    for answer, result, count in [(True, "avoided", 0), (False, "hit", 1)]:
        e = engine((MockAttack, Handler()), (Ask, AskHandler()), (Simple, SimpleHandler()))
        e.start_action(MockAttack("attack"))
        e.submit_decision(Decision("request-response", P2, answer))
        assert (e.last_result, e.state.metadata.get("count", 0)) == (result, count)


def test_mock_multi_target_dying_resume_cursor():
    trace = []
    e = engine((Multi, MultiHandler()), (Target, TargetHandler(trace)), (Ask, AskHandler()))
    e.start_action(Multi("multi"))
    assert e.status is EngineStatus.WAITING_FOR_DECISION and e.stack.depth == 3
    assert trace == ["p2", "p3"]
    assert e.stack.snapshot()[0].cursor == 2
    e.submit_decision(Decision("request-dying-target-p3", P3, True))
    assert trace == ["p2", "p3", "p4"]
    assert e.last_result == "all targets"


def test_mock_nested_counter():
    e = engine((Counter, CounterHandler()), (Ask, AskHandler()))
    e.start_action(Counter("counter-1"))
    for level in (1, 2, 3):
        assert e.status is EngineStatus.WAITING_FOR_DECISION
        e.submit_decision(Decision(f"request-counter-choice-{level}", P1, True))
    assert e.status is EngineStatus.COMPLETED and e.last_result is True


def test_bad_handler_step_guard():
    class BadHandler:
        def step(self, state, frame):
            return StepResult.continue_()
    registry = ActionHandlerRegistry()
    registry.register(Simple, BadHandler())
    e = GameEngine(GameState("test"), registry, max_steps=5)
    with pytest.raises(ResolutionError, match="step limit"):
        e.start_action(Simple("loop"))
    assert e.status is EngineStatus.ERROR

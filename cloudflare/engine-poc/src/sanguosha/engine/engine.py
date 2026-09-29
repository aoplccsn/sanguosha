"""Small synchronous coordinator for explicit resolution frames."""

from enum import StrEnum

from sanguosha.model.state import GameState

from .actions import Action, ResultValue, StepKind
from .errors import InvalidDecision, InvalidEngineState, ResolutionError, UnknownRequest
from .registry import ActionHandlerRegistry
from .requests import Decision, PendingRequest
from .resolution import FrameStatus, ResolutionFrame, ResolutionStack


class EngineStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_FOR_DECISION = "waiting_for_decision"
    COMPLETED = "completed"
    ERROR = "error"


class GameEngine:
    def __init__(self, state: GameState, registry: ActionHandlerRegistry, *, max_steps: int = 100_000) -> None:
        self.state = state
        self.registry = registry
        self.stack = ResolutionStack()
        self.pending_request: PendingRequest | None = None
        self.status = EngineStatus.IDLE
        self.last_result: ResultValue = None
        self._next_frame = 1
        self._seen_action_ids: set[str] = set()
        self._seen_request_ids: set[str] = set()
        self.max_steps = max_steps
        self.reaction_provider = None

    def _new_frame(self, action: Action, parent_id: str | None = None) -> ResolutionFrame:
        if not action.action_id or action.action_id in self._seen_action_ids:
            raise ResolutionError(f"duplicate or empty action id: {action.action_id!r}")
        self.registry.handler_for(action)
        frame = ResolutionFrame(f"frame-{self._next_frame}", action, parent_id)
        self._next_frame += 1
        self._seen_action_ids.add(action.action_id)
        return frame

    def start_action(self, action: Action) -> EngineStatus:
        if self.status in (EngineStatus.RUNNING, EngineStatus.WAITING_FOR_DECISION) or not self.stack.is_empty():
            raise InvalidEngineState("engine is already resolving")
        # Optional handler preflight rejects invalid top-level actions before
        # creating a frame or changing the engine's status.
        validator = getattr(self.registry.handler_for(action), "validate_start", None)
        if validator is not None:
            validator(self.state, action)
        frame = self._new_frame(action)
        self.stack.push(frame)
        self.last_result = None
        return self.run_until_blocked()

    def submit_decision(self, decision: Decision) -> EngineStatus:
        request = self.pending_request
        if request is None or self.status is not EngineStatus.WAITING_FOR_DECISION:
            raise UnknownRequest("no pending request")
        if decision.request_id != request.request_id:
            raise UnknownRequest(f"request {decision.request_id!r} is not pending")
        if decision.player_id != request.player_id:
            raise InvalidDecision("wrong player for pending request")
        request.validate(decision.value)
        frame = self.stack.top()
        if frame.frame_id != request.originating_frame_id or frame.status is not FrameStatus.WAITING_DECISION:
            raise ResolutionError("pending request does not match top frame")
        frame.decision = decision.value
        frame.status = FrameStatus.READY
        self.pending_request = None
        return self.run_until_blocked()

    def run_until_blocked(self) -> EngineStatus:
        if self.pending_request is not None:
            self.status = EngineStatus.WAITING_FOR_DECISION
            return self.status
        self.status = EngineStatus.RUNNING
        steps = 0
        try:
            while not self.stack.is_empty():
                steps += 1
                if steps > self.max_steps:
                    raise ResolutionError("resolution step limit exceeded")
                frame = self.stack.top()
                if frame.status is not FrameStatus.READY:
                    raise ResolutionError(f"cannot step frame in {frame.status} state")
                if frame.deferred_step is not None:
                    outcome = frame.deferred_step
                    frame.deferred_step = None
                    frame.child_result = frame.reaction_child_result
                else:
                    outcome = self.registry.handler_for(frame.action).step(self.state, frame)
                reaction = self.reaction_provider(self.state) if self.reaction_provider else None
                if reaction is not None:
                    frame.deferred_step = outcome
                    frame.reaction_child_result = frame.child_result
                    frame.status = FrameStatus.WAITING_CHILD
                    self.stack.push(self._new_frame(reaction, frame.frame_id))
                    continue
                if outcome.kind is StepKind.CONTINUE:
                    continue
                if outcome.kind is StepKind.REQUEST_DECISION:
                    request = outcome.request
                    if request is None or not request.request_id or request.request_id in self._seen_request_ids:
                        raise ResolutionError("missing or duplicate request id")
                    if request.originating_action_id != frame.action.action_id or request.originating_frame_id != frame.frame_id:
                        raise ResolutionError("request origin does not match frame")
                    self._seen_request_ids.add(request.request_id)
                    frame.status = FrameStatus.WAITING_DECISION
                    self.pending_request = request
                    self.status = EngineStatus.WAITING_FOR_DECISION
                    return self.status
                if outcome.kind is StepKind.PUSH_CHILD:
                    if outcome.child is None:
                        raise ResolutionError("push outcome has no child")
                    child = self._new_frame(outcome.child, frame.frame_id)
                    frame.status = FrameStatus.WAITING_CHILD
                    self.stack.push(child)
                    continue
                if outcome.kind in (StepKind.COMPLETE, StepKind.CANCELLED):
                    frame.result = outcome.value
                    frame.status = FrameStatus.COMPLETE
                    self.stack.pop()
                    if self.stack.is_empty():
                        self.last_result = frame.result
                    else:
                        parent = self.stack.top()
                        if parent.frame_id != frame.parent_frame_id or parent.status is not FrameStatus.WAITING_CHILD:
                            raise ResolutionError("child result has no waiting parent")
                        parent.child_result = frame.result
                        parent.status = FrameStatus.READY
                    continue
                raise ResolutionError(f"action failed: {outcome.value!r}")
            self.status = EngineStatus.COMPLETED
            return self.status
        except Exception:
            self.status = EngineStatus.ERROR
            raise

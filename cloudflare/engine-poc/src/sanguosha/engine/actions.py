"""Action data and explicit step outcomes."""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from sanguosha.model.state import GameState
from sanguosha.model.virtual_card import VirtualCard

from .requests import ChoiceValue, PendingRequest

if TYPE_CHECKING:
    from .resolution import ResolutionFrame


@dataclass(frozen=True, slots=True)
class Action:
    action_id: str


ResultValue = bool | str | int | VirtualCard | None


class StepKind(StrEnum):
    CONTINUE = "continue"
    REQUEST_DECISION = "request_decision"
    PUSH_CHILD = "push_child"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StepResult:
    kind: StepKind
    request: PendingRequest | None = None
    child: Action | None = None
    value: ResultValue = None

    @classmethod
    def continue_(cls) -> "StepResult":
        return cls(StepKind.CONTINUE)

    @classmethod
    def ask(cls, request: PendingRequest) -> "StepResult":
        return cls(StepKind.REQUEST_DECISION, request=request)

    @classmethod
    def push(cls, child: Action) -> "StepResult":
        return cls(StepKind.PUSH_CHILD, child=child)

    @classmethod
    def complete(cls, value: ResultValue = None) -> "StepResult":
        return cls(StepKind.COMPLETE, value=value)

    @classmethod
    def cancelled(cls, value: ResultValue = None) -> "StepResult":
        return cls(StepKind.CANCELLED, value=value)

    @classmethod
    def failed(cls, value: ResultValue = None) -> "StepResult":
        return cls(StepKind.FAILED, value=value)


class ActionHandler(Protocol):
    def step(self, state: GameState, frame: "ResolutionFrame") -> StepResult: ...

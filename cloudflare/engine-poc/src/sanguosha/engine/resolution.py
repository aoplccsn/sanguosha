"""Explicit frames preserve all continuation data across Python calls."""

from dataclasses import dataclass, field
from enum import StrEnum

from .actions import Action, ResultValue, StepResult
from .errors import ResolutionError
from .requests import ChoiceValue


class FrameStatus(StrEnum):
    READY = "ready"
    WAITING_DECISION = "waiting_decision"
    WAITING_CHILD = "waiting_child"
    COMPLETE = "complete"


@dataclass(slots=True)
class ResolutionFrame:
    frame_id: str
    action: Action
    parent_frame_id: str | None = None
    step_index: int = 0
    cursor: int = 0
    local: dict[str, str | int | bool] = field(default_factory=dict)
    decision: ChoiceValue | None = None
    child_result: ResultValue = None
    result: ResultValue = None
    status: FrameStatus = FrameStatus.READY
    deferred_step: StepResult | None = None
    reaction_child_result: ResultValue = None


class ResolutionStack:
    def __init__(self) -> None:
        self._frames: list[ResolutionFrame] = []

    def push(self, frame: ResolutionFrame) -> None:
        self._frames.append(frame)

    def top(self) -> ResolutionFrame:
        if not self._frames:
            raise ResolutionError("resolution stack is empty")
        return self._frames[-1]

    def pop(self) -> ResolutionFrame:
        if not self._frames:
            raise ResolutionError("resolution stack is empty")
        return self._frames.pop()

    def is_empty(self) -> bool:
        return not self._frames

    @property
    def depth(self) -> int:
        return len(self._frames)

    def snapshot(self) -> tuple[ResolutionFrame, ...]:
        return tuple(self._frames)

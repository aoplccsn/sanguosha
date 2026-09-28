"""Human-only preview state; engine decisions are sent only after confirmation."""
from dataclasses import dataclass, field
from enum import Enum, auto


class UiMode(Enum):
    IDLE = auto()
    CARD_SELECTED = auto()
    TARGET_SELECTING = auto()
    TARGET_SELECTED_PENDING_CONFIRM = auto()
    RESPONDING_WITH_CARD = auto()
    MULTI_CARD_DISCARDING = auto()


@dataclass
class InteractionState:
    mode: UiMode = UiMode.IDLE
    request_id: str | None = None
    card_id: str | None = None
    target_id: str | None = None
    legal_targets: set[str] = field(default_factory=set)

    def reset(self, request_id: str | None = None, mode: UiMode = UiMode.IDLE) -> None:
        self.mode = mode
        self.request_id = request_id
        self.card_id = None
        self.target_id = None
        self.legal_targets.clear()

    def select_card(self, card_id: str, legal_targets: set[str]) -> None:
        self.card_id = card_id
        self.target_id = None
        self.legal_targets = legal_targets
        self.mode = UiMode.TARGET_SELECTING if legal_targets else UiMode.CARD_SELECTED

    def select_target(self, target_id: str) -> None:
        if target_id in self.legal_targets:
            self.target_id = target_id
            self.mode = UiMode.TARGET_SELECTED_PENDING_CONFIRM

    def select_response(self, card_id: str) -> None:
        self.card_id = card_id
        self.mode = UiMode.RESPONDING_WITH_CARD

"""Final result data for an identity match."""

from dataclasses import dataclass

from .ids import PlayerId


@dataclass(frozen=True, slots=True)
class VictoryResult:
    label: str
    winner_ids: tuple[PlayerId, ...]
    reason: str

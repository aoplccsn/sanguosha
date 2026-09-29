"""Typed counters for one player's current play phase."""

from dataclasses import dataclass, field

from .ids import CardDefinitionId, PlayerId


@dataclass(slots=True)
class PlayUsageState:
    player_id: PlayerId
    turn_number: int
    counts: dict[CardDefinitionId, int] = field(default_factory=dict)

    def count(self, definition_id: CardDefinitionId) -> int:
        return self.counts.get(definition_id, 0)

    def record(self, definition_id: CardDefinitionId) -> None:
        self.counts[definition_id] = self.count(definition_id) + 1

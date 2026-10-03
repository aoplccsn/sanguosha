"""Immutable card definitions and physical card identities."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .enums import CardCategory, Color, DamageNature, EquipmentSlot, Suit
from .ids import CardDefinitionId, CardInstanceId


@dataclass(frozen=True, slots=True)
class CardDefinition:
    id: CardDefinitionId
    name: str
    category: CardCategory
    subtype: str | None = None
    nature: DamageNature | None = None
    equipment_slot: EquipmentSlot | None = None
    attack_range: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.name:
            raise ValueError("card definition id and name are required")
        if self.attack_range is not None and self.attack_range < 1:
            raise ValueError("attack_range must be positive")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def nullifiable(self) -> bool:
        """Only trick effects may open a counter window; equipment/basic never do."""
        return (self.category in (CardCategory.TRICK, CardCategory.DELAYED_TRICK)
                and self.metadata.get('nullifiable', True) is not False)


@dataclass(frozen=True, slots=True)
class CardInstance:
    instance_id: CardInstanceId
    definition_id: CardDefinitionId
    suit: Suit
    rank: int

    def __post_init__(self) -> None:
        if not self.instance_id or not self.definition_id:
            raise ValueError("card instance and definition ids are required")
        if not 1 <= self.rank <= 13:
            raise ValueError("rank must be between 1 and 13")

    @property
    def color(self) -> Color:
        return Color.RED if self.suit in (Suit.HEART, Suit.DIAMOND) else Color.BLACK

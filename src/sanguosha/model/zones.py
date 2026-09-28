"""A game's sole location store is GameState.zones, keyed by ZoneRef."""

from dataclasses import dataclass, field
from enum import StrEnum

from .enums import EquipmentSlot
from .ids import CardInstanceId, PlayerId


class ZoneType(StrEnum):
    DRAW_PILE = "draw_pile"
    DISCARD_PILE = "discard_pile"
    HAND = "hand"
    EQUIPMENT = "equipment"
    JUDGMENT = "judgment"
    PROCESSING = "processing"
    REMOVED = "removed"
    SPECIAL = "special"


@dataclass(frozen=True, slots=True)
class ZoneRef:
    zone_type: ZoneType
    player_id: PlayerId | None = None
    equipment_slot: EquipmentSlot | None = None
    special_key: str | None = None

    def __post_init__(self) -> None:
        personal = self.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT, ZoneType.JUDGMENT)
        if personal != (self.player_id is not None):
            raise ValueError("personal zones require a player; shared zones must not have one")
        if (self.zone_type is ZoneType.EQUIPMENT) != (self.equipment_slot is not None):
            raise ValueError("equipment slot is required only for equipment zones")
        if (self.zone_type is ZoneType.SPECIAL) != (self.special_key is not None):
            raise ValueError("special key is required only for special zones")
        if self.special_key == "":
            raise ValueError("special key cannot be empty")


@dataclass(slots=True)
class CardZone:
    ref: ZoneRef
    card_ids: list[CardInstanceId] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.card_ids) != len(set(self.card_ids)):
            raise ValueError("card IDs cannot repeat in one zone")
        if self.ref.zone_type is ZoneType.EQUIPMENT and len(self.card_ids) > 1:
            raise ValueError("equipment slot holds at most one card")

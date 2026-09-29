"""Immutable character templates; never contain match state."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .enums import Gender, Kingdom
from .ids import CharacterId, SkillId


@dataclass(frozen=True, slots=True)
class CharacterDefinition:
    id: CharacterId
    name: str
    kingdom: Kingdom
    max_hp: int
    gender: Gender
    skill_ids: tuple[SkillId, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.name:
            raise ValueError("character id and name are required")
        if self.max_hp < 1:
            raise ValueError("max_hp must be positive")
        object.__setattr__(self, "skill_ids", tuple(self.skill_ids))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

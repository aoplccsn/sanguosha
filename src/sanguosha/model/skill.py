"""Skill descriptions only; triggers and effects belong to later phases."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .enums import SkillType
from .ids import SkillId


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    id: SkillId
    name: str
    description: str
    skill_type: SkillType
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.name:
            raise ValueError("skill id and name are required")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

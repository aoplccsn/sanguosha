"""Stable string identifiers. NewType prevents accidental cross-ID use in typing."""

from typing import NewType

PlayerId = NewType("PlayerId", str)
CardInstanceId = NewType("CardInstanceId", str)
CardDefinitionId = NewType("CardDefinitionId", str)
CharacterId = NewType("CharacterId", str)
SkillId = NewType("SkillId", str)

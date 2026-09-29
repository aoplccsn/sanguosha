"""Stable card definition lookup, separate from executable rules."""

from sanguosha.model.card import CardDefinition
from sanguosha.model.ids import CardDefinitionId

from .errors import EngineError


class UnknownCardDefinition(EngineError):
    pass


class CardDefinitionRegistry:
    def __init__(self) -> None:
        self._definitions: dict[CardDefinitionId, CardDefinition] = {}

    def register(self, definition: CardDefinition) -> None:
        if definition.id in self._definitions:
            raise EngineError(f"duplicate card definition {definition.id}")
        self._definitions[definition.id] = definition

    def get(self, definition_id: CardDefinitionId) -> CardDefinition:
        try:
            return self._definitions[definition_id]
        except KeyError as exc:
            raise UnknownCardDefinition(f"unknown card definition {definition_id}") from exc

"""Living-seat distance with equipment-driven range modifiers.

The zone store remains the sole source of equipped cards. Additional rule
modifiers (such as future character skills) can be composed through the
small DistanceModifier protocol.
"""

from typing import Protocol

from sanguosha.content.characters.standard import ALL_65_GENERAL_POOL
from sanguosha.model.enums import EquipmentSlot
from sanguosha.model.ids import PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .card_registry import CardDefinitionRegistry


class DistanceModifier(Protocol):
    def distance_delta(self, state: GameState, source: PlayerId, target: PlayerId) -> int: ...

    def attack_range(self, state: GameState, player: PlayerId, current: int) -> int: ...


class HorseModifier:
    def distance_delta(self, state: GameState, source: PlayerId, target: PlayerId) -> int:
        offensive = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, source, EquipmentSlot.OFFENSIVE_HORSE))
        defensive = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, target, EquipmentSlot.DEFENSIVE_HORSE))
        return int(bool(defensive)) - int(bool(offensive))

    def attack_range(self, state: GameState, player: PlayerId, current: int) -> int:
        return current


class CharacterDistanceModifier:
    """Declarative character distance effects in the shared distance path."""

    def distance_delta(self, state: GameState, source: PlayerId, target: PlayerId) -> int:
        character = _CHARACTERS.get(state.players[source].character_id)
        delta = -1 if character is not None and 'mashu' in character.skill_ids else 0
        if character is not None and 'tuntian' in character.skill_ids and 'tuntian' not in state.players[source].disabled_skills:
            delta -= len(state.cards_in(ZoneRef(ZoneType.SPECIAL, source, special_key='tian')))
        return delta

    def attack_range(self, state: GameState, player: PlayerId, current: int) -> int:
        return current


_CHARACTERS = {character.id: character for character in ALL_65_GENERAL_POOL}


class DistanceSystem:
    def __init__(self, definitions: CardDefinitionRegistry | None = None,
                 modifiers: tuple[DistanceModifier, ...] = (HorseModifier(), CharacterDistanceModifier())) -> None:
        self.definitions = definitions
        self.modifiers = modifiers

    def base_distance(self, state: GameState, source: PlayerId, target: PlayerId) -> int:
        living = tuple(pid for pid in state.seat_order if state.players[pid].is_alive)
        if source == target or source not in living or target not in living:
            raise ValueError("distance requires two distinct living players")
        difference = abs(living.index(source) - living.index(target))
        base = min(difference, len(living) - difference)
        return base

    def distance_between(self, state: GameState, source: PlayerId, target: PlayerId) -> int:
        base = self.base_distance(state, source, target)
        return max(1, base + sum(mod.distance_delta(state, source, target) for mod in self.modifiers))

    def attack_range(self, state: GameState, player: PlayerId) -> int:
        if player not in state.players or not state.players[player].is_alive:
            raise ValueError("attack range requires a living player")
        current = 1
        weapon = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, player, EquipmentSlot.WEAPON))
        if weapon and self.definitions is not None:
            definition = self.definitions.get(state.cards[weapon[0]].definition_id)
            current = definition.attack_range or 1
        for modifier in self.modifiers:
            current = modifier.attack_range(state, player, current)
        return max(1, current)

    def can_reach_with_slash(self, state: GameState, source: PlayerId, target: PlayerId) -> bool:
        try:
            return self.distance_between(state, source, target) <= self.attack_range(state, source)
        except ValueError:
            return False


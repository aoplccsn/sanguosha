"""Contextual suit interpretation without changing physical card data."""

from functools import lru_cache
from sanguosha.model.enums import Color, Suit


@lru_cache(maxsize=1)
def _skill_registry():
    # Lazy import keeps the skills/suits dependency acyclic at module load.
    from .skills import SkillRegistry
    return SkillRegistry()


def _hongyan(suit):
    return Suit.HEART if suit is Suit.SPADE else suit


SUIT_MODIFIERS = {'hongyan': _hongyan}


def effective_suit(state, card_id, owner_id=None):
    """Interpret a card for its owner or an explicit judgment/use context."""
    suit = state.cards[card_id].suit
    if owner_id is None:
        owner_id = next((ref.player_id for ref, zone in state.zones.items()
                         if ref.player_id is not None and card_id in zone.card_ids), None)
    if owner_id is None or owner_id not in state.players:
        return suit
    skills = _skill_registry()
    for skill_id, modifier in SUIT_MODIFIERS.items():
        if skills.has(state, owner_id, skill_id):
            suit = modifier(suit)
    return suit


def effective_color(state, card_id, owner_id=None):
    suit = effective_suit(state, card_id, owner_id)
    return Color.RED if suit in (Suit.HEART, Suit.DIAMOND) else Color.BLACK

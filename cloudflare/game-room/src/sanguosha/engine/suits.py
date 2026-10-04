"""Contextual suit interpretation without changing physical card data."""

from sanguosha.content.characters.standard import ALL_GENERAL_POOL
from sanguosha.model.enums import Color, Suit


_CHARACTER_SKILLS = {character.id: frozenset(character.skill_ids)
                     for character in ALL_GENERAL_POOL}


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
    skills = _CHARACTER_SKILLS.get(state.players[owner_id].character_id, ())
    for skill_id, modifier in SUIT_MODIFIERS.items():
        if skill_id in skills:
            suit = modifier(suit)
    return suit


def effective_color(state, card_id, owner_id=None):
    suit = effective_suit(state, card_id, owner_id)
    return Color.RED if suit in (Suit.HEART, Suit.DIAMOND) else Color.BLACK

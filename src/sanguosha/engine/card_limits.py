"""Turn-scoped use/response restrictions evaluated against the final card."""
from itertools import combinations
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard
from .suits import effective_color, effective_suit


def card_allowed(state, player_id, material_ids, virtual_card=None):
    limits = state.metadata.get('qianxi_limits', {})
    if not limits or not material_ids:
        return True
    hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
    # The pinned ExpPattern requires every physical subcard to be in hand.
    if not all(cid in hand for cid in material_ids):
        return True
    color = (virtual_card.color if virtual_card is not None else
             effective_color(state, material_ids[0], player_id) if len(material_ids) == 1 else
             VirtualCard.spear(state, material_ids,
                 lambda st, cid: effective_suit(st, cid, player_id)).color)
    if color is None:
        return True
    return not any(effect['target'] == player_id and effect['color'] == color.value
                   and effect['turn'] == state.turn_number
                   and source in state.players and state.players[source].is_alive
                   for source, effect in limits.items())


def legal_pairs(state, player_id, card_ids):
    return tuple(pair for pair in combinations(card_ids, 2)
                 if card_allowed(state, player_id, pair))


def clear_source(state, source):
    effect = state.metadata.get('qianxi_limits', {}).pop(source, None)
    if effect and effect['target'] in state.players:
        target = state.players[effect['target']]
        target.marks.pop('qianxi_' + effect['color'] + '_' + source, None)

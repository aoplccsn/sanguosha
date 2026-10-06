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


def validate_view_as_limits(state, player_id, material_ids, definition_id, *, recast=False, skills=None, skill_id=None):
    """Apply final-card use limits before a view-as material leaves its zone."""
    from .card_rules import InvalidCardUse
    from .qiaoshui import prohibited
    from sanguosha.model.enums import Phase
    usage = state.play_usage
    if (player_id not in state.players or not state.players[player_id].is_alive
            or state.current_player_id != player_id or state.current_phase is not Phase.PLAY
            or usage is None or usage.player_id != player_id or usage.turn_number != state.turn_number
            or skill_id is not None and (skills is None or not skills.has(state, player_id, skill_id))):
        raise InvalidCardUse('view-as actor or skill is no longer available')
    if recast and definition_id == 'trick.iron_chain':
        return
    if prohibited(state, player_id, definition_id):
        raise InvalidCardUse('view-as card use is prohibited')
    if not card_allowed(state, player_id, material_ids):
        raise InvalidCardUse('view-as hand color is prohibited')

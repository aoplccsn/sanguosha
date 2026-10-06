"""Damage uses the effective card identity, never the material's printed type."""


def damage_definition(state, action):
    virtual = getattr(action, 'virtual_card', None)
    if virtual is not None:
        return virtual.definition_id
    kind = getattr(action, 'card_kind', '')
    if kind == 'slash':
        return 'basic.slash'
    if kind == 'duel':
        return 'trick.duel'
    if kind == 'trick':
        return 'trick.'
    card = state.cards.get(action.card_id)
    return card.definition_id if card is not None else ''

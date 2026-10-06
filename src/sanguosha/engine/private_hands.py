"""Explicit, viewer-scoped grants for skills that authorize viewing a hand."""


def can_view_hand(state,viewer,owner):
    if viewer==owner:return True
    if viewer not in state.players or owner not in state.players:return False
    if not state.players[viewer].is_alive or not state.players[owner].is_alive:return False
    from .suits import _skill_registry
    for key,skill in (('gongxin_reveal','gongxin'),('poxi_reveal','poxi')):
        grant=state.metadata.get(key,{})
        if grant.get('actor')==viewer and grant.get('target')==owner and _skill_registry().has(state,viewer,skill):return True
    return False

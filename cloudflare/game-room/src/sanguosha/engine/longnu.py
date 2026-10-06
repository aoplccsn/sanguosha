"""Locked Longnu card identity and per-card Slash modifiers."""
from sanguosha.model.enums import Phase,Color
from sanguosha.model.zones import ZoneRef,ZoneType


def form(state,skills,pid):
    return state.players[pid].marks.get('longnu_form',0) if skills is not None and skills.has(state,pid,'longnu') else 0


def longnu_definition(state,skills,pid,definition,cid):
    active=form(state,skills,pid)
    if not active or cid is None:return definition
    # Processing cards retain the identity fixed at their use/response commitment.
    if cid not in state.cards_in(ZoneRef(ZoneType.HAND,pid)) and cid not in state.cards_in(ZoneRef(ZoneType.PROCESSING)):return definition
    if active==1:
        from .suits import effective_color
        if effective_color(state,cid,pid) is Color.RED:return 'basic.fire_slash'
    if active==2 and definition.startswith(('trick.','delayed.')):return 'basic.thunder_slash'
    return definition


def modifiers(state,skills,pid,cid):
    physical=state.cards[cid].definition_id
    definition=longnu_definition(state,skills,pid,physical,cid)
    active=form(state,skills,pid)
    if active==1:
        from .suits import effective_color
        return definition=='basic.fire_slash' and effective_color(state,cid,pid) is Color.RED,False
    return False,active==2 and definition=='basic.thunder_slash'

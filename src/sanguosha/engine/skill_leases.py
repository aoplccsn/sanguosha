"""Duorui leases suppress a skill without overwriting permanent losses."""
from .skill_grants import add_grant,remove_grant


def leases(state):return state.metadata.get('duorui_leases',{})


def suppressed(state,pid,skill):
    return any(item['target']==pid and item['skill']==skill for item in leases(state).values())


def begin_lease(state,source,target,skill):
    tag='duorui:'+source+':'+str(state.turn_number)
    state.metadata.setdefault('duorui_leases',{})[source]={'target':target,'skill':skill,'tag':tag,'created_turn':state.turn_number}
    add_grant(state,source,skill,tag)
    if skill=='jieying_liubei':
        from .chaining import set_chained

        set_chained(state,source,True,None)


def expire_target(state,target):
    for source,item in tuple(leases(state).items()):
        if item['target']==target:
            remove_grant(state,source,item['skill'],item['tag'])
            del state.metadata['duorui_leases'][source]


def on_death(state,pid):
    expire_target(state,pid)
    item=leases(state).get(pid)
    if item is not None:remove_grant(state,pid,item['skill'],item['tag'])

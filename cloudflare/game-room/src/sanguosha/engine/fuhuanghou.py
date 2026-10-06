"""Turn-scoped Zhuikong targets and shared Qiuyuan Slash queues."""
def target_allowed(state,user,target):
    return user==target or state.players[user].marks.get('zhuikong_self_only')!=state.turn_number


def clear_turn(state,pid):
    state.players[pid].marks.pop('zhuikong_self_only',None)
    effects=state.metadata.get('zhuikong_distance',{})
    for key,item in tuple(effects.items()):
        if item['source']==pid:del effects[key]


def fixed_distance(state,source,target):
    return any(item['source']==source and item['target']==target and item['turn']==state.turn_number
               for item in state.metadata.get('zhuikong_distance',{}).values())


def slash_window(state,root,targets=(),known=()):
    return state.metadata.setdefault('slash_target_windows',{}).setdefault(root,{'targets':list(targets),'known':list(dict.fromkeys((*known,*targets))),'cursor':0})


def add_slash_target(state,root,source,target,skills):
    from .yj2011_tier3 import hand
    w=slash_window(state,root)
    if (target==source or not state.players[target].is_alive or target in w['known'] or not target_allowed(state,source,target)
        or skills.has(state,target,'kongcheng') and not hand(state,target)):return False
    w['known'].append(target)
    cursor=w['cursor'];pending=(*w['targets'][cursor:],target)
    w['targets']=w['targets'][:cursor]+[q for q in state.seat_order if q in pending]
    return True

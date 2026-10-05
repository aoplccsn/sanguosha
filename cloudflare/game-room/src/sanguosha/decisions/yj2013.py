"""YJ2013 heuristics use own cards and public posture/card counts."""
from sanguosha.engine.requests import RequestType,Decision
from sanguosha.engine.yj2011_tier3 import hand

def decide(provider,state,r):
    pid=r.player_id;kind=r.request_type;prompt=r.prompt
    def keep(c):return {'basic.peach':9,'basic.dodge':6,'trick.nullification':7}.get(state.cards[c].definition_id,2)
    if kind is RequestType.CHOOSE_OPTION and 'skill:junxing' in r.choices:
        own=hand(state,pid)
        if len(own)>=3 and sum(keep(c)<=2 for c in own)>=1:
            return Decision(r.request_id,pid,'skill:junxing')
    if '【龙吟】' in prompt:
        if kind is RequestType.YES_NO:
            source=r.subject_player_id
            value=source==pid or source in state.players and provider._priority(state,pid,source)<0
        elif kind is RequestType.CHOOSE_CARD:value=min(r.eligible_card_ids,key=keep)
        else:return None
        r.validate(value)
        return Decision(r.request_id,pid,value)
    if '【峻刑】' in prompt:
        if kind is RequestType.CHOOSE_CARDS:
            if r.min_count:
                value=tuple(sorted(r.eligible_card_ids,key=keep)[:1])
            else:
                value=() if not state.players[pid].face_up else tuple(sorted(r.eligible_card_ids,key=keep)[:1])
        elif kind is RequestType.CHOOSE_PLAYER:
            def score(q):
                priority=provider._priority(state,pid,q)
                return priority if state.players[q].face_up else -priority+2
            value=max(r.allowed_player_ids,key=score)
        else:return None
    elif '【御策】' in prompt:
        if kind is RequestType.YES_NO:value=True
        elif kind is RequestType.CHOOSE_CARD:value=min(r.eligible_card_ids,key=keep)
        elif kind is RequestType.CHOOSE_CARDS:
            value=tuple(sorted(r.eligible_card_ids,key=keep)[:1]) if provider._priority(state,pid,r.subject_player_id)>0 else ()
        else:return None
    else:return None
    r.validate(value)
    return Decision(r.request_id,pid,value)

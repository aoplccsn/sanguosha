"""YJ2013 heuristics use own cards and public posture/card counts."""
from sanguosha.engine.requests import RequestType,Decision
from sanguosha.engine.yj2011_tier3 import hand

def decide(provider,state,r):
    pid=r.player_id;kind=r.request_type;prompt=r.prompt
    def keep(c):return {'basic.peach':9,'basic.dodge':6,'trick.nullification':7}.get(state.cards[c].definition_id,2)
    if kind is RequestType.CHOOSE_OPTION and 'skill:mieji' in r.choices:
        if any(provider._priority(state,pid,q)>0 for q in state.seat_order if q!=pid and state.players[q].is_alive):return Decision(r.request_id,pid,'skill:mieji')
    if '【灭计】' in prompt:
        if kind is RequestType.CHOOSE_CARD:value=min(r.eligible_card_ids,key=keep)
        elif kind is RequestType.CHOOSE_PLAYER:value=max(r.allowed_player_ids,key=lambda q:provider._priority(state,pid,q))
        elif kind is RequestType.CHOOSE_CARDS:value=min(r.legal_card_sets,key=lambda cards:sum(keep(c) for c in cards))
        else:return None
        r.validate(value);return Decision(r.request_id,pid,value)
    if '【直言】' in prompt:
        value=True if kind is RequestType.YES_NO else min(r.allowed_player_ids,key=lambda q:(provider._priority(state,pid,q),state.players[q].hp))
        r.validate(value);return Decision(r.request_id,pid,value)
    if kind is RequestType.CHOOSE_OPTION and 'skill:danshou' in r.choices:
        own=hand(state,pid)
        if len(own)>=2 and any(provider._priority(state,pid,q)>0 for q in state.seat_order if q!=pid and state.players[q].is_alive):return Decision(r.request_id,pid,'skill:danshou')
    if kind is RequestType.CHOOSE_OPTION and 'skill:fencheng' in r.choices:
        targets=[q for q in state.seat_order if q!=pid and state.players[q].is_alive]
        score=sum((1 if provider._priority(state,pid,q)>0 else -1)*(3 if state.players[q].hp<=2 else 1) for q in targets)
        if score>=2:return Decision(r.request_id,pid,'skill:fencheng')
    if '【焚城】' in prompt:
        n=r.minimum_nonempty_count
        ordered=sorted(r.eligible_card_ids,key=keep)
        value=tuple(ordered[:n]) if state.players[pid].hp<=2 or n<=2 and sum(keep(c) for c in ordered[:n])<=5 else ()
        r.validate(value);return Decision(r.request_id,pid,value)
    if '【胆守】' in prompt:
        if kind is RequestType.CHOOSE_CARDS:value=tuple(sorted(r.eligible_card_ids,key=keep)[:r.min_count])
        elif kind is RequestType.CHOOSE_PLAYER:value=max(r.allowed_player_ids,key=lambda q:provider._priority(state,pid,q))
        elif kind is RequestType.CHOOSE_CARD:
            own=[c for c in r.eligible_card_ids if c in hand(state,pid)]
            public=[c for c in r.eligible_card_ids if c not in hand(state,r.subject_player_id)]
            value=min(own,key=keep) if own else public[0] if public else r.eligible_card_ids[0]
        else:return None
        r.validate(value);return Decision(r.request_id,pid,value)
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

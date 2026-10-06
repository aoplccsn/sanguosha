"""God prototype heuristics over own cards, public marks, posture and equipment."""
from sanguosha.engine.requests import RequestType,Decision
from sanguosha.engine.yj2011_tier3 import hand


def decide(provider,state,r):
    pid=r.player_id;kind=r.request_type
    def enemy(q):return provider._priority(state,pid,q)>0
    if '【劫营】' in r.prompt:
        if kind is RequestType.YES_NO:
            value=any(q!=pid and state.players[q].is_alive and enemy(q) for q in state.seat_order)
        elif kind is RequestType.CHOOSE_PLAYER:
            value=max(r.allowed_player_ids,key=lambda q:(provider._priority(state,pid,q),len(hand(state,q))))
        else:return None
        r.validate(value);return Decision(r.request_id,pid,value)
    if kind is RequestType.CHOOSE_OPTION and 'skill:poxi' in r.choices:
        if any(q!=pid and state.players[q].is_alive and enemy(q) and len(hand(state,q))>=2 for q in state.seat_order):return Decision(r.request_id,pid,'skill:poxi')
    if '【魄袭】' in r.prompt:
        if kind is RequestType.CHOOSE_PLAYER:
            value=max(r.allowed_player_ids,key=lambda q:(provider._priority(state,pid,q),len(hand(state,q))))
        elif kind is RequestType.CHOOSE_CARDS:
            from itertools import product
            from sanguosha.engine.private_hands import can_view_hand
            if not can_view_hand(state,pid,r.subject_player_id):return None
            own=set(hand(state,pid))
            def keep(c):return {'basic.peach':9,'basic.dodge':5,'trick.nullification':6}.get(state.cards[c].definition_id,2)
            groups=[sorted(group,key=lambda c:keep(c) if c in own else -keep(c))[:3] for group in r.exclusive_card_groups]
            def score(cards):
                n=sum(c in own for c in cards)
                effect={0:-5,1:-4,2:0,3:4 if state.players[pid].hp<state.players[pid].max_hp else 0,4:8}[n]
                return effect+sum(-keep(c) if c in own else keep(c) for c in cards)
            candidates=list(product(*groups)) if len(groups)==4 else []
            value=max(candidates,key=score) if candidates else ()
            if value and score(value)<0:value=()
        else:return None
        r.validate(value);return Decision(r.request_id,pid,tuple(value) if kind is RequestType.CHOOSE_CARDS else value)
    if kind is RequestType.CHOOSE_OPTION and 'skill:zhanhuo' in r.choices:
        targets=[q for q in state.seat_order if q!=pid and state.players[q].is_alive and state.players[q].chained and enemy(q)]
        if targets and any(state.players[q].hp<=2 or any(ref.player_id==q and ref.equipment_slot is not None and z.card_ids for ref,z in state.zones.items()) for q in targets):return Decision(r.request_id,pid,'skill:zhanhuo')
    if not any(name in r.prompt for name in ('【摧克】','【绽火】')):return None
    if kind is RequestType.YES_NO:
        if '所有其他角色' in r.prompt:
            value=sum((1 if enemy(q) else -1)*(2 if state.players[q].hp<=1 else 1) for q in state.seat_order if q!=pid and state.players[q].is_alive)>0
        else:value=any(enemy(q) for q in state.seat_order if q!=pid and state.players[q].is_alive)
    elif kind is RequestType.CHOOSE_PLAYER:
        value=max(r.allowed_player_ids,key=lambda q:(provider._priority(state,pid,q),-state.players[q].hp))
    elif kind is RequestType.CHOOSE_PLAYERS:
        targets=sorted(r.allowed_player_ids,key=lambda q:(provider._priority(state,pid,q),-state.players[q].hp),reverse=True)
        enemies=[q for q in targets if enemy(q)]
        value=tuple((enemies or targets)[:r.max_count])
    elif kind is RequestType.CHOOSE_CARD:
        public=[c for c in r.eligible_card_ids if c not in hand(state,r.subject_player_id)]
        value=public[0] if public else r.eligible_card_ids[0]
    else:return None
    r.validate(value);return Decision(r.request_id,pid,value)

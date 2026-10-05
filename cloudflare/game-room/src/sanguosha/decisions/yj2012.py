"""Minimal YJ2012 heuristics over own cards and public state only."""
from sanguosha.engine.requests import Decision, RequestType
from sanguosha.engine.yj2011_tier3 import hand


def decide(provider,state,r):
    pid=r.player_id; kind=r.request_type; prompt=r.prompt; p=state.players[pid]
    if kind is RequestType.CHOOSE_OPTION and 'skill:qice' in r.choices:
        own=hand(state,pid)
        if len(own)<=2 and not any(state.cards[c].definition_id=='basic.peach' for c in own):
            return Decision(r.request_id,pid,'skill:qice')
    if '【奇策】' in prompt:
        if kind is RequestType.CHOOSE_OPTION:
            order=('trick.ex_nihilo','trick.snatch','trick.dismantlement','trick.duel','trick.iron_chain',
                   'trick.amazing_grace','trick.god_salvation','trick.savage_assault','trick.archery_attack')
            value=next((d for d in order if d in r.choices),r.choices[0])
        elif kind is RequestType.CHOOSE_PLAYERS:
            candidates=sorted(r.allowed_player_ids,key=lambda q:provider._priority(state,pid,q),reverse=True)
            value=tuple(candidates[:r.min_count])
        else:
            return None
        r.validate(value)
        return Decision(r.request_id,pid,value)
    if kind is RequestType.CHOOSE_OPTION and 'skill:gongqi' in r.choices:
        own=hand(state,pid)
        slashes=sum(state.cards[c].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash') for c in own)
        if slashes and len(own)>=3: return Decision(r.request_id,pid,'skill:gongqi')
    if kind is RequestType.CHOOSE_OPTION and 'skill:jiefan' in r.choices:
        if any(q!=pid and state.players[q].is_alive and provider._priority(state,pid,q)<0 and len(hand(state,q))<=1 for q in state.seat_order):
            return Decision(r.request_id,pid,'skill:jiefan')
    if kind is RequestType.CHOOSE_OPTION and 'skill:anxu' in r.choices:
        return Decision(r.request_id,pid,'skill:anxu')
    if kind is RequestType.CHOOSE_OPTION and 'skill:paiyi' in r.choices:
        from sanguosha.engine.yj2012 import power_zone
        powers=len(state.cards_in(power_zone(pid)))
        lethal=any(q!=pid and state.players[q].is_alive and state.players[q].hp==1
                   and provider._priority(state,pid,q)>0 and len(hand(state,q))+2>len(hand(state,pid))
                   for q in state.seat_order)
        if powers>=2 or lethal: return Decision(r.request_id,pid,'skill:paiyi')
    if not any('【'+name+'】' in prompt for name in ('权计','自立','排异','将驰','自守','智愚','伏枥','安恤','追忆','秘计','弓骑','解烦')):
        return None
    def keep(cid):
        return {'basic.peach':9,'basic.dodge':6,'trick.nullification':7,'basic.slash':3}.get(state.cards[cid].definition_id,2)
    value=None
    if kind is RequestType.YES_NO:
        value=True
        if '自守' in prompt:
            own=hand(state,pid)
            attacks=sum(state.cards[c].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash','trick.duel') for c in own)
            value=p.hp<=2 or attacks==0
    elif kind is RequestType.CHOOSE_OPTION:
        if '自立' in prompt: value='recover' if 'recover' in r.choices and p.hp<=2 else 'draw'
        elif '秘计' in prompt:
            value=max(r.choices,key=int)
        elif '将驰' in prompt:
            own=hand(state,pid)
            slashes=sum(state.cards[c].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash') for c in own)
            value='chi' if slashes>=2 and p.hp>=2 else 'jiang' if slashes==0 else 'default'
    elif kind is RequestType.CHOOSE_CARD:
        value=(r.eligible_card_ids[0] if r.subject_player_id not in (None,pid)
               else min(r.eligible_card_ids,key=keep))
    elif kind is RequestType.CHOOSE_CARDS:
        if '解烦' in prompt:
            allied=r.subject_player_id==pid or provider._priority(state,pid,r.subject_player_id)<0
            value=() if allied else tuple(sorted(r.eligible_card_ids,key=keep)[:r.max_count])
        else:
            value=tuple(sorted(r.eligible_card_ids,key=keep)[:r.max_count])
    elif kind is RequestType.CHOOSE_PLAYER and '排异' in prompt:
        # Opponent card counts are public; definitions are never read here.
        def score(q):
            allied=q==pid or provider._priority(state,pid,q)<0
            more=len(hand(state,q))+2>len(hand(state,pid)) if q!=pid else False
            return (4 if allied else -3)+(0 if not more else -5 if allied else 5)+(3 if not allied and more and state.players[q].hp==1 else 0)
        value=max(r.allowed_player_ids,key=score)
    elif kind is RequestType.CHOOSE_PLAYER:
        if '第一名' in prompt or '弃牌目标' in prompt:
            value=max(r.allowed_player_ids,key=lambda q:(provider._priority(state,pid,q),len(hand(state,q))))
        else:
            value=min(r.allowed_player_ids,key=lambda q:(provider._priority(state,pid,q),len(hand(state,q))))
    if value is None: return None
    r.validate(value)
    return Decision(r.request_id,pid,value)

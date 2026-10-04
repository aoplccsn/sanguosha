"""YJ2011 heuristics use own cards and public target state only."""
from sanguosha.engine.requests import Decision, RequestType
from sanguosha.model.zones import ZoneRef, ZoneType


def decide_yj2011(provider,state,request,player_id):
    kind=request.request_type; prompt=request.prompt
    if not any(name in prompt for name in ('【破军】','【伤逝】','【旋风】','【举荐】')):
        return None
    priority=lambda pid:provider._priority(state,player_id,pid)
    value=None
    if kind is RequestType.YES_NO:
        if '【伤逝】' in prompt:
            value=True
        elif '【破军】' in prompt:
            target=request.subject_player_id
            p=state.players[target]
            value=((priority(target)>0 and p.face_up and p.hp<=2)
                   or (priority(target)<0 and not p.face_up))
        elif '【旋风】' in prompt:
            value=any(pid!=player_id and state.players[pid].is_alive and priority(pid)>0
                and any(ref.player_id==pid and ref.zone_type in (ZoneType.HAND,ZoneType.EQUIPMENT)
                        and zone.card_ids for ref,zone in state.zones.items()) for pid in state.seat_order)
        else:
            value=any(pid!=player_id and p.is_alive and priority(pid)<0 for pid,p in state.players.items())
    elif kind is RequestType.CHOOSE_PLAYER:
        if '【举荐】' in prompt:
            value=min(request.allowed_player_ids,key=lambda pid:(priority(pid),
                -(state.players[pid].max_hp-state.players[pid].hp),state.players[pid].face_up))
        else:
            value=max(request.allowed_player_ids,key=lambda pid:priority(pid))
    elif kind is RequestType.CHOOSE_CARD:
        if '【旋风】' in prompt:
            # Face-down hand candidates are opaque to the AI. Prefer a public
            # equipment card; otherwise choose an opaque candidate by position.
            public={cid for ref,z in state.zones.items() if ref.player_id==request.subject_player_id
                    and ref.zone_type is ZoneType.EQUIPMENT for cid in z.card_ids}
            value=next((cid for cid in request.eligible_card_ids if cid in public),request.eligible_card_ids[0])
        else:
            keep={'trick.nullification':4,'equipment.armor.eight_trigrams':3}
            value=min(request.eligible_card_ids,key=lambda cid:keep.get(state.cards[cid].definition_id,0))
    elif kind is RequestType.CHOOSE_OPTION and '【举荐】' in prompt:
        p=state.players[player_id]
        value=('recover' if p.hp<=2 and 'recover' in request.choices else
               'reset' if not p.face_up and 'reset' in request.choices else 'draw')
    if value is None: return None
    request.validate(value)
    return Decision(request.request_id,player_id,value)

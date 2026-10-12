"""Small deterministic boundary choices using own cards and public targets."""
from sanguosha.engine.requests import Decision, RequestType
from sanguosha.model.zones import ZoneRef, ZoneType

def decide(provider, state, request):
    pid, kind, prompt = request.player_id, request.request_type, request.prompt
    priority = lambda q: -100 if q == pid else provider._priority(state, pid, q)
    own = state.cards_in(ZoneRef(ZoneType.HAND, pid))
    def keep(cid):
        return {'basic.peach':9, 'basic.dodge':6, 'trick.nullification':7,
                'basic.slash':3}.get(state.cards[cid].definition_id, 2)
    def reply(value):
        request.validate(value)
        return Decision(request.request_id, pid, value)
    if kind is RequestType.CHOOSE_OPTION and 'skill:jie_qimou' in request.choices:
        slashes = sum('slash' in state.cards[cid].definition_id for cid in own)
        if (state.players[pid].hp >= 3 and slashes >= 2 and any(q != pid
                and state.players[q].is_alive and priority(q) > 0 for q in state.seat_order)):
            return reply('skill:jie_qimou')
    if '【狂骨】' in prompt and kind is RequestType.CHOOSE_OPTION:
        p=state.players[pid]
        return reply('recover' if 'recover' in request.choices and (p.hp <= 2 or p.max_hp-p.hp >= 2) else 'draw')
    if '【奇谋】' in prompt and kind is RequestType.CHOOSE_OPTION:
        safe=[int(x) for x in request.choices if int(x)<state.players[pid].hp]
        return reply(str(min(safe))) if safe else reply(request.choices[0])
    if '【胆守】' in prompt and kind is RequestType.YES_NO:
        import re
        count=int(re.search(r'弃置 (\d+)',prompt).group(1))
        target=request.subject_player_id
        return reply(target is not None and priority(target)>0 and
            (count <= 2 or state.players[target].hp <= 1))
    combat = any(name in prompt for name in ('【破军】', '【旋风】', '【替身】', '【胆守】'))
    if not combat:
        return None
    if kind is RequestType.YES_NO:
        if '【破军】' in prompt:
            return reply(request.subject_player_id is not None and priority(request.subject_player_id) > 0)
        if '【替身】' in prompt:
            # Only own cards and public equipment are considered for the cost.
            cards = tuple(cid for ref,zone in state.zones.items()
                if ref.player_id == pid and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT) for cid in zone.card_ids)
            costs = [cid for cid in cards if state.cards[cid].definition_id.startswith(('trick.', 'delayed.', 'equipment.horse.'))]
            return reply(sum(keep(cid) for cid in costs) <= 8)
    if kind is RequestType.CHOOSE_OPTION and '【旋风】' in prompt:
        enemies = [q for q in state.seat_order if q != pid and state.players[q].is_alive
                   and priority(q) > 0 and any(ref.player_id == q and zone.card_ids
                   for ref,zone in state.zones.items() if ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT))]
        return reply('discard' if 'discard' in request.choices and enemies else 'cancel')
    if kind is RequestType.CHOOSE_PLAYER:
        friendly = '接收' in prompt
        chooser = min if friendly else max
        return reply(chooser(request.allowed_player_ids, key=priority))
    if kind in (RequestType.CHOOSE_CARD, RequestType.CHOOSE_CARDS):
        other = request.subject_player_id not in (None, pid)
        candidates = list(request.eligible_card_ids)
        if other:
            public = {cid for ref,zone in state.zones.items() if ref.player_id == request.subject_player_id
                      and ref.zone_type is ZoneType.EQUIPMENT for cid in zone.card_ids}
            candidates.sort(key=lambda cid: cid not in public)
        else:
            candidates.sort(key=keep)
        if kind is RequestType.CHOOSE_CARD:
            return reply(candidates[0])
        count = request.max_count if '【破军】' in prompt else request.min_count
        if request.legal_card_sets:
            return reply(request.legal_card_sets[0])
        return reply(tuple(candidates[:count]))
    return reply(request.timeout_value())

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
    # Basic conversions remain legal choices submitted through the same request.
    converted = [x for x in request.eligible_card_ids if x.startswith('virtual:jie_jianying:')]
    if kind is RequestType.RESPOND_WITH_CARD and converted:
        if (request.required_definition_id == 'basic.peach' and request.subject_player_id is not None
                and priority(request.subject_player_id) > 0):
            from sanguosha.engine.requests import PASS_RESPONSE
            return reply(PASS_RESPONSE)
        physical = [x for x in request.eligible_card_ids if x in state.cards]
        candidates = physical + converted
        return reply(min(candidates, key=lambda x: keep(x.split(':',2)[2]) if x.startswith('virtual:') else keep(x)))
    if kind is RequestType.CHOOSE_OPTION:
        choices=request.choices
        if 'skill:jie_paiyi' in choices:
            return reply('skill:jie_paiyi')
        enemies=[q for q in state.seat_order if q!=pid and state.players[q].is_alive and priority(q)>0]
        if 'skill:jie_mieji' in choices and enemies:
            return reply('skill:jie_mieji')
        if 'skill:jie_fencheng' in choices:
            allies=[q for q in state.seat_order if q!=pid and state.players[q].is_alive and priority(q)<0]
            if len(enemies)>=2 and len(enemies)>len(allies) and all(state.players[q].hp>2 for q in allies):
                return reply('skill:jie_fencheng')
        if 'skill:jie_jianying' in choices:
            slashes=sum('slash' in state.cards[cid].definition_id for cid in own)
            if state.players[pid].hp<state.players[pid].max_hp or enemies and not slashes:
                return reply('skill:jie_jianying')
    advanced = any(x in prompt for x in ('【权计】','【自立】','【排异】','【绝策】','【灭计】','【焚城】','【渐营】','【倾袭】'))
    scoped = (str(state.players[pid].character_id).startswith('boundary_')
              or 'boundary' in request.originating_action_id or 'jie-' in request.originating_action_id)
    if advanced and scoped:
        if kind is RequestType.YES_NO:
            if any(x in prompt for x in ('【权计】','【渐营】')):
                return reply(True)
            if '【倾袭】' in prompt:
                return reply(request.subject_player_id is not None and priority(request.subject_player_id)>0)
            if '【绝策】' in prompt:
                return reply(any(q!=pid and state.players[q].is_alive and priority(q)>0
                    for q in state.metadata.get('jie_juece_lost',())))
        if kind is RequestType.CHOOSE_PLAYER:
            if '【排异】' in prompt:
                lethal=[q for q in request.allowed_player_ids if q!=pid and priority(q)>0
                        and state.players[q].hp<=1 and len(state.cards_in(ZoneRef(ZoneType.HAND,q)))+2>len(own)]
                if lethal: return reply(lethal[0])
                if pid in request.allowed_player_ids: return reply(pid)
                return reply(min(request.allowed_player_ids,key=priority))
            return reply(max(request.allowed_player_ids,key=priority))
        if kind is RequestType.CHOOSE_PLAYERS:
            selected=sorted(request.allowed_player_ids,key=priority,reverse=True)
            return reply(tuple(selected[:request.min_count]))
        if kind is RequestType.CHOOSE_CARD:
            return reply(min(request.eligible_card_ids,key=keep))
        if kind is RequestType.CHOOSE_CARDS:
            cards=sorted(request.eligible_card_ids,key=keep)
            count=request.min_count
            if request.minimum_nonempty_count:
                cost=sum(keep(c) for c in cards[:request.minimum_nonempty_count])
                count=request.minimum_nonempty_count if state.players[pid].hp<=2 or cost<=7 else 0
            if request.legal_card_sets: return reply(request.legal_card_sets[0])
            return reply(tuple(cards[:count]))
        if kind is RequestType.CHOOSE_OPTION:
            choices=request.choices
            if '【自立】' in prompt:
                p=state.players[pid]
                return reply('recover' if 'recover' in choices and p.hp<p.max_hp else 'draw')
            if '【渐营】' in prompt:
                if 'basic.peach' in choices: return reply('basic.peach')
                if 'basic.slash' in choices: return reply('basic.slash')
                return reply(choices[0])
            if '【灭计】' in prompt:
                tricks=[c for c in own if state.cards[c].definition_id.startswith(('trick.','delayed.'))]
                ordinary=[c for c in own if c not in tricks]
                give=min((keep(c) for c in tricks),default=100)
                discard=sum(sorted(keep(c) for c in ordinary)[:2]) if ordinary else 100
                return reply('give_trick' if 'give_trick' in choices and give<=discard else choices[-1])
            return reply(request.timeout_value())
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
        counts = {q: sum(len(zone.card_ids) for ref, zone in state.zones.items()
                        if ref.player_id == q and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT))
                  for q in state.seat_order if q != pid and state.players[q].is_alive}
        safe = sum(counts[q] for q in enemies) >= min(2, sum(counts.values()))
        return reply('discard' if 'discard' in request.choices and enemies and safe else 'cancel')
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

"""YJ2011 choices use own cards, public equipment and public player state."""
from sanguosha.engine.requests import Decision, RequestType
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.engine.yj2011_tier3 import equipped_cards, hand


def decide(provider, state, request):
    pid = request.player_id
    priority = lambda q: -100 if q == pid else provider._priority(state, pid, q)
    kind, prompt = request.request_type, request.prompt
    def keep(cid):
        return {'basic.peach': 9, 'basic.dodge': 5, 'trick.nullification': 6,
                'basic.slash': 3}.get(state.cards[cid].definition_id, 1)
    def equip_value(q):
        return sum(3 if 'armor' in state.cards[cid].definition_id else 2
                   for cid in equipped_cards(state, q))
    def pair_score(a, b):
        weight = lambda q: 1 if priority(q) < 0 else -1
        return (weight(a) - weight(b)) * (equip_value(b) - equip_value(a))
    living = [q for q in state.seat_order if state.players[q].is_alive]
    lost = max(0, state.players[pid].max_hp - state.players[pid].hp)
    pairs = [(a, b) for i, a in enumerate(living) for b in living[i+1:]
             if abs(len(equipped_cards(state, a)) - len(equipped_cards(state, b))) <= lost]
    best_pair = max(pairs, key=lambda pair: pair_score(*pair), default=None)
    value = None
    if kind is RequestType.CHOOSE_OPTION and any(x.startswith('skill:') for x in request.choices):
        own = hand(state, pid)
        if 'skill:xinzhan' in request.choices:
            value = 'skill:xinzhan'
        elif ('skill:xianzhen' in request.choices and own
              and max(state.cards[cid].rank for cid in own) >= 10
              and any(priority(q) > 0 and hand(state, q) for q in living if q != pid)
              and any(state.cards[cid].definition_id in ('basic.slash', 'basic.wine', 'basic.fire_slash', 'basic.thunder_slash') for cid in own)):
            value = 'skill:xianzhen'
        elif 'skill:ganlu' in request.choices and best_pair and pair_score(*best_pair) > 0:
            value = 'skill:ganlu'
        elif 'skill:mingce' in request.choices and any(q != pid and priority(q) < 0 for q in living):
            value = 'skill:mingce'
        elif ('skill:jiushi' in request.choices and any(x.startswith('use:')
                and state.cards[x[4:]].definition_id in ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash')
                for x in request.choices) and any(priority(q) > 0 for q in living if q != pid)):
            value = 'skill:jiushi'
        if value:
            return Decision(request.request_id, pid, value)
    names = ('【落英】', '【酒诗】', '【恩怨】', '【眩惑】', '【心战】', '【甘露】', '【补益】', '【明策】', '【陷阵】')
    if not any(name in prompt for name in names):
        return None
    if kind is RequestType.YES_NO:
        if '【落英】' in prompt or '【酒诗】' in prompt:
            value = True
        elif '【恩怨】' in prompt:
            q = request.subject_player_id
            value = priority(q) < 0 if '给牌者' in prompt else priority(q) > 0
        elif '【补益】' in prompt:
            value = priority(request.subject_player_id) < 0
        elif '【眩惑】' in prompt:
            value = any(q != pid and priority(q) < 0 for q in living)
    elif kind is RequestType.CHOOSE_PLAYER:
        if '【甘露】' in prompt:
            if '第一名' in prompt:
                value = max(request.allowed_player_ids, key=lambda a:
                    max((pair_score(a, b) for b in living if b != a
                         and abs(len(equipped_cards(state, a))-len(equipped_cards(state, b))) <= lost), default=-100))
            else:
                # The first selection is exposed through the allowed partner set;
                # choose the largest positive equipment transfer for an ally.
                value = max(request.allowed_player_ids, key=lambda q: pair_score(request.subject_player_id, q))
        elif '受赠者' in prompt or '摸牌角色' in prompt:
            value = min(request.allowed_player_ids, key=lambda q: (priority(q), len(hand(state, q))))
        else:
            value = max(request.allowed_player_ids, key=lambda q: (priority(q), -state.players[q].hp))
    elif kind is RequestType.CHOOSE_CARD:
        if request.subject_player_id not in (None, pid):
            public = set(equipped_cards(state, request.subject_player_id))
            value = next((cid for cid in request.eligible_card_ids if cid in public), request.eligible_card_ids[0])
        elif '拼点' in prompt:
            value = max(request.eligible_card_ids, key=lambda cid: state.cards[cid].rank)
        else:
            value = min(request.eligible_card_ids, key=keep)
    elif kind is RequestType.CHOOSE_CARDS:
        if '剩余牌' in prompt:
            value = tuple(sorted(request.eligible_card_ids, key=keep, reverse=True))
        else:
            value = request.eligible_card_ids
    elif kind is RequestType.CHOOSE_OPTION:
        if '【恩怨】' in prompt:
            value = 'give' if 'give' in request.choices else 'lose_hp'
        elif '【明策】' in prompt:
            value = 'use_slash' if priority(request.subject_player_id) > 0 else 'draw'
        elif '【眩惑】' in prompt:
            value = next((cid for cid in request.choices if cid != 'decline'), 'decline')
    if value is None:
        return None
    request.validate(value)
    return Decision(request.request_id, pid, value)

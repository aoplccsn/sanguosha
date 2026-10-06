"""Small mobile-general heuristics using own cards and public player facts."""
from sanguosha.engine.requests import Decision, RequestType
from sanguosha.model.zones import ZoneRef, ZoneType


def decide(ai,state,request):
    prompt = request.prompt; pid = request.player_id; player = state.players[pid]
    if not prompt.startswith(('榻谟：','定州：','智盟：','英霸：','冯河：','破围：','神著：','定汉：','奇正相生：','慧识：','天翊：','辉逝：','佐幸：')):
        return None
    kind = request.request_type; value = None
    hand = state.cards_in(ZoneRef(ZoneType.HAND,pid))
    if kind is RequestType.YES_NO:
        if prompt.startswith('榻谟：'): value = False
        elif prompt.startswith('智盟：'): value = any(q != pid and state.players[q].is_alive and len(state.cards_in(ZoneRef(ZoneType.HAND,q))) > len(hand) for q in state.seat_order)
        elif '继续判定' in prompt: value = player.max_hp < 8
        else: value = True
    elif kind is RequestType.CHOOSE_OPTION:
        choices = request.choices
        if prompt.startswith('神著：'):
            value = 'draw1_quota' if any(state.cards[c].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash') for c in hand) else 'draw3_stop'
        elif prompt.startswith('破围：'):
            hostile = ai._priority(state,pid,request.subject_player_id) > 0
            value = ('discard_damage' if hostile and 'discard_damage' in choices else 'take_hand' if hostile and 'take_hand' in choices else 'cancel')
        elif '秘密选择' in prompt:
            value = 'qi'
        elif 'response-type' in request.request_id:
            value = 'slash' if any(state.cards[c].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash') for c in hand) else 'dodge' if any(state.cards[c].definition_id == 'basic.dodge' for c in hand) else 'pass'
        elif prompt.startswith('定汉：'):
            value = next((q for q in ('remove:trick.ex_nihilo','add:trick.duel','add:trick.snatch','add:trick.dismantlement') if q in choices),'cancel')
        elif prompt.startswith('佐幸：'):
            value = next((q for q in ('trick.ex_nihilo','trick.god_salvation') if q in choices),choices[0])
        elif prompt.startswith('辉逝：'): value = choices[0]
    elif kind is RequestType.CHOOSE_PLAYER:
        targets = request.allowed_player_ids
        if prompt.startswith(('天翊：','辉逝：','慧识：','冯河：')):
            value = pid if pid in targets else min(targets,key=lambda q: ai._priority(state,pid,q))
        elif prompt.startswith('智盟：'):
            value = max(targets,key=lambda q: len(state.cards_in(ZoneRef(ZoneType.HAND,q))))
        else:
            value = max(targets,key=lambda q: ai._priority(state,pid,q))
    if value is None: return None
    return Decision(request.request_id,pid,value)

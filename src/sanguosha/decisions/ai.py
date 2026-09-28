"""Deterministic legal decisions for basic and military identity matches."""

from sanguosha.content.cards.ids import DODGE_ID, PEACH_ID, SLASH_ID
from sanguosha.engine.phases import END_PLAY_PHASE
from sanguosha.engine.requests import PASS_RESPONSE, Decision, PendingRequest, RequestType
from sanguosha.model.enums import Identity
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType


class AIDecisionProvider:
    def __init__(self, human_id: PlayerId) -> None:
        self.human_id = human_id

    def _priority(self, state: GameState, actor: PlayerId, target: PlayerId) -> int:
        role = state.players[actor].identity
        opponent = state.players[target].identity
        if role is Identity.REBEL:
            return 100 if opponent is Identity.LORD else -100
        if role is Identity.LOYALIST:
            return 100 if opponent is Identity.REBEL else 60 if opponent is Identity.RENEGADE else -100
        if role is Identity.LORD:
            return 100 if opponent is Identity.REBEL else 60 if opponent is Identity.RENEGADE else -100
        # The renegade weakens the leading side, and finishes the lord last.
        living_rebels = sum(p.is_alive and p.identity is Identity.REBEL for p in state.players.values())
        if living_rebels:
            return 100 if opponent is Identity.REBEL else 20 if opponent is Identity.LOYALIST else -50
        return 100 if opponent is Identity.LORD else 20

    def decide(self, state: GameState, request: PendingRequest) -> Decision:
        player_id = request.player_id
        kind = request.request_type
        if kind is RequestType.CHOOSE_OPTION:
            usable = [choice for choice in request.choices if choice.startswith("use:")]
            peach = [choice for choice in usable if state.cards[CardInstanceId(choice[4:])].definition_id == PEACH_ID]
            slash = [choice for choice in usable if state.cards[CardInstanceId(choice[4:])].definition_id == SLASH_ID]
            if state.ruleset_id == 'classic-military':
                slash = [choice for choice in usable if state.cards[CardInstanceId(choice[4:])].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash')]
            enemies = [pid for pid in state.seat_order if pid != player_id and state.players[pid].is_alive and self._priority(state, player_id, pid) > 0]
            if peach and state.players[player_id].hp < state.players[player_id].max_hp:
                value = peach[0]
            elif slash and enemies:
                value = slash[0]
            elif enemies and any(choice.startswith('virtual:wusheng:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:wusheng:'))
            elif enemies and 'skill:jijiang' in request.choices:
                value = 'skill:jijiang'
            elif usable and state.ruleset_id == 'classic-military':
                value = usable[0]
            elif 'skill:zhiheng' in request.choices:
                value = 'skill:zhiheng'
            elif 'skill:qingnang' in request.choices:
                value = 'skill:qingnang'
            elif ('skill:kurou' in request.choices and state.players[player_id].hp > 2
                  and len(state.cards_in(ZoneRef(ZoneType.HAND, player_id))) < 2):
                value = 'skill:kurou'
            elif 'skill:rende' in request.choices and len(state.cards_in(ZoneRef(ZoneType.HAND,player_id))) > 1:
                value = 'skill:rende'
            elif 'virtual:spear' in request.choices:
                value = 'virtual:spear'
            else:
                value = END_PLAY_PHASE if END_PLAY_PHASE in request.choices else request.choices[0]
        elif kind is RequestType.CHOOSE_PLAYER:
            value = (player_id if '青囊' in request.prompt and player_id in request.allowed_player_ids else
                     min(request.allowed_player_ids, key=lambda pid: self._priority(state, player_id, pid))
                     if '仁德' in request.prompt or '青囊' in request.prompt or '遗计' in request.prompt else
                     max(request.allowed_player_ids, key=lambda pid: self._priority(state, player_id, pid)))
        elif kind is RequestType.RESPOND_WITH_CARD:
            if not request.eligible_card_ids:
                value = PASS_RESPONSE
            elif request.required_definition_id == DODGE_ID:
                value = request.eligible_card_ids[0]
            elif request.required_definition_id == PEACH_ID:
                subject = request.subject_player_id
                if subject is not None and (subject == player_id or self._priority(state, player_id, subject) < 0):
                    value = request.eligible_card_ids[0]
                else:
                    value = PASS_RESPONSE
            else:
                value = request.eligible_card_ids[0] if state.ruleset_id == 'classic-military' else PASS_RESPONSE
        elif kind is RequestType.CHOOSE_CARDS:
            # Low value is discarded first: Slash, Dodge, then Peach.
            keep_value = {SLASH_ID: 0, DODGE_ID: 1, PEACH_ID: 2}
            ordered = sorted(request.eligible_card_ids, key=lambda cid: (keep_value.get(state.cards[cid].definition_id, 0), str(cid)))
            value = tuple(ordered[:request.min_count])
        elif kind is RequestType.CHOOSE_CARD:
            value = (next((cid for cid in request.eligible_card_ids
                           if f'better:{cid}' in request.choices), request.eligible_card_ids[0]))
        elif kind is RequestType.CHOOSE_PLAYERS:
            ordered=sorted(request.allowed_player_ids,key=lambda pid:self._priority(state,player_id,pid),reverse=True)
            count=max(1,request.min_count) if state.ruleset_id=='classic-military' else request.min_count
            if state.ruleset_id=='classic-military' and request.max_count>1:
                enemies=[pid for pid in ordered if pid!=player_id and self._priority(state,player_id,pid)>0]
                count=max(count,min(request.max_count,len(enemies)))
            value=tuple(ordered[:min(count,len(ordered),request.max_count)])
        elif kind is RequestType.YES_NO:
            if '【鬼才】' in request.prompt:
                subject = request.subject_player_id
                current_match = 'current:1' in request.choices
                enemy = subject is not None and self._priority(state, player_id, subject) > 0
                value = any(choice.startswith('better:') for choice in request.choices) and (current_match == enemy)
            else:
                value = state.ruleset_id == 'classic-military' and ('苦肉' not in request.prompt or state.players[player_id].hp > 2) and (
                    '是否发动' in request.prompt or '【奸雄】' in request.prompt)
        else:
            raise RuntimeError(f"AI cannot answer request type {kind}")
        return Decision(request.request_id, player_id, value)

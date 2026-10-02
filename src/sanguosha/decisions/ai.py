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
        if kind is RequestType.CHOOSE_OPTION and '英魂：选择' in request.prompt:
            target = request.subject_player_id
            enemy = target is not None and self._priority(state, player_id, target) > 0
            value = 'draw_one_discard_x' if enemy else 'draw_x_discard_one'
            return Decision(request.request_id, player_id, value)
        if kind is RequestType.CHOOSE_OPTION and '乱武：' in request.prompt:
            return Decision(request.request_id, player_id, 'slash')
        if kind is RequestType.CHOOSE_OPTION and '崩坏：' in request.prompt:
            player = state.players[player_id]
            value = ('lose_max_hp' if player.hp <= 2 and player.max_hp > player.hp
                     else 'lose_hp')
            return Decision(request.request_id, player_id, value)
        if kind is RequestType.CHOOSE_OPTION and '烈刃：选择' in request.prompt:
            equipment = [choice for choice in request.choices if choice.startswith('equipment:')]
            value = equipment[0] if equipment else 'random_hand'
            return Decision(request.request_id, player_id, value)
        if kind is RequestType.CHOOSE_OPTION and '蛊惑：声明' in request.prompt:
            hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
            enemies = any(pid != player_id and state.players[pid].is_alive
                          and self._priority(state, player_id, pid) > 0
                          for pid in state.seat_order)
            def declaration_score(definition):
                matching = [state.cards[cid] for cid in hand
                            if state.cards[cid].definition_id == definition]
                suited = any(card.suit.value == 'heart' for card in matching)
                usefulness = (4 if definition == 'trick.ex_nihilo' else
                              3 if definition == 'basic.peach' and state.players[player_id].hp < state.players[player_id].max_hp else
                              2 if definition in ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash') and enemies else 0)
                return (int(suited) * 10 + int(bool(matching)) * 5 + usefulness)
            return Decision(request.request_id, player_id,
                            max(request.choices, key=declaration_score))
        if kind is RequestType.CHOOSE_OPTION:
            usable = [choice for choice in request.choices if choice.startswith("use:")]
            peach = [choice for choice in usable if state.cards[CardInstanceId(choice[4:])].definition_id == PEACH_ID]
            slash = [choice for choice in usable if state.cards[CardInstanceId(choice[4:])].definition_id == SLASH_ID]
            if state.ruleset_id == 'classic-military':
                slash = [choice for choice in usable if state.cards[CardInstanceId(choice[4:])].definition_id in ('basic.slash','basic.fire_slash','basic.thunder_slash')]
            enemies = [pid for pid in state.seat_order if pid != player_id and state.players[pid].is_alive and self._priority(state, player_id, pid) > 0]
            lord = next((pid for pid in state.seat_order
                         if state.players[pid].is_alive and state.players[pid].identity is Identity.LORD), None)
            if peach and state.players[player_id].hp < state.players[player_id].max_hp:
                value = peach[0]
            elif ('skill:luanwu' in request.choices and state.players[player_id].hp > 1
                  and sum(self._priority(state, player_id, pid) > 0 for pid in enemies) >= 2):
                value = 'skill:luanwu'
            elif ('skill:dimeng' in request.choices and any(
                  self._priority(state, player_id, pid) < 0
                  and len(state.cards_in(ZoneRef(ZoneType.HAND, pid))) <= 2
                  for pid in state.seat_order if pid != player_id and state.players[pid].is_alive)
                  and any(len(state.cards_in(ZoneRef(ZoneType.HAND, pid))) >= 3
                          for pid in enemies)):
                value = 'skill:dimeng'
            elif enemies and any(choice.startswith('virtual:duanliang:')
                                 for choice in request.choices):
                value = next(choice for choice in request.choices
                             if choice.startswith('virtual:duanliang:'))
            elif (enemies and slash and any(choice.startswith('virtual:jiuchi:')
                                            for choice in request.choices)):
                value = next(choice for choice in request.choices
                             if choice.startswith('virtual:jiuchi:'))
            elif ('skill:guhuo' in request.choices and enemies and
                  any(state.cards[cid].suit.value == 'heart' and
                      state.cards[cid].definition_id in ('basic.slash', 'basic.fire_slash',
                          'basic.thunder_slash', 'trick.ex_nihilo')
                      for cid in state.cards_in(ZoneRef(ZoneType.HAND, player_id)))):
                value = 'skill:guhuo'
            elif ('skill:huangtian' in request.choices and lord is not None
                  and self._priority(state, player_id, lord) < 0
                  and (state.players[lord].hp <= 2
                       or len(state.cards_in(ZoneRef(ZoneType.HAND, lord))) <= 1)
                  and len(state.cards_in(ZoneRef(ZoneType.HAND, player_id))) >= 2):
                value = 'skill:huangtian'
            elif slash and enemies:
                value = slash[0]
            elif enemies and any(choice.startswith('virtual:wusheng:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:wusheng:'))
            elif enemies and any(choice.startswith('virtual:qixi:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:qixi:'))
            elif enemies and any(choice.startswith('virtual:guose:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:guose:'))
            elif enemies and any(choice.startswith('virtual:longdan:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:longdan:'))
            elif enemies and 'skill:jijiang' in request.choices:
                value = 'skill:jijiang'
            elif usable and state.ruleset_id == 'classic-military':
                value = usable[0]
            elif 'skill:zhiheng' in request.choices:
                value = 'skill:zhiheng'
            elif 'skill:qingnang' in request.choices:
                value = 'skill:qingnang'
            elif 'skill:jieyin' in request.choices:
                value = 'skill:jieyin'
            elif 'skill:fanjian' in request.choices:
                value = 'skill:fanjian'
            elif 'skill:lijian' in request.choices:
                value = 'skill:lijian'
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
            if '好施：' in request.prompt:
                value = min(request.allowed_player_ids,
                            key=lambda pid: self._priority(state, player_id, pid))
            elif '缔盟：选择第一' in request.prompt:
                value = min(request.allowed_player_ids, key=lambda pid: (
                    self._priority(state, player_id, pid),
                    len(state.cards_in(ZoneRef(ZoneType.HAND, pid)))))
            elif '缔盟：选择第二' in request.prompt:
                value = max(request.allowed_player_ids, key=lambda pid: (
                    self._priority(state, player_id, pid),
                    len(state.cards_in(ZoneRef(ZoneType.HAND, pid)))))
            elif '放逐：' in request.prompt:
                missing = state.players[player_id].max_hp - state.players[player_id].hp
                value = min(request.allowed_player_ids, key=lambda pid: (
                    (1 if self._priority(state, player_id, pid) > 0 else -1)
                    * (1 if state.players[pid].face_up else -1)
                    - (missing - 1) * (1 if self._priority(state, player_id, pid) > 0 else -1)))
            elif '天香' in request.prompt:
                enemies = [pid for pid in request.allowed_player_ids
                           if self._priority(state, player_id, pid) > 0]
                value = min(enemies, key=lambda pid: state.players[pid].hp) if enemies else request.allowed_player_ids[0]
            else:
                value = (player_id if '青囊' in request.prompt and player_id in request.allowed_player_ids else
                     min(request.allowed_player_ids, key=lambda pid: self._priority(state, player_id, pid))
                     if '仁德' in request.prompt or '青囊' in request.prompt or '遗计' in request.prompt or '结姻' in request.prompt else
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
            if '拼点：选择' in request.prompt:
                value = max(request.eligible_card_ids,
                            key=lambda cid: (state.cards[cid].rank, str(cid)))
            elif '蛊惑：扣置' in request.prompt:
                declared = next((choice[9:] for choice in request.choices
                                 if choice.startswith('declared:')), '')
                keep = {'basic.peach': 4, 'basic.dodge': 3,
                        'trick.nullification': 3, 'basic.wine': 2}
                value = max(request.eligible_card_ids, key=lambda cid: (
                    int(state.cards[cid].definition_id == declared) * 10 +
                    int(state.cards[cid].suit.value == 'heart') * 3 -
                    keep.get(state.cards[cid].definition_id, 0), str(cid)))
            elif '黄天' in request.prompt:
                lord = next((pid for pid in state.seat_order
                             if state.players[pid].is_alive and state.players[pid].identity is Identity.LORD), None)
                dodges = [cid for cid in request.eligible_card_ids
                          if state.cards[cid].definition_id == DODGE_ID]
                lightning = [cid for cid in request.eligible_card_ids
                             if state.cards[cid].definition_id == 'delayed.lightning']
                value = (dodges[0] if lord is not None and state.players[lord].hp <= 2
                         and state.players[player_id].hp >= 3 and dodges else
                         lightning[0] if lightning else request.eligible_card_ids[0])
            elif '天香' in request.prompt:
                card_value = {SLASH_ID: 0, DODGE_ID: 2, PEACH_ID: 3}
                value = min(request.eligible_card_ids,
                            key=lambda cid: (card_value.get(state.cards[cid].definition_id, 1), str(cid)))
            elif '神速' in request.prompt:
                hand = set(state.cards_in(ZoneRef(ZoneType.HAND, player_id)))
                value = next((cid for cid in request.eligible_card_ids if cid in hand),
                             request.eligible_card_ids[0])
            else:
                value = next((cid for cid in request.eligible_card_ids
                              if f'better:{cid}' in request.choices), request.eligible_card_ids[0])
        elif kind is RequestType.CHOOSE_PLAYERS:
            ordered=sorted(request.allowed_player_ids,key=lambda pid:self._priority(state,player_id,pid),reverse=True)
            count=max(1,request.min_count) if state.ruleset_id=='classic-military' else request.min_count
            if state.ruleset_id=='classic-military' and request.max_count>1:
                enemies=[pid for pid in ordered if pid!=player_id and self._priority(state,player_id,pid)>0]
                count=max(count,min(request.max_count,len(enemies)))
            value=tuple(ordered[:min(count,len(ordered),request.max_count)])
        elif kind is RequestType.YES_NO:
            if '【行殇】' in request.prompt or '【颂威】' in request.prompt:
                value = True
            elif '【暴虐】' in request.prompt:
                subject = request.subject_player_id
                value = (subject is not None and self._priority(state, player_id, subject) < 0
                         and state.players[subject].hp < state.players[subject].max_hp)
            elif '【烈刃】' in request.prompt:
                subject = request.subject_player_id
                hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                value = (subject is not None and self._priority(state, player_id, subject) > 0
                         and any(state.cards[cid].rank >= 10 for cid in hand))
            elif '【再起】' in request.prompt:
                player = state.players[player_id]
                value = player.max_hp - player.hp >= 2
            elif '【英魂】' in request.prompt:
                value = bool(request.allowed_player_ids or any(
                    pid != player_id and state.players[pid].is_alive for pid in state.seat_order))
            elif '蛊惑声明' in request.prompt:
                declared = next((choice[9:] for choice in request.choices
                                 if choice.startswith('declared:')), '')
                dangerous = declared in ('basic.slash', 'basic.fire_slash',
                    'basic.thunder_slash', 'trick.ex_nihilo', 'trick.nullification')
                value = (state.players[player_id].hp >= 3 and dangerous and
                         sum(map(ord, request.request_id + str(player_id))) % 4 == 0)
            elif '雷击判定' in request.prompt and '【鬼道】' in request.prompt:
                subject = request.subject_player_id
                value = (subject is not None and self._priority(state, player_id, subject) > 0
                         and any(choice.startswith('better:') for choice in request.choices))
            elif '【鬼道】' in request.prompt:
                subject = request.subject_player_id
                current_match = 'current:1' in request.choices
                enemy = subject is not None and self._priority(state, player_id, subject) > 0
                value = any(choice.startswith('better:') for choice in request.choices) and (current_match == enemy)
            elif '【天香】' in request.prompt:
                damage = next((int(choice.split(':', 1)[1]) for choice in request.choices
                               if choice.startswith('damage:')), 1)
                enemies = [pid for pid in state.seat_order if pid != player_id
                           and state.players[pid].is_alive
                           and self._priority(state, player_id, pid) > 0]
                player = state.players[player_id]
                value = bool(enemies) and (player.hp <= damage
                    or any(state.players[pid].hp <= damage for pid in enemies)
                    or player.hp < player.max_hp and any(
                        state.players[pid].hp >= state.players[pid].max_hp - 1 for pid in enemies))
            elif '【神速】' in request.prompt:
                hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                enemies = [pid for pid in state.seat_order if pid != player_id
                           and state.players[pid].is_alive
                           and self._priority(state, player_id, pid) > 0]
                finishing_hit = any(state.players[pid].hp <= 1 for pid in enemies)
                value = bool(enemies) and (finishing_hit or
                    (len(hand) >= 4 if 'A' in request.prompt else len(hand) <= 2))
            elif '【据守】' in request.prompt:
                player = state.players[player_id]
                hand_count = len(state.cards_in(ZoneRef(ZoneType.HAND, player_id)))
                value = player.face_up and player.hp >= 2 and hand_count <= 2
            elif '【鬼才】' in request.prompt:
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

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
        known_lord = target in state.revealed_identities and state.players[target].identity is Identity.LORD
        public_hostility = int(state.metadata.get('public_hostility_to_lord', {}).get(target, 0))
        if role is Identity.REBEL:
            return 100 if known_lord else -20
        if role in (Identity.LOYALIST, Identity.LORD):
            return -100 if known_lord else 20 + 20 * min(public_hostility, 3)
        # Hidden roles are unknown to the AI. The renegade conserves the lord
        # until only the two of them remain, using only public seat information.
        living = sum(player.is_alive for player in state.players.values())
        if known_lord:
            return 100 if living == 2 else -20
        return 20 + 10 * min(public_hostility, 3)

    def _target_score(self, state: GameState, actor: PlayerId, target: PlayerId, *, damage: int = 1) -> int:
        """Shared relation/threat/kill heuristic for legal target choices."""
        if target == actor or not state.players[target].is_alive:
            return -10_000
        player = state.players[target]
        hand = len(state.cards_in(ZoneRef(ZoneType.HAND, target)))
        score = self._priority(state, actor, target) * 4 + (player.max_hp - player.hp) * 3 + hand
        if player.hp <= damage:
            score += 30
        if player.hp == 1:
            score += 12
        if not player.face_up:
            score -= 4
        return score

    def _card_value(self, state: GameState, player_id: PlayerId, definition_id: str) -> int:
        player = state.players[player_id]
        if definition_id == PEACH_ID:
            return 28 if player.hp <= 1 else 3
        if definition_id == DODGE_ID:
            return 22 if player.hp <= 1 else 10
        if definition_id in (SLASH_ID, 'basic.fire_slash', 'basic.thunder_slash'):
            return 14 if player.hp <= 1 else 20
        if definition_id == 'trick.nullification':
            return 20 if player.hp <= 1 else 12
        if definition_id.startswith('equipment.'):
            return 8
        return 6

    def _choice_card_value(self, state: GameState, player_id: PlayerId, card_id: str) -> int:
        card = state.cards.get(card_id)
        return self._card_value(state, player_id, card.definition_id) if card is not None else 5

    def decide(self, state: GameState, request: PendingRequest) -> Decision:
        player_id = request.player_id
        from .yj2011_tier3 import decide as decide_tier3
        tier3 = decide_tier3(self, state, request)
        if tier3 is not None:
            return tier3
        from .yj2011 import decide_yj2011
        yj2011_decision = decide_yj2011(self, state, request, player_id)
        if yj2011_decision is not None:
            return yj2011_decision
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
        if kind is RequestType.CHOOSE_OPTION and '化身：选择' in request.prompt:
            preferred = ('yingzi', 'paoxiao', 'guanxing', 'jizhi', 'qicai',
                         'longdan', 'mashu', 'qixi', 'yinghun')
            value = max(request.choices, key=lambda choice: (
                0 if choice == 'keep' else
                len(preferred) - preferred.index(choice.rsplit(':', 1)[-1])
                if choice.rsplit(':', 1)[-1] in preferred else 1))
            return Decision(request.request_id, player_id, value)
        if kind is RequestType.CHOOSE_OPTION and '志继：' in request.prompt:
            value = ('recover' if 'recover' in request.choices
                     and state.players[player_id].hp <= 1 else 'draw')
            return Decision(request.request_id, player_id, value)
        if kind is RequestType.CHOOSE_OPTION and '享乐：' in request.prompt:
            subject = request.subject_player_id
            value = next((choice for choice in request.choices if choice != 'decline'), 'decline')
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
                from sanguosha.engine.skills import SkillRegistry
                from sanguosha.engine.yj2011_tier3 import canonical_definition
                skill_registry=SkillRegistry()
                slash = [choice for choice in usable if canonical_definition(state, skill_registry, player_id, state.cards[CardInstanceId(choice[4:])].definition_id) in ('basic.slash','basic.fire_slash','basic.thunder_slash')]
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
                value = max(slash, key=lambda choice: (
                    self._choice_card_value(state, player_id, choice[4:]), str(choice)))
            elif enemies and any(choice.startswith('virtual:wusheng:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:wusheng:'))
            elif enemies and any(choice.startswith('virtual:qixi:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:qixi:'))
            elif enemies and any(choice.startswith('virtual:jixi:') for choice in request.choices):
                value = next(choice for choice in request.choices if choice.startswith('virtual:jixi:'))
            elif enemies and 'skill:tiaoxin' in request.choices:
                value = 'skill:tiaoxin'
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
            elif 'skill:zhijian' in request.choices:
                value = 'skill:zhijian'
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
            if '放权：选择获得额外回合' in request.prompt or '直谏：选择装备' in request.prompt:
                value = min(request.allowed_player_ids,
                            key=lambda pid: self._priority(state, player_id, pid))
            elif '巧变' in request.prompt and '摸牌' in request.prompt:
                value = max(request.allowed_player_ids,
                            key=lambda pid: self._priority(state, player_id, pid))
            elif '好施：' in request.prompt:
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
                     max(request.allowed_player_ids, key=lambda pid: self._target_score(state, player_id, pid)))
        elif kind is RequestType.RESPOND_WITH_CARD:
            if not request.eligible_card_ids:
                value = PASS_RESPONSE
            elif request.required_definition_id == DODGE_ID:
                value = max(request.eligible_card_ids, key=lambda cid: (
                    self._choice_card_value(state, player_id, cid), str(cid)))
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
            ordered = sorted(request.eligible_card_ids, key=lambda cid: (
                100 if (state.cards.get(cid) is not None and state.cards[cid].definition_id == PEACH_ID)
                else self._choice_card_value(state, player_id, cid), str(cid)))
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
            if '【巧变】' in request.prompt:
                hand_count = len(state.cards_in(ZoneRef(ZoneType.HAND, player_id)))
                value = hand_count > (3 if '出牌' in request.prompt else 1)
            elif '【放权】跳过' in request.prompt:
                value = len(state.cards_in(ZoneRef(ZoneType.HAND, player_id))) <= 1
            elif '【悲歌】' in request.prompt:
                subject = request.subject_player_id
                value = subject is not None and self._priority(state, player_id, subject) < 0
            elif '【行殇】' in request.prompt or '【颂威】' in request.prompt:
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

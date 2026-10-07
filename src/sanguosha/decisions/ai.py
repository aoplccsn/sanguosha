"""Deterministic legal decisions for basic and military identity matches."""

from sanguosha.content.cards.ids import DODGE_ID, PEACH_ID, SLASH_ID
from sanguosha.engine.phases import END_PLAY_PHASE
from sanguosha.engine.requests import PASS_RESPONSE, Decision, PendingRequest, RequestType
from sanguosha.model.enums import Identity
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType
from . import strategy


class AIDecisionProvider:
    def __init__(self, human_id: PlayerId) -> None:
        self.human_id = human_id

    def thinking_profile(self, state: GameState, request: PendingRequest) -> tuple[str, int]:
        """Only own legal candidates and public target facts affect pacing."""
        candidates = len(request.choices) + len(request.eligible_card_ids) + len(request.allowed_player_ids)
        skill = any(choice.startswith(('skill:', 'virtual:')) for choice in request.choices)
        multi = request.max_count > 1 and bool(request.allowed_player_ids)
        kill = any(state.players[pid].hp <= 1 and self._priority(state, request.player_id, pid) > 0
                   for pid in request.allowed_player_ids)
        skill = skill or any(cid.startswith('virtual:') for cid in request.eligible_card_ids)
        if request.request_type is RequestType.YES_NO and candidates <= 1:
            return 'simple', 1800
        if multi or skill or candidates > 8 or kill:
            return 'complex', min(3000, 2600 + min(candidates, 16) * 20 + int(multi) * 100 + int(kill) * 100)
        if request.request_type is RequestType.RESPOND_WITH_CARD and candidates <= 3:
            return 'simple', 1800 + candidates * 100
        return 'ordinary', 2200 + min(candidates, 8) * 80

    def observe_public_events(self, state, events):
        """Small public attitude ledger; persisted with the match, no hidden cards."""
        from sanguosha.engine.events import CardUsedEvent, DamageDealtEvent, HpRecoveredEvent, CardRespondedEvent, VirtualResponseEvent, Event
        ledger = state.metadata.setdefault('public_attitude', {})
        start = state.metadata.get('public_attitude_event_count', 0)
        effects=state.metadata.setdefault('public_counter_effects',{})
        for event in events[start:]:
            source, targets, change = None, (), 0
            if isinstance(event, (DamageDealtEvent, HpRecoveredEvent)):
                source, targets = event.source_id, (event.target_id,)
                change = event.amount * (2 if isinstance(event, HpRecoveredEvent) else -2)
            elif isinstance(event, CardUsedEvent):
                definition = event.virtual_definition_id or state.cards[event.card_id].definition_id
                if definition in ('trick.dismantlement', 'trick.snatch', 'trick.duel',
                                  'basic.slash', 'basic.fire_slash', 'basic.thunder_slash'):
                    source, targets, change = event.player_id, event.target_ids, -1
            if isinstance(event,Event) and event.event_type=='effect_target':
                effects[event.event_id.replace(':current:',':window:')]={'targets':list(event.target_ids),'definition':event.metadata.get('definition_id',''),'count':0}
            elif isinstance(event,(CardRespondedEvent,VirtualResponseEvent)) and event.response_definition_id=='trick.nullification':
                effect=effects.get(event.source_action_id)
                if effect:
                    beneficial=effect['definition'] in ('trick.ex_nihilo','trick.god_salvation','trick.amazing_grace')
                    source,targets=event.player_id,effect['targets']
                    change=(-1 if beneficial else 1)*(1 if effect['count']%2==0 else -1)
                    effect['count']+=1
            elif isinstance(event,Event) and event.source_id and event.target_ids:
                sid=event.metadata.get('skill_id') or event.event_type.removeprefix('skill_')
                tags=strategy.skill_tags(sid)
                if event.event_type.startswith(('skill_','presentation_skill')):
                    source,targets=event.source_id,event.target_ids
                    change=-1 if tags & {'damage','discard','control'} else 1 if tags & {'give','heal','save','protect'} else 0
            if source:
                relation = ledger.setdefault(str(source), {})
                for target in targets:
                    if target != source:
                        relation[str(target)] = max(-6, min(6, relation.get(str(target), 0) + change))
        state.metadata['public_attitude_event_count'] = len(events)

    def relation(self, state: GameState, actor: PlayerId, target: PlayerId) -> str:
        if actor == target:
            return 'SELF'
        from sanguosha.game_modes import game_mode
        mode = game_mode(state.metadata.get('mode_id', 'military-five'))
        if mode.public_sides:
            return 'ALLY' if mode.team_for(actor) == mode.team_for(target) else 'ENEMY'
        return 'ENEMY' if self._priority(state, actor, target) > 0 else 'ALLY'

    def _priority(self, state: GameState, actor: PlayerId, target: PlayerId) -> int:
        from sanguosha.game_modes import game_mode
        mode = game_mode(state.metadata.get('mode_id', 'military-five'))
        if mode.public_sides:
            return -100 if actor == target or mode.team_for(actor) == mode.team_for(target) else 100
        role = state.players[actor].identity
        known_lord = target in state.revealed_identities and state.players[target].identity is Identity.LORD
        public_hostility = int(state.metadata.get('public_hostility_to_lord', {}).get(target, 0))
        ledger = state.metadata.get('public_attitude', {})
        lord = next((pid for pid in state.revealed_identities if state.players[pid].identity is Identity.LORD), None)
        to_lord = strategy.belief(state,target)
        to_self = ledger.get(str(target), {}).get(str(actor), 0)
        if target in state.revealed_identities and not known_lord:
            revealed = state.players[target].identity
            if role is Identity.REBEL:
                return -100 if revealed is Identity.REBEL else 80
            if role in (Identity.LOYALIST, Identity.LORD):
                return -100 if revealed is Identity.LOYALIST else 80
        if role is Identity.REBEL:
            return 100 if known_lord else -20 + 15 * to_lord - 5 * to_self
        if role in (Identity.LOYALIST, Identity.LORD):
            return -100 if known_lord else 20 + 20 * min(public_hostility, 3) - 15 * to_lord - 5 * to_self
        living = [q for q in state.seat_order if state.players[q].is_alive]
        if known_lord:
            if len(living)==2: return 100
            return -80 if state.players[target].hp<=2 else -10
        court = sum(strategy.strength(state,q) for q in living if q==lord or strategy.belief(state,q)>=2)
        rebels = sum(strategy.strength(state,q) for q in living if q!=lord and strategy.belief(state,q)<=-2)
        balance = max(-40,min(40,(court-rebels)*1.5))
        lean = 1 if to_lord>=2 else -1 if to_lord<=-2 else 0
        return round(20+lean*balance-5*to_self)

    def _target_score(self, state: GameState, actor: PlayerId, target: PlayerId, *, damage: int = 1, elemental: bool = False) -> int:
        if target == actor or not state.players[target].is_alive:
            return -10_000
        from sanguosha.engine.distance import DistanceSystem
        terms = strategy.damage_terms(self,state,actor,target,damage,elemental)
        terms['distance']=-max(0,DistanceSystem().distance_between(state,actor,target)-1)*2
        return round(sum(terms.values()))

    def _support_score(self,state,actor,target):
        return strategy.support_score(self,state,actor,target)

    def _card_value(self, state: GameState, player_id: PlayerId, definition_id: str) -> int:
        player = state.players[player_id]
        if definition_id == PEACH_ID:
            return 32 if player.hp <= 2 else 18
        if definition_id == DODGE_ID:
            return 26 if player.hp <= 2 else 10
        if definition_id in (SLASH_ID, 'basic.fire_slash', 'basic.thunder_slash'):
            return 14 if player.hp <= 1 else 20
        if definition_id == 'basic.wine':
            return 28 if player.hp<=1 else 11
        if definition_id == 'trick.nullification':
            return 20 if player.hp <= 1 else 12
        if definition_id.startswith('equipment.'):
            slot,quality=self._equipment_quality(state,player_id,definition_id)
            existing=state.cards_in(ZoneRef(ZoneType.EQUIPMENT,player_id,slot))
            return 3 if existing and self._equipment_quality(state,player_id,state.cards[existing[0]].definition_id)[1]>=quality else quality
        return 6

    def _choice_card_value(self, state: GameState, player_id: PlayerId, card_id: str) -> int:
        card = state.cards.get(card_id)
        if card is None: return 5
        value=self._card_value(state,player_id,card.definition_id)
        tags=strategy.profile(state,player_id); skills=strategy.active_skills(state,player_id)
        if card.suit.value in ('heart','diamond') and skills & {'wusheng','jijiu','huoji'}: value+=9
        if card.suit.value in ('spade','club') and skills & {'qingguo','kanpo','qixi'}: value+=7
        if card.definition_id.startswith('equipment.') and 'equip' in tags: value+=8
        if 'slash' in card.definition_id and 'burst' in tags: value+=9
        if card.definition_id.startswith('trick.') and 'jizhi' in skills: value+=8
        return value

    def _equipment_quality(self, state, actor, definition, *, observer=None):
        from sanguosha.content.cards.classic_military import WEAPONS, HORSES
        from sanguosha.engine.distance import DistanceSystem
        from sanguosha.model.enums import EquipmentSlot
        if '.weapon.' in definition:
            reach = dict((f'equipment.weapon.{key}', radius) for key, _, radius in WEAPONS).get(definition, 1)
            enemies = [pid for pid in state.seat_order if pid != actor and state.players[pid].is_alive and self._priority(state, observer or actor, pid) > 0]
            accessible = sum(DistanceSystem().distance_between(state, actor, pid) <= reach for pid in enemies)
            # Hand count is public even when valuing an opponent's equipment.
            slashes = strategy.hand_count(state,actor)
            return EquipmentSlot.WEAPON, 8 + accessible * 6 + reach + (15 if definition.endswith('crossbow') and slashes >= 2 else 0)
        if '.armor.' in definition:
            quality = {'eight_trigrams': 22, 'renwang_shield': 20, 'silver_lion': 19, 'vine': 14}.get(definition.rsplit('.', 1)[-1], 10)
            return EquipmentSlot.ARMOR, quality + (6 if state.players[actor].hp <= 2 and definition.endswith('silver_lion') else 0)
        slot = next((slot for key, _, slot in HORSES if definition == f'equipment.horse.{key}'), EquipmentSlot.DEFENSIVE_HORSE)
        return slot, 15

    def _action_priority(self, state, actor, definition, enemies):
        player = state.players[actor]
        if definition == PEACH_ID:
            return 130 if player.hp < player.max_hp else -100
        if definition == 'trick.ex_nihilo':
            return 105
        if definition.startswith('equipment.'):
            slot, quality = self._equipment_quality(state, actor, definition)
            existing = state.cards_in(ZoneRef(ZoneType.EQUIPMENT, actor, slot))
            if existing:
                old = state.cards[existing[0]].definition_id
                if quality <= self._equipment_quality(state, actor, old)[1]:
                    return -100
            return 95 if '.armor.' in definition and player.hp <= 2 else 82
        if definition in ('trick.dismantlement', 'trick.snatch'):
            defended = any(ref.player_id in enemies and ref.zone_type is ZoneType.EQUIPMENT and zone.card_ids
                           for ref, zone in state.zones.items())
            return 98 if defended else 65
        if definition == 'basic.wine':
            own_slash = any('slash' in state.cards[cid].definition_id for cid in state.cards_in(ZoneRef(ZoneType.HAND, actor)))
            return 92 if enemies and own_slash else -100
        if 'slash' in definition:
            best=max((self._target_score(state,actor,pid,damage=1+player.marks.get('wine',0),elemental=definition!='basic.slash') for pid in enemies),default=-100)
            return 115+best*.15 if best>=90 else 60+best*.25 if best>0 else -100
        if definition in ('trick.savage_assault', 'trick.archery_attack'):
            from sanguosha.engine.military_basics import equipped
            from sanguosha.model.enums import EquipmentSlot
            from sanguosha.engine.skills import SkillRegistry
            from sanguosha.engine.forest import savage_effect_immune
            net = 0
            for pid in state.seat_order:
                if pid == actor or not state.players[pid].is_alive:
                    continue
                if equipped(state, pid, EquipmentSlot.ARMOR) == 'equipment.armor.vine':
                    continue
                if definition == 'trick.savage_assault' and savage_effect_immune(state, pid, SkillRegistry()):
                    continue
                relation = 1 if self._priority(state, actor, pid) > 0 else -1
                danger = 3 if state.players[pid].hp <= 1 else 2 if state.players[pid].hp <= 2 else 1
                # Opponent hand count is public; card definitions are never inspected.
                chance = max(.35, 1 - len(state.cards_in(ZoneRef(ZoneType.HAND, pid))) * .1)
                loss=1.0
                if 'masochism' in strategy.profile(state,pid) and state.players[pid].hp>1: loss=.25
                if pid==strategy.lord_id(state) and self._priority(state,actor,pid)<0 and state.players[pid].hp<=1: danger=8
                net += relation * danger * chance * loss
            reveal=strategy.exposure_cost(self,state,actor,strategy.lord_id(state)) if strategy.lord_id(state) else 0
            return 60+round(net*8) if net>0 and net*25>reveal else -100
        if definition == 'trick.fire_attack':
            suits={state.cards[c].suit for c in state.cards_in(ZoneRef(ZoneType.HAND,actor)) if state.cards[c].definition_id!='trick.fire_attack' and self._choice_card_value(state,actor,c)<26}
            return 55+len(suits)*5 if enemies and suits else -100
        if definition == 'trick.iron_chain':
            elemental=any(state.cards[c].definition_id in ('basic.fire_slash','basic.thunder_slash','trick.fire_attack') for c in state.cards_in(ZoneRef(ZoneType.HAND,actor)))
            linked_friends=any(state.players[q].chained and self._priority(state,actor,q)<0 for q in state.seat_order if q!=actor and state.players[q].is_alive)
            return 80 if linked_friends else 68 if elemental and enemies else 15
        if definition == 'trick.god_salvation':
            net=sum((1 if q==actor or self._priority(state,actor,q)<0 else -1)*(state.players[q].max_hp-state.players[q].hp) for q in state.seat_order if state.players[q].is_alive)
            return 80+net*5 if net>0 else -100
        if definition.startswith(('trick.', 'delayed.')):
            return 60
        return 0

    def decide(self, state: GameState, request: PendingRequest, *, response_context=None) -> Decision:
        decision=self._decide(state,request,response_context=response_context)
        import os
        if os.environ.get('AI_DECISION_DEBUG')=='1':
            import json, logging
            targets={str(q):strategy.damage_terms(self,state,request.player_id,q) for q in request.allowed_player_ids if q!=request.player_id}
            logging.getLogger('sanguosha.ai').warning('AI_DECISION %s',json.dumps({'actor':str(request.player_id),'prompt':request.prompt,'target_scores':targets,'choice':str(decision.value)},ensure_ascii=False))
        return decision

    def _decide(self, state: GameState, request: PendingRequest, *, response_context=None) -> Decision:
        player_id = request.player_id
        if request.prompt == '神将：选择本局势力':
            return Decision(request.request_id,player_id,'wu' if state.players[player_id].character_id == 'mountain_god_simayi' else 'wei')
        from .mobile_gods import decide as mobile_decide
        mobile_choice = mobile_decide(self,state,request)
        if mobile_choice is not None: return mobile_choice
        if request.request_type is RequestType.CHOOSE_OPTION and request.prompt.startswith(('极略：', '连破：')):
            choice=max(request.choices,key=lambda q:strategy.learning_score(self,state,player_id,q))
            return Decision(request.request_id, player_id, choice)
        if request.required_definition_id == 'trick.nullification' and response_context:
            target = response_context.get('current_target_id') or request.subject_player_id
            definition = response_context.get('definition_id', '')
            if target in state.players:
                allied = target == player_id or self._priority(state, player_id, target) < 0
                beneficial = definition in ('trick.ex_nihilo', 'trick.god_salvation', 'trick.amazing_grace')
                want_cancel = allied != beneficial
                cancelled = bool(response_context.get('cancelled'))
                value = (10 if state.players[target].hp <= 2 and not beneficial else
                         8 if definition == 'trick.ex_nihilo' else
                         7 if definition in ('trick.dismantlement', 'trick.snatch') else 6)
                own_counters = sum(state.cards[cid].definition_id == 'trick.nullification'
                                   for cid in state.cards_in(ZoneRef(ZoneType.HAND, player_id)))
                threshold = 7 if own_counters <= 1 else 5
                if target!=player_id and self._priority(state,player_id,target)>0 and not beneficial:
                    value=0 if not cancelled else value
                if state.players[player_id].identity is Identity.REBEL and target==strategy.lord_id(state) and not beneficial:
                    # A cheap public show of support only while there is no killing window.
                    own=state.players[player_id]
                    disguise=state.turn_number<=len(state.seat_order)*2 and strategy.belief(state,player_id)>-2 and own.hp>=3 and own_counters>=2 and state.players[target].hp>=3 and value<=7
                    want_cancel=disguise
                if want_cancel == cancelled or value < threshold:
                    return Decision(request.request_id, player_id, PASS_RESPONSE)
        if request.request_type is RequestType.YES_NO and '【精策】' in request.prompt:
            return Decision(request.request_id, player_id, True)
        if '【称象】' in request.prompt:
            if request.request_type is RequestType.YES_NO:
                return Decision(request.request_id,player_id,True)
            if request.request_type is RequestType.CHOOSE_OPTION:
                return Decision(request.request_id,player_id,'continue')
            if request.request_type is RequestType.CHOOSE_CARD:
                value=max(request.eligible_card_ids,key=lambda c:
                    {'basic.peach':9,'basic.dodge':6,'trick.nullification':7}.get(state.cards[c].definition_id,4)/state.cards[c].rank)
                return Decision(request.request_id,player_id,value)
        if '【仁心】' in request.prompt:
            if request.request_type is RequestType.YES_NO:
                target=request.subject_player_id
                value=target in state.players and self._priority(state,player_id,target)<0
                return Decision(request.request_id,player_id,value)
            if request.request_type is RequestType.CHOOSE_CARD:
                return Decision(request.request_id,player_id,request.eligible_card_ids[0])
        if '【绝策】' in request.prompt:
            if request.request_type is RequestType.YES_NO:
                from sanguosha.engine.yj2011_tier3 import hand
                value=any(q!=player_id and state.players[q].is_alive and not hand(state,q)
                    and self._priority(state,player_id,q)>0 for q in state.seat_order)
                return Decision(request.request_id,player_id,value)
            if request.request_type is RequestType.CHOOSE_PLAYER:
                value=max(request.allowed_player_ids,key=lambda q:self._priority(state,player_id,q))
                return Decision(request.request_id,player_id,value)
        if '【夺刀】' in request.prompt:
            if request.request_type is RequestType.YES_NO:
                from sanguosha.model.enums import EquipmentSlot
                source=request.subject_player_id
                value=source in state.players and bool(state.cards_in(ZoneRef(ZoneType.EQUIPMENT,source,EquipmentSlot.WEAPON)))
                return Decision(request.request_id, player_id, value)
            if request.request_type is RequestType.CHOOSE_CARD:
                value=min(request.eligible_card_ids,key=lambda c:
                    {'basic.peach':9,'basic.dodge':6,'trick.nullification':7}.get(state.cards[c].definition_id,2))
                return Decision(request.request_id,player_id,value)
        from .remaining_gods import decide as decide_remaining_gods
        god_decision=decide_remaining_gods(self,state,request)
        if god_decision is not None:return god_decision
        from .yj2013 import decide as decide_yj2013
        yj2013_decision=decide_yj2013(self,state,request)
        if yj2013_decision is not None:
            return yj2013_decision
        from .yj2012 import decide as decide_yj2012
        yj2012_decision = decide_yj2012(self, state, request)
        if yj2012_decision is not None:
            return yj2012_decision
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
                slash = [choice for choice in usable if canonical_definition(state, skill_registry, player_id, state.cards[CardInstanceId(choice[4:])].definition_id,CardInstanceId(choice[4:])) in ('basic.slash','basic.fire_slash','basic.thunder_slash')]
            enemies = [pid for pid in state.seat_order if pid != player_id and state.players[pid].is_alive and self._priority(state, player_id, pid) > 0]
            lord = next((pid for pid in state.seat_order
                         if pid in state.revealed_identities and state.players[pid].is_alive and state.players[pid].identity is Identity.LORD), None)
            lethal=[c for c in slash if any(state.players[q].hp<=1 and self._priority(state,player_id,q)>0 for q in request.play_card_targets.get(c,(tuple(enemies),0,0))[0])]
            if lethal and (state.players[player_id].hp>=2 or any(q==lord and state.players[player_id].identity is Identity.REBEL for c in lethal for q in request.play_card_targets.get(c,(tuple(enemies),0,0))[0])):
                value=lethal[0]
            elif peach and state.players[player_id].hp < state.players[player_id].max_hp:
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
            elif usable and any(self._action_priority(state, player_id, state.cards[CardInstanceId(choice[4:])].definition_id, [q for q in request.play_card_targets.get(choice,(tuple(enemies),0,0))[0] if q in enemies]) > 72 for choice in usable):
                value = max(usable, key=lambda choice: self._action_priority(state, player_id, state.cards[CardInstanceId(choice[4:])].definition_id, [q for q in request.play_card_targets.get(choice,(tuple(enemies),0,0))[0] if q in enemies]))
            elif slash and enemies and any(self._action_priority(state,player_id,state.cards[c[4:]].definition_id,enemies)>0 for c in slash):
                value = max(slash, key=lambda choice: (
                    self._choice_card_value(state, player_id, choice[4:]), str(choice)))
            elif enemies and any(self._target_score(state,player_id,q)>0 for q in enemies) and any(choice.startswith('virtual:wusheng:') for choice in request.choices):
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
            elif 'skill:huishi' in request.choices and state.players[player_id].max_hp < 8:
                value = 'skill:huishi'
            elif 'skill:zuoxing' in request.choices:
                value = 'skill:zuoxing'
            elif enemies and 'skill:dingzhou' in request.choices:
                value = 'skill:dingzhou'
            elif enemies and 'skill:yingba' in request.choices and state.players[player_id].max_hp > 2:
                value = 'skill:yingba'
            elif 'skill:huishi_guojia' in request.choices and state.players[player_id].max_hp > 3:
                value = 'skill:huishi_guojia'
            elif usable and state.ruleset_id == 'classic-military':
                worthwhile = [choice for choice in usable if self._action_priority(state, player_id, state.cards[CardInstanceId(choice[4:])].definition_id, [q for q in request.play_card_targets.get(choice,(tuple(enemies),0,0))[0] if q in enemies]) > 0]
                value = max(worthwhile, key=lambda choice: self._action_priority(state, player_id, state.cards[CardInstanceId(choice[4:])].definition_id, [q for q in request.play_card_targets.get(choice,(tuple(enemies),0,0))[0] if q in enemies])) if worthwhile else END_PLAY_PHASE
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
                            key=lambda pid: -self._support_score(state,player_id,pid))
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
            elif '火攻' in request.prompt:
                value=max(request.allowed_player_ids,key=lambda pid:self._target_score(state,player_id,pid)-len(state.cards_in(ZoneRef(ZoneType.HAND,pid))))
            elif '过河拆桥' in request.prompt or '顺手牵羊' in request.prompt:
                def resource_score(pid):
                    visible=[state.cards[c].definition_id for ref,z in state.zones.items() if ref.player_id==pid and ref.zone_type is ZoneType.EQUIPMENT for c in z.card_ids]
                    return self._priority(state,player_id,pid)*4+sum(self._equipment_quality(state,pid,d,observer=player_id)[1] for d in visible)+len(state.cards_in(ZoneRef(ZoneType.HAND,pid)))
                value=max(request.allowed_player_ids,key=resource_score)
            elif '天香' in request.prompt:
                enemies = [pid for pid in request.allowed_player_ids
                           if self._priority(state, player_id, pid) > 0]
                value = min(enemies, key=lambda pid: state.players[pid].hp) if enemies else request.allowed_player_ids[0]
            else:
                value = (player_id if '青囊' in request.prompt and player_id in request.allowed_player_ids else
                     min(request.allowed_player_ids, key=lambda pid: -self._support_score(state,player_id,pid))
                     if '仁德' in request.prompt or '青囊' in request.prompt or '遗计' in request.prompt or '结姻' in request.prompt else
                     max(request.allowed_player_ids, key=lambda pid: self._target_score(state, player_id, pid)))
        elif kind is RequestType.RESPOND_WITH_CARD:
            if not request.eligible_card_ids:
                value = PASS_RESPONSE
            elif request.required_definition_id == DODGE_ID:
                from sanguosha.engine.skills import SkillRegistry
                benefits = 'masochism' in strategy.profile(state,player_id)
                hand = state.cards_in(ZoneRef(ZoneType.HAND, player_id))
                scarce = sum(state.cards[cid].definition_id == DODGE_ID for cid in hand) == 1
                player=state.players[player_id]
                # Mobile 忍戒 grants a mark only after declining a response; survive first.
                growing='renjie' in strategy.active_skills(state,player_id) and not player.marks.get('awakened_baiyin') and player.marks.get('ren',0)==3 and player.marks.get('renjie_round_count',0)<4
                amount=(response_context or {}).get('damage',1)
                safe=player.hp>amount+1 and not player.chained and not any(strategy.threat(state,q)>55 and self._priority(state,player_id,q)>0 for q in state.seat_order if q!=player_id and state.players[q].is_alive)
                if request.allow_pass and safe and scarce and (benefits or growing):
                    return Decision(request.request_id, player_id, PASS_RESPONSE)
                value = max(request.eligible_card_ids, key=lambda cid: (
                    self._choice_card_value(state, player_id, cid), str(cid)))
            elif '火攻' in request.prompt:
                cheapest=min(request.eligible_card_ids,key=lambda cid:self._choice_card_value(state,player_id,cid))
                value=cheapest if self._choice_card_value(state,player_id,cheapest)<26 else PASS_RESPONSE
            elif request.required_definition_id == PEACH_ID:
                subject = request.subject_player_id
                if subject is not None and (subject == player_id or self._priority(state, player_id, subject) < 0):
                    value = request.eligible_card_ids[0]
                else:
                    lord=strategy.lord_id(state); own=state.players[player_id]
                    count=sum(state.cards[c].definition_id==PEACH_ID for c in state.cards_in(ZoneRef(ZoneType.HAND,player_id)))
                    conceal=(own.identity is Identity.REBEL and subject==lord and state.turn_number<=len(state.seat_order)*2 and strategy.belief(state,player_id)>-2 and count>=2 and own.hp>=3 and state.players[subject].hp==0 and not any('slash' in state.cards[c].definition_id for c in state.cards_in(ZoneRef(ZoneType.HAND,player_id))))
                    value=request.eligible_card_ids[0] if conceal else PASS_RESPONSE
            else:
                value = request.eligible_card_ids[0] if state.ruleset_id == 'classic-military' else PASS_RESPONSE
        elif kind is RequestType.CHOOSE_CARDS:
            # Low value is discarded first: Slash, Dodge, then Peach.
            ordered = sorted(request.eligible_card_ids, key=lambda cid: (
                100 if (state.cards.get(cid) is not None and state.cards[cid].definition_id == PEACH_ID)
                else self._choice_card_value(state, player_id, cid), str(cid)))
            value = (min(request.legal_card_sets, key=lambda cards: sum(ordered.index(cid) for cid in cards))
                     if request.legal_card_sets else tuple(ordered[:request.min_count]))
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
            elif request.subject_player_id and request.subject_player_id!=player_id and '目标区域' in request.prompt:
                target=request.subject_player_id
                public={cid:ref for ref,z in state.zones.items() if ref.player_id==target and ref.zone_type in (ZoneType.EQUIPMENT,ZoneType.JUDGMENT) for cid in z.card_ids}
                friendly=self._priority(state,player_id,target)<0
                def removal_value(cid):
                    if cid not in public:return 5 if not friendly else -20
                    ref=public[cid];definition=state.cards[cid].definition_id
                    if ref.zone_type is ZoneType.JUDGMENT:return 45 if friendly and definition!='delayed.lightning' else -30 if friendly else -15
                    quality=self._equipment_quality(state,target,definition,observer=player_id)[1]
                    return -quality if friendly else quality
                value=max(request.eligible_card_ids,key=removal_value)
            elif '火攻' in request.prompt:
                value=min(request.eligible_card_ids,key=lambda cid:self._choice_card_value(state,player_id,cid))
            elif '黄天' in request.prompt:
                lord = next((pid for pid in state.seat_order
                             if pid in state.revealed_identities and state.players[pid].is_alive and state.players[pid].identity is Identity.LORD), None)
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
            def target_score(pid):
                if '铁索连环' in request.prompt:
                    friendly=pid==player_id or self._priority(state,player_id,pid)<0
                    return 100 if friendly and state.players[pid].chained else 50 if not friendly and not state.players[pid].chained else -100
                return self._target_score(state,player_id,pid)
            ordered=sorted(request.allowed_player_ids,key=target_score,reverse=True)
            count=max(1,request.min_count) if state.ruleset_id=='classic-military' else request.min_count
            if state.ruleset_id=='classic-military' and request.max_count>1:
                enemies=[pid for pid in ordered if (target_score(pid)>0 if '铁索连环' in request.prompt else pid!=player_id and self._priority(state,player_id,pid)>0)]
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

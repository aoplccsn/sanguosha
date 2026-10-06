"""Trick cursors, counter windows and delayed judgments on ResolutionStack."""
from dataclasses import dataclass
from sanguosha.model.enums import Phase, EquipmentSlot, Suit, DamageNature
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.state import GameStatus
from .actions import Action, StepResult
from .requests import PendingRequest, RequestType, PASS_RESPONSE
from .response import RespondWithCardAction
from .card_effects import SlashEffectAction
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .events import TrickTargetsDeclaredEvent, Event
from .deck import DrawCardsAction
from .recovery import RecoverAction
from .judgment import JudgmentAction, JudgmentPattern
from .military_basics import MilitaryDamageAction, MilitaryStrike, equipped
from sanguosha.model.virtual_card import VirtualCard

def personal_cards(state, pid):
    return tuple(cid for ref, zone in state.zones.items() if ref.player_id == pid for cid in zone.card_ids)

def locate(state, cid):
    return next(ref for ref, zone in state.zones.items() if cid in zone.card_ids)

def delayed_definition(state, cid):
    return state.metadata.get('virtual_delayed_cards', {}).get(cid, state.cards[cid].definition_id)

@dataclass(frozen=True, slots=True)
class NullificationWindow(Action):
    target_id: str

class NullificationHandler:
    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            frame.local['cancelled'] = False
            frame.local['round'] = 0
            frame.local['start'] = state.seat_order.index(state.current_player_id or state.seat_order[0])
            frame.step_index = 1
        if frame.step_index == 2:
            if frame.child_result is not None:
                frame.local['cancelled'] = not frame.local['cancelled']
                frame.local['round'] += 1
                frame.local['start'] = (frame.local['start'] + frame.cursor - 1) % len(state.seat_order)
                frame.cursor = 0
            frame.step_index = 1
        if frame.cursor >= len(state.seat_order) or state.status is GameStatus.FINISHED:
            return StepResult.complete(bool(frame.local['cancelled']))
        pid = state.seat_order[(int(frame.local['start']) + frame.cursor) % len(state.seat_order)]
        frame.cursor += 1
        if not state.players[pid].is_alive:
            return StepResult.continue_()
        frame.step_index = 2
        return StepResult.push(RespondWithCardAction(
            f'{action.action_id}:counter:{frame.local["round"]}:{frame.cursor}', pid,
            'trick.nullification', action.action_id, '无懈可击：响应锦囊或反制上一张无懈', action.target_id))

@dataclass(frozen=True, slots=True)
class TrickAction(Action):
    source_id: str
    card_id: str
    definition_id: str
    targets: tuple[str, ...] = ()
    virtual_card: VirtualCard | None = None

@dataclass(frozen=True, slots=True)
class TargetTrick(Action):
    source_id: str
    target_id: str
    card_id: str
    definition_id: str
    pool_key: str = ''

class MilitaryTrickRule:
    def __init__(self, definition, distance, skills=None):
        self.definition = definition
        self.distance = distance
        self.skills = skills
        self.requires_target_selection = definition not in ('trick.ex_nihilo','trick.savage_assault',
            'trick.archery_attack','trick.god_salvation','trick.amazing_grace','delayed.lightning')
    def can_use(self, state, user):
        from .qiaoshui import prohibited
        if prohibited(state,user,self.definition):return False
        if state.players[user].marks.get('zhuikong_self_only')==state.turn_number and self.definition in ('trick.savage_assault','trick.archery_attack'):return False
        if (state.current_phase is Phase.PLAY and state.players[user].marks.get('yj_zishou') == state.turn_number
                and self.definition in ('trick.savage_assault', 'trick.archery_attack', 'trick.god_salvation', 'trick.amazing_grace')):
            return False
        if self.definition == 'trick.nullification':
            return False
        if self.definition == 'delayed.lightning':
            return not self._duplicate(state, user)
        return True
    def _duplicate(self, state, pid):
        return any(delayed_definition(state, cid) == self.definition
                   for cid in state.cards_in(ZoneRef(ZoneType.JUDGMENT,pid)))
    def target_candidates(self, state, user):
        d = self.definition
        def valid(pid):
            from .fuhuanghou import target_allowed
            if not target_allowed(state,user,pid):return False
            if (pid != user and state.current_phase is Phase.PLAY
                    and state.players[user].marks.get('yj_zishou') == state.turn_number):
                return False
            if not state.players[pid].is_alive:
                return False
            if self.skills is not None:
                if d in ('trick.snatch', 'delayed.indulgence') and self.skills.has(state, pid, 'qianxun'):
                    return False
                if d == 'trick.duel' and self.skills.has(state, pid, 'kongcheng') and not state.cards_in(ZoneRef(ZoneType.HAND, pid)):
                    return False
            if d == 'trick.iron_chain':
                return True
            if pid == user and d != 'trick.fire_attack':
                return False
            if d in ('trick.dismantlement','trick.snatch'):
                return bool(personal_cards(state,pid)) and (d != 'trick.snatch' or
                    self.skills is not None and self.skills.has(state, user, 'qicai') or
                    self.distance.distance_between(state,user,pid) <= 1)
            if d == 'trick.borrowed_sword':
                return equipped(state,pid,EquipmentSlot.WEAPON) is not None and any(
                    self.distance.can_reach_with_slash(state,pid,q) for q in state.seat_order if q != pid and state.players[q].is_alive)
            if d == 'trick.fire_attack':
                return bool(state.cards_in(ZoneRef(ZoneType.HAND,pid)))
            if d.startswith('delayed.'):
                supply_range = (2 if self.skills is not None and self.skills.has(state, user, 'duanliang') else 1)
                return not self._duplicate(state,pid) and (d != 'delayed.supply_shortage' or self.distance.distance_between(state,user,pid) <= supply_range)
            return True
        return tuple(pid for pid in state.seat_order if valid(pid))
    def target_bounds(self, state, user, card):
        return (0,2) if self.definition == 'trick.iron_chain' else (1,1)
    def validate_targets(self,state,user,targets):
        if not self.requires_target_selection:
            if targets:
                raise InvalidCardUse('this trick computes its targets')
            return
        low, high = self.target_bounds(state,user,None)
        if not low <= len(targets) <= high or len(set(targets)) != len(targets) or any(pid not in self.target_candidates(state,user) for pid in targets):
            raise InvalidCardUse('invalid trick targets')
    def usage_limit(self,state,user):
        return None
    def effect_action(self,aid,user,card,targets):
        return TrickAction(aid,user,card,self.definition,targets)

class TrickHandler:
    def __init__(self,moves,deck,recorder,skills=None,definitions=None):
        self.moves=moves
        self.deck=deck
        self.recorder=recorder
        self.skills=skills
        self.definitions=definitions
    def step(self,state,frame):
        a=frame.action
        d=a.definition_id
        if frame.step_index == 0:
            from .forest import weimu_blocks
            if d.startswith('delayed.'):
                target = a.targets[0] if a.targets else a.source_id
                if weimu_blocks(state, target, a.card_id, d, a.source_id, self.skills, a.virtual_card):
                    raise InvalidCardUse('帷幕阻止黑色锦囊成为目标')
                self.moves.move(state,CardMove(a.action_id+':attach',(a.card_id,),ZoneRef(ZoneType.PROCESSING),
                    ZoneRef(ZoneType.JUDGMENT,target),CardMoveReason.USE,a.source_id))
                return StepResult.complete()
            if d == 'trick.iron_chain' and not a.targets:
                # Recast is not a trick effect and has no counter window.
                self.moves.move(state,CardMove(a.action_id+':recast',(a.card_id,),ZoneRef(ZoneType.PROCESSING),
                    ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.RECAST,a.source_id))
                return StepResult.complete(self.deck.draw(state,a.source_id,1,a.action_id+':draw'))
            order=state.seat_order[state.seat_order.index(a.source_id):]+state.seat_order[:state.seat_order.index(a.source_id)]
            targets=a.targets
            if d == 'trick.ex_nihilo':
                targets=(a.source_id,)
            elif d in ('trick.savage_assault','trick.archery_attack'):
                targets=tuple(pid for pid in order if pid != a.source_id and state.players[pid].is_alive)
            elif d in ('trick.god_salvation','trick.amazing_grace'):
                targets=tuple(pid for pid in order if state.players[pid].is_alive)
            targets=tuple(pid for pid in targets if not weimu_blocks(
                state, pid, a.card_id, d, a.source_id, self.skills, a.virtual_card))
            if d in ('trick.savage_assault', 'trick.archery_attack'):
                from .forest import savage_effect_immune
                from .yj2011_tier3 import protected
                targets = tuple(pid for pid in targets if
                    equipped(state, pid, EquipmentSlot.ARMOR) != 'equipment.armor.vine'
                    and not protected(state, pid)
                    and not (d == 'trick.savage_assault' and savage_effect_immune(state, pid, self.skills)))
            from .fuhuanghou import target_allowed
            targets=tuple(pid for pid in targets if target_allowed(state,a.source_id,pid))
            from .qiaoshui import take_targets
            adjusted=take_targets(state,a.action_id,targets)
            targets=tuple(q for q in adjusted if q in targets) if d in ('trick.savage_assault','trick.archery_attack','trick.god_salvation','trick.amazing_grace') else adjusted
            frame.local['targets']='|'.join(targets)
            if not a.targets and d in ('trick.savage_assault', 'trick.archery_attack', 'trick.god_salvation', 'trick.amazing_grace'):
                self.recorder.record(TrickTargetsDeclaredEvent(a.action_id+':targets',
                    a.source_id, a.card_id, d, tuple(targets)))
            frame.local['pool']=a.action_id
            if d == 'trick.amazing_grace':
                pool=ZoneRef(ZoneType.SPECIAL,special_key=a.action_id)
                count=self.deck.draw(state,a.source_id,len(targets),a.action_id+':reveal')
                hand=state.cards_in(ZoneRef(ZoneType.HAND,a.source_id))
                drawn=hand[-count:] if count else ()
                if drawn:
                    self.moves.move(state,CardMove(a.action_id+':pool',drawn,ZoneRef(ZoneType.HAND,a.source_id),pool,CardMoveReason.SYSTEM))
            frame.step_index=1
        targets=str(frame.local['targets']).split('|') if frame.local['targets'] else []
        if frame.step_index==5:
            if frame.child_result is True:
                frame.local['zhenlie_cancelled']=(*frame.local.get('zhenlie_cancelled',()),frame.local['zhenlie_target'])
            frame.step_index=1
        if frame.step_index==1 and state.status is not GameStatus.FINISHED:
            index=frame.local.get('zhenlie_cursor',0)
            while index<len(targets):
                target=targets[index];index+=1;frame.local['zhenlie_cursor']=index
                if (target!=a.source_id and state.players[target].is_alive and self.skills is not None
                        and self.skills.has(state,target,'zhenlie')):
                    frame.local['zhenlie_target']=target;frame.step_index=5
                    from .yj2012 import YJ2012Action
                    return StepResult.push(YJ2012Action(a.action_id+':zhenlie:'+target,target,'zhenlie',a.source_id,
                        card_ids=(a.card_id,),definition_id=d))
        if frame.step_index == 2:
            frame.step_index=3
            if not frame.child_result:
                return StepResult.push(TargetTrick(f'{a.action_id}:effect:{frame.cursor}',a.source_id,
                    targets[frame.cursor-1],a.card_id,d,str(frame.local['pool'])))
        if frame.step_index == 3:
            frame.step_index=1
        if state.status is GameStatus.FINISHED or frame.cursor >= len(targets):
            pool=ZoneRef(ZoneType.SPECIAL,special_key=a.action_id)
            remainder=state.cards_in(pool)
            if remainder:
                self.moves.move(state,CardMove(a.action_id+':pool-cleanup',remainder,pool,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
            return StepResult.complete()
        target=targets[frame.cursor]
        frame.cursor+=1
        if not state.players[target].is_alive or target in frame.local.get('zhenlie_cancelled',()):
            return StepResult.continue_()
        if d == 'trick.savage_assault':
            from .forest import savage_effect_immune
            if savage_effect_immune(state, target, self.skills):
                return StepResult.continue_()
        frame.step_index=2
        self.recorder.record(Event(a.action_id+f':current:{frame.cursor}','effect_target',a.source_id,(target,),metadata={'definition_id':d}))
        if self.definitions is not None and not self.definitions.get(d).nullifiable:
            frame.child_result = False
            return StepResult.continue_()
        return StepResult.push(NullificationWindow(f'{a.action_id}:window:{frame.cursor}',target))

class TargetTrickHandler:
    def __init__(self,moves,distance,skills=None):
        self.moves=moves
        self.distance=distance
        self.skills=skills
    def ask(self,a,f,player,kind,prompt,**kwargs):
        return StepResult.ask(PendingRequest(f'{a.action_id}:request:{f.step_index}',player,kind,prompt,a.action_id,f.frame_id,**kwargs))
    def move(self,state,a,cid,dest):
        self.moves.move(state,CardMove(a.action_id+f':move:{cid}',(cid,),locate(state,cid),dest,CardMoveReason.DISCARD,a.source_id))
    def step(self,state,f):
        a=f.action
        d=a.definition_id
        hand=ZoneRef(ZoneType.HAND,a.target_id)
        if f.step_index == 0:
            from .yj2011_tier3 import protected
            if protected(state, a.target_id):
                return StepResult.complete('prevented')
            f.step_index=1
            if d == 'trick.ex_nihilo':
                return StepResult.push(DrawCardsAction(a.action_id+':draw',a.target_id,2))
            if d == 'trick.god_salvation':
                return StepResult.push(RecoverAction(a.action_id+':heal',a.source_id,a.target_id,1))
            if d == 'trick.iron_chain':
                from .chaining import set_chained
                set_chained(state,a.target_id,not state.players[a.target_id].chained,self.skills)
                return StepResult.complete()
            if d in ('trick.dismantlement','trick.snatch'):
                eligible=personal_cards(state,a.target_id)
                if not eligible:
                    return StepResult.complete()
                return self.ask(a,f,a.source_id,RequestType.CHOOSE_CARD,'选择目标区域的一张牌',eligible_card_ids=eligible,subject_player_id=a.target_id)
            if d == 'trick.amazing_grace':
                eligible=state.cards_in(ZoneRef(ZoneType.SPECIAL,special_key=a.pool_key))
                return self.ask(a,f,a.target_id,RequestType.CHOOSE_CARD,'五谷丰登：选择公共牌',eligible_card_ids=eligible) if eligible else StepResult.complete()
            if d == 'trick.borrowed_sword':
                candidates=tuple(pid for pid in state.seat_order if pid != a.target_id and state.players[pid].is_alive and self.distance.can_reach_with_slash(state,a.target_id,pid))
                return self.ask(a,f,a.source_id,RequestType.CHOOSE_PLAYER,'借刀杀人：选择被杀目标',allowed_player_ids=candidates)
            if d == 'trick.fire_attack':
                eligible=state.cards_in(hand)
                return self.ask(a,f,a.target_id,RequestType.CHOOSE_CARD,'火攻：展示一张手牌',eligible_card_ids=eligible) if eligible else StepResult.complete()
            if d in ('trick.duel','trick.savage_assault','trick.archery_attack'):
                if d != 'trick.duel' and equipped(state,a.target_id,EquipmentSlot.ARMOR) == 'equipment.armor.vine':
                    return StepResult.complete('prevented')
                f.local['who']=a.target_id
                return StepResult.push(RespondWithCardAction(a.action_id+':response:0',a.target_id,
                    'basic.dodge' if d == 'trick.archery_attack' else 'basic.slash',a.action_id,
                    '请打出闪' if d == 'trick.archery_attack' else '请打出杀',a.target_id))
        if f.step_index == 1:
            if d in ('trick.dismantlement','trick.snatch'):
                self.move(state,a,f.decision,ZoneRef(ZoneType.HAND,a.source_id) if d == 'trick.snatch' else ZoneRef(ZoneType.DISCARD_PILE))
                f.decision=None
                return StepResult.complete()
            if d == 'trick.amazing_grace':
                self.move(state,a,f.decision,hand)
                f.decision=None
                return StepResult.complete()
            if d == 'trick.fire_attack':
                from .suits import effective_suit
                suit=effective_suit(state, f.decision, a.target_id)
                f.local['revealed_card_id']=str(f.decision)
                f.local['revealed_suit']=suit.value
                self.moves.recorder.record(Event(a.action_id+':revealed','card_revealed',a.target_id,(a.source_id,),metadata={'card_id':str(f.decision),'reason':'fire_attack'}))
                f.decision=None
                f.step_index=2
                eligible=tuple(cid for cid in state.cards_in(ZoneRef(ZoneType.HAND,a.source_id))
                               if effective_suit(state, cid, a.source_id) == suit)
                if not eligible:
                    self.moves.recorder.record(Event(a.action_id+':no-match','fire_attack_result',a.source_id,(a.target_id,),metadata={'suit':suit.value,'stage':'no_match','dealt_damage':False}))
                return self.ask(a,f,a.source_id,RequestType.RESPOND_WITH_CARD,f'火攻：请选择弃置一张 { {Suit.SPADE: "♠", Suit.HEART: "♥", Suit.CLUB: "♣", Suit.DIAMOND: "♦"}[suit]} 手牌，或放弃' if eligible else f'火攻：没有可弃置的 { {Suit.SPADE: "♠", Suit.HEART: "♥", Suit.CLUB: "♣", Suit.DIAMOND: "♦"}[suit]} 手牌，未造成伤害',eligible_card_ids=eligible,allow_pass=True)
            if d == 'trick.borrowed_sword':
                f.local['victim']=str(f.decision)
                f.decision=None
                f.step_index=2
                return StepResult.push(RespondWithCardAction(a.action_id+':borrow-response',a.target_id,'basic.slash',a.action_id,'借刀：使用杀或交出武器',str(f.local['victim'])))
            if d in ('trick.duel','trick.savage_assault','trick.archery_attack'):
                if f.child_result is not None:
                    if d != 'trick.duel':
                        return StepResult.complete()
                    responder = f.local['who']
                    opponent = a.source_id if responder == a.target_id else a.target_id
                    if (self.skills is not None and self.skills.has(state,opponent,'wushuang') and
                            not f.local.get('duel_second')):
                        f.local['duel_second'] = True
                        f.cursor += 1
                        return StepResult.push(RespondWithCardAction(f'{a.action_id}:response:{f.cursor}',responder,
                            'basic.slash',a.action_id,'无双：决斗中请再打出一张杀',responder))
                    f.local.pop('duel_second',None)
                    who=a.source_id if f.local['who'] == a.target_id else a.target_id
                    f.local['who']=who
                    f.cursor+=1
                    return StepResult.push(RespondWithCardAction(f'{a.action_id}:response:{f.cursor}',who,'basic.slash',a.action_id,'决斗：请继续打出杀',who))
                f.step_index=3
                f.local.pop('duel_second',None)
                who=str(f.local['who'])
                source=(a.target_id if who == a.source_id else a.source_id) if d == 'trick.duel' else a.source_id
                if d == 'trick.duel':f.local['duel_winner']=source;f.local['duel_loser']=who
                if d == 'trick.savage_assault':
                    from .forest import savage_damage_source
                    source = savage_damage_source(state, a.source_id, self.skills)
                return StepResult.push(MilitaryDamageAction(a.action_id+':damage',source,who,1,card_id=a.card_id))
            return StepResult.complete()
        if f.step_index == 2:
            f.step_index=3
            if d == 'trick.fire_attack':
                choice=f.decision
                f.decision=None
                if choice is PASS_RESPONSE:
                    self.moves.recorder.record(Event(a.action_id+':no-damage','fire_attack_result',a.source_id,(a.target_id,),metadata={'suit':f.local.get('revealed_suit',''),'dealt_damage':False}))
                    return StepResult.complete()
                self.move(state,a,choice,ZoneRef(ZoneType.DISCARD_PILE))
                return StepResult.push(MilitaryDamageAction(a.action_id+':fire',a.source_id,a.target_id,1,DamageNature.FIRE,a.card_id))
            if d == 'trick.borrowed_sword':
                if f.child_result is not None:
                    result=f.child_result
                    cid=result.material_ids[0] if isinstance(result,VirtualCard) else str(result)
                    return StepResult.push(MilitaryStrike(a.action_id+':borrowed-slash',a.target_id,str(f.local['victim']),cid,'basic.dodge',virtual_card=result if isinstance(result,VirtualCard) else None))
                ref=ZoneRef(ZoneType.EQUIPMENT,a.target_id,EquipmentSlot.WEAPON)
                cards=state.cards_in(ref)
                if cards:
                    self.move(state,a,cards[0],ZoneRef(ZoneType.HAND,a.source_id))
        if d == 'trick.duel' and f.step_index==3 and f.local.get('duel_winner'):
            self.moves.recorder.record(Event(a.action_id+':duel-resolved','duel_resolved',a.source_id,(a.target_id,),metadata={'winner_id':f.local['duel_winner'],'loser_id':f.local['duel_loser']}))
        return StepResult.complete()

@dataclass(frozen=True,slots=True)
class ResolveDelayed(Action):
    player_id: str
    card_id: str

class DelayedHandler:
    def __init__(self,moves,definitions=None):
        self.moves=moves
        self.definitions=definitions
    def step(self,state,f):
        a=f.action
        d=delayed_definition(state, a.card_id)
        if f.step_index == 0:
            f.step_index=1
            if self.definitions is not None and not self.definitions.get(d).nullifiable:
                f.child_result = False
                return StepResult.continue_()
            return StepResult.push(NullificationWindow(a.action_id+':window',a.player_id))
        if f.step_index == 1:
            if f.child_result:
                f.local['cancelled']=True
                f.step_index=3
            else:
                f.step_index=2
                pattern={'delayed.indulgence':JudgmentPattern(suit=Suit.HEART),
                    'delayed.supply_shortage':JudgmentPattern(suit=Suit.CLUB),
                    'delayed.lightning':JudgmentPattern(suit=Suit.SPADE,ranks=frozenset(range(2,10)))}[d]
                return StepResult.push(JudgmentAction(a.action_id+':judgment',a.player_id,pattern))
        if f.step_index == 2:
            f.local['hit']=bool(f.child_result)
            f.step_index=3
            if d == 'delayed.lightning' and f.child_result:
                self.moves.move(state,CardMove(a.action_id+':discard',(a.card_id,),locate(state,a.card_id),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
                f.step_index=4
                return StepResult.push(MilitaryDamageAction(a.action_id+':lightning',None,a.player_id,3,DamageNature.THUNDER,a.card_id))
            if d != 'delayed.lightning' and not f.child_result:
                state.players[a.player_id].marks['skip_play' if d == 'delayed.indulgence' else 'skip_draw']=1
        if f.step_index == 3:
            dest=ZoneRef(ZoneType.DISCARD_PILE)
            if d == 'delayed.lightning':
                start=state.seat_order.index(a.player_id)
                order=state.seat_order[start+1:]+state.seat_order[:start]
                for pid in order:
                    if state.players[pid].is_alive and not any(state.cards[cid].definition_id == d for cid in state.cards_in(ZoneRef(ZoneType.JUDGMENT,pid))):
                        dest=ZoneRef(ZoneType.JUDGMENT,pid)
                        break
            self.moves.move(state,CardMove(a.action_id+':move',(a.card_id,),locate(state,a.card_id),dest,CardMoveReason.SYSTEM))
        return StepResult.complete()

class JudgmentPhaseBody:
    def step(self,state,f):
        a=f.action
        if f.step_index == 1:
            f.local['cards']='|'.join(reversed(state.cards_in(ZoneRef(ZoneType.JUDGMENT,a.player_id))))
            f.step_index=2
        cards=str(f.local['cards']).split('|') if f.local['cards'] else []
        if f.cursor >= len(cards) or not state.players[a.player_id].is_alive or state.status is GameStatus.FINISHED:
            return StepResult.complete()
        cid=cards[f.cursor]
        f.cursor+=1
        if cid not in state.cards_in(ZoneRef(ZoneType.JUDGMENT,a.player_id)):
            return StepResult.continue_()
        return StepResult.push(ResolveDelayed(f'{a.action_id}:delayed:{f.cursor}',a.player_id,cid))

def register_military_tricks(definitions,rules,registry,moves,events,deck,bodies,skills=None):
    from sanguosha.content.cards.classic_military import TRICKS,DELAYED
    from .distance import DistanceSystem
    distance=DistanceSystem(definitions)
    for key,_ in TRICKS:
        rules.register('trick.'+key,MilitaryTrickRule('trick.'+key,distance,skills))
    for key,_ in DELAYED:
        rules.register('delayed.'+key,MilitaryTrickRule('delayed.'+key,distance,skills))
    registry.register(NullificationWindow,NullificationHandler())
    registry.register(TrickAction,TrickHandler(moves,deck,events,skills,definitions))
    registry.register(TargetTrick,TargetTrickHandler(moves,distance,skills))
    registry.register(ResolveDelayed,DelayedHandler(moves,definitions))
    bodies.register(Phase.JUDGMENT,JudgmentPhaseBody())

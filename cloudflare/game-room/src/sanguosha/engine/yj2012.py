"""Classic YJ2012 resumable skills; production exposure is acceptance-gated."""
from dataclasses import dataclass
from sanguosha.model.enums import Phase, Color, Suit, DamageNature
from sanguosha.model.zones import ZoneRef, ZoneType
from .actions import Action, StepResult
from .requests import RequestType
from .deck import DrawCardsAction
from .hp import LoseMaxHpAction
from .recovery import RecoverAction
from .card_moves import CardMoveReason
from .card_rules import InvalidCardUse
from .suits import effective_color
from .yj2011_tier3 import YJSkillHandler, hand


@dataclass(frozen=True, slots=True)
class YJ2012Action(Action):
    player_id: str
    skill: str
    opponent_id: str | None = None
    card_ids: tuple[str, ...] = ()
    amount: int = 1
    definition_id: str = ''


def power_zone(pid):
    return ZoneRef(ZoneType.SPECIAL, pid, special_key='quan')


def factions(state, skills):
    return len({skills.faction(state, q) for q in state.seat_order if state.players[q].is_alive})


class YJ2012Handler(YJSkillHandler):
    def step(self,state,f):
        if f.step_index == 0 and not self.skills.has(state, f.action.player_id, f.action.skill):
            if f.action.skill in ('paiyi', 'anxu', 'gongqi', 'jiefan', 'qice', 'lihuo'):
                raise InvalidCardUse('角色不具有该主动技能')
            return StepResult.complete()
        if f.action.skill=='lihuo' and f.step_index>=3:
            return self.lihuo(state,f)
        if f.action.skill == 'qice' and f.step_index == 3:
            return self.qice(state,f)
        if f.action.skill == 'zhuiyi':
            return self.zhuiyi(state,f)
        return super().step(state,f)

    def chunlao(self,state,f):
        from .military_basics import SLASH_IDS
        a=f.action;pid=a.player_id
        wine=ZoneRef(ZoneType.SPECIAL,pid,special_key='wine')
        if f.step_index==0:
            cards=tuple(c for c in hand(state,pid) if state.cards[c].definition_id in SLASH_IDS)
            if state.cards_in(wine) or not cards:return StepResult.complete()
            f.local['cards']=cards;f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【醇醪】是否将任意张手牌杀置为醇？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_CARDS,'【醇醪】选择置为醇的手牌杀',eligible_card_ids=f.local['cards'],min_count=1,max_count=len(f.local['cards']))
        cards,f.decision=tuple(f.decision),None
        self.transfer(state,a,cards,wine)
        return StepResult.complete()

    def lihuo(self,state,f):
        from dataclasses import replace
        from .military_basics import MilitarySlashRule,SlashSequence
        from .suits import effective_suit
        from sanguosha.model.virtual_card import VirtualCard
        from .events import CardUsedEvent
        from .yj2011_tier3 import record_slash_use
        from .hp import LoseHpAction
        a=f.action;pid=a.player_id
        rule=MilitarySlashRule(self.authorized.distance,self.skills)
        if f.step_index==0:
            if state.current_player_id!=pid or state.current_phase is not Phase.PLAY:raise InvalidCardUse('烈火仅出牌阶段使用')
            from .card_limits import card_allowed
            cards=tuple(c for c in hand(state,pid) if state.cards[c].definition_id=='basic.slash' and card_allowed(state,pid,(c,)))
            limit=rule.usage_limit(state,pid)
            if not cards or not rule.can_use(state,pid) or not rule.target_candidates(state,pid) or (limit is not None and state.play_usage.count('basic.slash')>=limit):raise InvalidCardUse('烈火不可用')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_CARD,'【烈火】选择一张普通杀当火杀',eligible_card_ids=cards)
        if f.step_index==1:
            f.local['card'],f.decision=f.decision,None
            f.step_index=2
            # A printed FireSlash has the same extra-target modifier as conversion.
            maximum=rule.target_bounds(state,pid,None)[1]
            return self.ask(f,RequestType.CHOOSE_PLAYERS,'【烈火】选择火杀目标',allowed_player_ids=rule.target_candidates(state,pid),min_count=1,max_count=maximum)
        if f.step_index==2:
            card=f.local['card'];targets,f.decision=tuple(f.decision),None
            from .card_limits import card_allowed
            if card not in hand(state,pid) or not card_allowed(state,pid,(card,)):raise InvalidCardUse('烈火素材不可用')
            rule.validate_targets(state,pid,targets)
            virtual=replace(VirtualCard.spear(state,(card,),lambda st,cid:effective_suit(st,cid,pid)),definition_id='basic.fire_slash',skill_id='lihuo')
            self.transfer(state,a,(card,),ZoneRef(ZoneType.PROCESSING),CardMoveReason.USE)
            counted=record_slash_use(state,pid,targets)
            state.metadata.setdefault('lihuo_hits',{}).pop(pid+':'+card,None)
            self.moves.recorder.record(CardUsedEvent(a.action_id+':used',pid,card,targets,'basic.fire_slash',counted,virtual))
            f.step_index=3
            return StepResult.push(SlashSequence(a.action_id+':slash',pid,card,targets,virtual))
        if f.step_index==3:
            card=f.local['card']
            if card in state.cards_in(ZoneRef(ZoneType.PROCESSING)):
                self.transfer(state,a,(card,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.USE)
            hit=state.metadata.get('lihuo_hits',{}).pop(pid+':'+card,False)
            if hit and state.players[pid].is_alive and self.skills.has(state,pid,'lihuo'):
                f.step_index=4
                return StepResult.push(LoseHpAction(a.action_id+':lihuo-cost',pid,1))
        return StepResult.complete()

    def qianxi(self,state,f):
        from .judgment import JudgmentAction, JudgmentPattern
        a=f.action;pid=a.player_id
        if f.step_index==0:
            targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive
                          and self.authorized.distance.distance_between(state,pid,q)==1)
            if not targets:return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【潜袭】是否判定并限制距离为一的一名角色的手牌？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            f.step_index=2
            return StepResult.push(JudgmentAction(a.action_id+':judge',pid,JudgmentPattern(),return_card_id=True))
        if f.step_index==2:
            targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive
                          and self.authorized.distance.distance_between(state,pid,q)==1)
            if not targets:return StepResult.complete()
            f.local['color']=effective_color(state,f.child_result,pid).value
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【潜袭】选择距离为一的角色',allowed_player_ids=targets,min_count=1,max_count=1)
        from .card_limits import clear_source
        target,f.decision=f.decision,None
        clear_source(state,pid)
        color=f.local['color']
        state.metadata.setdefault('qianxi_limits',{})[pid]={'target':target,'color':color,'turn':state.turn_number}
        state.players[target].marks['qianxi_'+color+'_'+pid]=1
        return StepResult.complete()

    def zhenlie(self,state,f):
        from .hp import LoseHpAction
        from .military_equipment import discardable
        a=f.action;pid=a.player_id;source=a.opponent_id
        if source==pid:return StepResult.complete(False)
        if f.step_index==0:
            f.step_index=1
            name=self.definitions.get(a.definition_id).name if a.definition_id else '此牌'
            return self.ask(f,RequestType.YES_NO,f'【贞烈】针对【{name}】，是否失去一点体力令其对你无效并弃置来源一张牌？',subject_player_id=source)
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete(False)
            f.step_index=2
            return StepResult.push(LoseHpAction(a.action_id+':cost',pid,1))
        if f.step_index==2:
            if source not in state.players or not state.players[source].is_alive:return StepResult.complete(True)
            cards=discardable(state,source)
            if not cards:return StepResult.complete(True)
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_CARD,'【贞烈】弃置来源一张手牌或装备',eligible_card_ids=cards,subject_player_id=source)
        if f.step_index==3:
            card,f.decision=f.decision,None
            self.transfer(state,a,(card,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
        return StepResult.complete(True)

    def qice_virtual(self, state, pid, definition):
        from dataclasses import replace
        from sanguosha.model.virtual_card import VirtualCard
        from .suits import effective_suit
        return replace(VirtualCard.spear(state, hand(state,pid),
            lambda state,cid:effective_suit(state,cid,pid)), definition_id=definition, skill_id="qice")

    def qice_targets(self, state, pid, definition):
        from .military_tricks import MilitaryTrickRule
        from .forest import weimu_blocks
        rule=MilitaryTrickRule(definition,self.authorized.distance,self.skills)
        virtual=self.qice_virtual(state,pid,definition)
        return tuple(q for q in rule.target_candidates(state,pid)
            if not weimu_blocks(state,q,virtual.material_ids[0],definition,pid,self.skills,virtual))

    def qice_definitions(self,state,pid):
        from .military_tricks import MilitaryTrickRule
        from .card_limits import card_allowed
        if not hand(state,pid) or not card_allowed(state,pid,hand(state,pid)): return ()
        return tuple(d for d in self.definitions._definitions
            if d.startswith('trick.') and MilitaryTrickRule(d,self.authorized.distance,self.skills).can_use(state,pid)
            and (not MilitaryTrickRule(d,self.authorized.distance,self.skills).requires_target_selection
                 or self.qice_targets(state,pid,d)))

    def qice(self,state,f):
        from .military_tricks import MilitaryTrickRule, TrickAction
        from .events import CardUsedEvent
        a=f.action; pid=a.player_id
        if f.step_index==0:
            self.validate_active(state,a)
            choices=self.qice_definitions(state,pid)
            if not choices: raise InvalidCardUse('qice has no legal trick')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_OPTION,'【奇策】选择非延时锦囊',choices=choices)
        if f.step_index==1:
            definition,f.decision=f.decision,None
            if definition not in self.qice_definitions(state,pid): raise InvalidCardUse('qice trick became unavailable')
            f.local['definition']=definition; f.step_index=2
            rule=MilitaryTrickRule(definition,self.authorized.distance,self.skills)
            if rule.requires_target_selection:
                low,high=rule.target_bounds(state,pid,None)
                return self.ask(f,RequestType.CHOOSE_PLAYERS,'【奇策】选择锦囊目标',
                    allowed_player_ids=self.qice_targets(state,pid,definition),min_count=max(1,low),max_count=high)
            f.decision=()
        if f.step_index==2:
            definition=f.local['definition']; targets,f.decision=tuple(f.decision),None
            self.validate_active(state,a)
            if definition not in self.qice_definitions(state,pid): raise InvalidCardUse('qice became unavailable')
            rule=MilitaryTrickRule(definition,self.authorized.distance,self.skills)
            rule.validate_targets(state,pid,targets)
            if rule.requires_target_selection and (not targets or any(q not in self.qice_targets(state,pid,definition) for q in targets)):
                raise InvalidCardUse('qice targets became unavailable')
            virtual=self.qice_virtual(state,pid,definition)
            f.local['materials']=virtual.material_ids
            self.transfer(state,a,virtual.material_ids,ZoneRef(ZoneType.PROCESSING),CardMoveReason.USE)
            state.play_usage.record('skill.qice'); state.play_usage.record(definition)
            self.moves.recorder.record(CardUsedEvent(a.action_id+':used',pid,virtual.material_ids[0],targets,definition,virtual_card=virtual))
            f.step_index=3
            return StepResult.push(TrickAction(a.action_id+':trick',pid,virtual.material_ids[0],definition,targets,virtual))
        cards=tuple(c for c in f.local['materials'] if c in state.cards_in(ZoneRef(ZoneType.PROCESSING)))
        if cards: self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.USE)
        return StepResult.complete()

    def anxu(self,state,f):
        a=f.action; pid=a.player_id
        others=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive)
        if f.step_index==0:
            self.validate_active(state,a)
            first=tuple(q for q in others if any(len(hand(state,q))!=len(hand(state,r)) for r in others))
            if not first: raise InvalidCardUse('安恤需要两名手牌数不同的其他角色')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【安恤】选择第一名角色',allowed_player_ids=first)
        if f.step_index==1:
            q,f.decision=f.decision,None
            f.local['first']=q; f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【安恤】选择手牌数不同的第二名角色',
                allowed_player_ids=tuple(r for r in others if r!=q and len(hand(state,q))!=len(hand(state,r))))
        if f.step_index==2:
            q=f.local['first']; r,f.decision=f.decision,None
            low,high=sorted((q,r),key=lambda x:len(hand(state,x)))
            if len(hand(state,low))==len(hand(state,high)): raise InvalidCardUse('安恤手牌数已相同')
            f.local.update(low=low,high=high); f.step_index=3
            state.play_usage.record('skill.anxu')
            return self.ask(f,RequestType.CHOOSE_CARD,'【安恤】选择获得的一张背面手牌',player=low,
                eligible_card_ids=hand(state,high),subject_player_id=high)
        if f.step_index==3:
            from .events import Event
            card,f.decision=f.decision,None
            if card not in hand(state,f.local['high']): raise InvalidCardUse('安恤候选已不可用')
            self.moves.recorder.record(Event(a.action_id+':reveal','card_revealed',f.local['low'],metadata={'card_id':card}))
            self.transfer(state,a,(card,),ZoneRef(ZoneType.HAND,f.local['low']),actor=f.local['low'])
            f.step_index=4
            if state.cards[card].suit is not Suit.SPADE:
                return StepResult.push(DrawCardsAction(a.action_id+':bonus',pid,1))
        return StepResult.complete()

    def zhuiyi(self,state,f):
        a=f.action
        if not self.skills.has(state,a.player_id,'zhuiyi'): return StepResult.complete()
        targets=tuple(q for q in state.seat_order if q!=a.player_id and q!=a.opponent_id and state.players[q].is_alive)
        if not targets: return StepResult.complete()
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【追忆】是否令一名非凶手角色摸三张牌并回复一点体力？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted: return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【追忆】选择受益者',allowed_player_ids=targets)
        if f.step_index==2:
            q,f.decision=f.decision,None
            f.local['target']=q; f.step_index=3
            return StepResult.push(DrawCardsAction(a.action_id+':draw',q,3))
        if f.step_index==3:
            f.step_index=4; q=f.local['target']
            if state.players[q].is_alive:
                return StepResult.push(RecoverAction(a.action_id+':recover',a.player_id,q,1))
        return StepResult.complete()

    def fuli(self,state,f):
        from .turnover import TurnoverAction
        a=f.action; p=state.players[a.player_id]
        if f.step_index==0:
            if not self.skills.has(state,a.player_id,'fuli') or p.marks.get('fuli_used') or p.hp>0:
                return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【伏枥】是否消耗限定技，回复至势力数并翻面？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted: return StepResult.complete()
            p.marks['fuli_used']=1; f.step_index=2
            amount=min(p.max_hp,factions(state,self.skills))-p.hp
            if amount>0:
                return StepResult.push(RecoverAction(a.action_id+':recover',a.player_id,a.player_id,amount))
        if f.step_index==2:
            f.step_index=3
            return StepResult.push(TurnoverAction(a.action_id+':turnover',a.player_id))
        return StepResult.complete()

    def miji(self,state,f):
        a=f.action; p=state.players[a.player_id]
        if f.step_index==0:
            lost=max(0,p.max_hp-p.hp)
            others=tuple(q for q in state.seat_order if q!=a.player_id and state.players[q].is_alive)
            if not lost or not others: return StepResult.complete()
            f.local['others']=others; f.step_index=1
            return self.ask(f,RequestType.CHOOSE_OPTION,'【秘计】选择摸牌并分配的数量，0为不发动',
                choices=tuple(str(n) for n in range(lost+1)))
        if f.step_index==1:
            n,f.decision=int(f.decision),None
            if not n: return StepResult.complete()
            f.local.update(remaining=n,allocations=[],used=[]); f.step_index=2
            return StepResult.push(DrawCardsAction(a.action_id+':draw',a.player_id,n))
        if f.step_index==2:
            if not f.local['remaining']:
                for q,cards in f.local['allocations']:
                    self.transfer(state,a,tuple(cards),ZoneRef(ZoneType.HAND,q))
                return StepResult.complete()
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【秘计】选择受赠者',
                allowed_player_ids=tuple(q for q in f.local['others'] if q not in [x[0] for x in f.local['allocations']]))
        if f.step_index==3:
            q,f.decision=f.decision,None
            f.local['recipient']=q; f.step_index=4
            choices=tuple(cid for cid in hand(state,a.player_id) if cid not in f.local['used'])
            remaining=f.local['remaining']
            last=len(f.local['others'])==len(f.local['allocations'])+1
            return self.ask(f,RequestType.CHOOSE_CARDS,'【秘计】选择交出的手牌',eligible_card_ids=choices,
                min_count=remaining if last else 1,max_count=min(remaining,len(choices)))
        cards,f.decision=tuple(f.decision),None
        f.local['allocations'].append((f.local['recipient'],cards))
        f.local['used'].extend(cards); f.local['remaining']-=len(cards)
        f.cursor+=1; f.step_index=2
        return StepResult.continue_()

    def gongqi(self,state,f):
        from .military_equipment import discardable
        from sanguosha.model.enums import CardCategory
        from .yj2011_tier3 import equipped_cards
        a=f.action; pid=a.player_id
        if f.step_index==0:
            self.validate_active(state,a)
            cards=discardable(state,pid)
            if not cards: raise InvalidCardUse('弓骑需要弃牌')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_CARD,'【弓骑】选择弃置的牌',eligible_card_ids=cards)
        if f.step_index==1:
            cid,f.decision=f.decision,None
            is_equipment=self.definitions.get(state.cards[cid].definition_id).category is CardCategory.EQUIPMENT
            self.transfer(state,a,(cid,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            state.play_usage.record('skill.gongqi'); state.players[pid].marks['yj_gongqi']=state.turn_number
            f.step_index=2
            targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive and discardable(state,q))
            if not is_equipment or not targets: return StepResult.complete()
            f.local['targets']=targets
            return self.ask(f,RequestType.YES_NO,'【弓骑】是否再弃置一名其他角色的一张牌？')
        if f.step_index==2:
            wanted,f.decision=f.decision is True,None
            if not wanted: return StepResult.complete()
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【弓骑】选择弃牌目标',allowed_player_ids=f.local['targets'])
        if f.step_index==3:
            q,f.decision=f.decision,None
            f.local['target']=q; f.step_index=4
            return self.ask(f,RequestType.CHOOSE_CARD,'【弓骑】选择目标的一张牌',eligible_card_ids=discardable(state,q),subject_player_id=q)
        cid,f.decision=f.decision,None
        self.transfer(state,a,(cid,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
        return StepResult.complete()

    def jiefan(self,state,f):
        from sanguosha.model.enums import EquipmentSlot
        from .military_equipment import discardable
        a=f.action; pid=a.player_id; p=state.players[pid]
        if f.step_index==0:
            self.validate_active(state,a)
            if p.marks.get('jiefan_used'): raise InvalidCardUse('解烦已消耗')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【解烦】选择受益者',allowed_player_ids=tuple(q for q in state.seat_order if state.players[q].is_alive))
        if f.step_index==1:
            q,f.decision=f.decision,None
            f.local['target']=q; p.marks['jiefan_used']=1
            start=state.seat_order.index(pid)
            order=state.seat_order[start:]+state.seat_order[:start]
            # Snapshot eligibility at invocation; later weapon departures cannot change the ordered payer list.
            f.local['payers']=tuple(r for r in order if r!=q and state.players[r].is_alive and self.authorized.distance.can_reach_with_slash(state,r,q))
            f.step_index=2
        if f.step_index==2:
            q=f.local['target']; payers=f.local['payers']
            if not state.players[q].is_alive or f.cursor>=len(payers): return StepResult.complete()
            payer=payers[f.cursor]
            if not state.players[payer].is_alive:
                f.cursor+=1; return StepResult.continue_()
            weapons=tuple(c for c in discardable(state,payer) if self.definitions.get(state.cards[c].definition_id).equipment_slot is EquipmentSlot.WEAPON)
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_CARDS,'【解烦】可弃置一张武器牌，否则受益者摸一张牌',player=payer,
                            eligible_card_ids=weapons,min_count=0,max_count=min(1,len(weapons)),subject_player_id=q)
        if f.step_index==3:
            cards,f.decision=tuple(f.decision),None
            payer=f.local['payers'][f.cursor]; q=f.local['target']; f.cursor+=1; f.step_index=2
            if cards:
                self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,actor=payer)
                return StepResult.continue_()
            return StepResult.push(DrawCardsAction(a.action_id+f':draw:{f.cursor}',q,1))
        return StepResult.complete()

    def quanji(self, state, f):
        a=f.action
        if not self.skills.has(state,a.player_id,'quanji') or f.cursor >= a.amount:
            return StepResult.complete()
        if f.step_index == 0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【权计】是否摸一张牌，再将一张手牌置为权？')
        if f.step_index == 1:
            wanted,f.decision=f.decision is True,None
            if not wanted:
                f.cursor+=1; f.step_index=0
                return StepResult.continue_()
            f.step_index=2
            return StepResult.push(DrawCardsAction(a.action_id+f':draw:{f.cursor}',a.player_id,1))
        if f.step_index == 2:
            cards=hand(state,a.player_id)
            if not cards:
                f.cursor+=1; f.step_index=0
                return StepResult.continue_()
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_CARD,'【权计】选择一张手牌置为权',eligible_card_ids=cards)
        card,f.decision=f.decision,None
        if card not in hand(state,a.player_id):
            raise InvalidCardUse('权计材料已不可用')
        # The public power pile is snapshotted by the normal zone store.
        self.transfer(state,a,(card,),power_zone(a.player_id))
        state.players[a.player_id].marks['quan']=len(state.cards_in(power_zone(a.player_id)))
        f.cursor+=1; f.step_index=0
        return StepResult.continue_()

    def zili(self,state,f):
        a=f.action; p=state.players[a.player_id]
        if f.step_index == 0:
            if (not self.skills.has(state,a.player_id,'zili') or p.marks.get('zili_awakened')
                    or (len(state.cards_in(power_zone(a.player_id))) < 3 and not p.marks.get('ignore_awakening:zili'))):
                return StepResult.complete()
            p.marks['zili_awakened']=1
            f.step_index=1
            return StepResult.push(LoseMaxHpAction(a.action_id+':cost',a.player_id))
        if f.step_index == 1:
            f.step_index=2
            choices=('draw','recover') if p.hp < p.max_hp else ('draw',)
            return self.ask(f,RequestType.CHOOSE_OPTION,'【自立】摸两张牌或回复一点体力',choices=choices)
        if f.step_index == 2:
            choice,f.decision=f.decision,None
            f.step_index=3
            child=(RecoverAction(a.action_id+':recover',a.player_id,a.player_id,1)
                   if choice == 'recover' else DrawCardsAction(a.action_id+':draw',a.player_id,2))
            return StepResult.push(child)
        p.granted_skills['paiyi']='zili'
        return StepResult.complete()

    def paiyi(self,state,f):
        a=f.action; pid=a.player_id
        if f.step_index == 0:
            if (not self.skills.has(state,pid,'paiyi') or state.current_player_id != pid
                    or state.current_phase is not Phase.PLAY or state.play_usage is None
                    or state.play_usage.count('skill.paiyi') or not state.cards_in(power_zone(pid))):
                raise InvalidCardUse('排异当前不可用')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_CARD,'【排异】选择弃置的一张权',
                            eligible_card_ids=state.cards_in(power_zone(pid)))
        if f.step_index == 1:
            f.local['power'],f.decision=f.decision,None
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【排异】选择摸两张牌的角色',
                            allowed_player_ids=tuple(q for q in state.seat_order if state.players[q].is_alive))
        if f.step_index == 2:
            target,f.decision=f.decision,None
            if f.local['power'] not in state.cards_in(power_zone(pid)):
                raise InvalidCardUse('排异权已不可用')
            self.transfer(state,a,(f.local['power'],),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            state.players[pid].marks['quan']=len(state.cards_in(power_zone(pid)))
            state.play_usage.record('skill.paiyi')
            f.local['target']=target; f.step_index=3
            return StepResult.push(DrawCardsAction(a.action_id+':draw',target,2))
        target=f.local['target']
        if f.step_index == 3 and state.players[target].is_alive and len(hand(state,target))>len(hand(state,pid)):
            from .military_basics import MilitaryDamageAction
            f.step_index=4
            return StepResult.push(MilitaryDamageAction(a.action_id+':damage',pid,target,1))
        return StepResult.complete()

    def jiangchi(self,state,f):
        from .remaining_gods import camp_bonus
        a=f.action; p=state.players[a.player_id]
        if f.step_index == 0:
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_OPTION,'【将驰】选择摸牌模式',choices=('default','jiang','chi'))
        if f.step_index == 1:
            choice,f.decision=f.decision,None
            if choice=='jiang': p.marks['slash_prohibited']=1
            elif choice=='chi':
                p.marks['slash_ignore_distance']=1
                p.marks['slash_quota_bonus']=p.marks.get('slash_quota_bonus',0)+1
            f.step_index=2
            return StepResult.push(DrawCardsAction(a.action_id+':draw',a.player_id,{'default':2,'jiang':3,'chi':1}[choice]+camp_bonus(state,a.player_id,self.skills)))
        return StepResult.complete(True)

    def zishou(self,state,f):
        from .remaining_gods import camp_bonus
        a=f.action
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【自守】是否额外摸势力数张牌，本回合出牌不能指定他人？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if wanted: state.players[a.player_id].marks['yj_zishou']=state.turn_number
            f.step_index=2
            return StepResult.push(DrawCardsAction(a.action_id+':draw',a.player_id,2+(factions(state,self.skills) if wanted else 0)+camp_bonus(state,a.player_id,self.skills)))
        return StepResult.complete(True)

    def zhiyu(self,state,f):
        a=f.action
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【智愚】是否摸一张牌并展示手牌？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted: return StepResult.complete()
            f.step_index=2
            return StepResult.push(DrawCardsAction(a.action_id+':draw',a.player_id,1))
        if f.step_index==2:
            from .events import Event
            cards=hand(state,a.player_id)
            for i,cid in enumerate(cards):
                self.moves.recorder.record(Event(a.action_id+f':reveal:{i}','card_revealed',a.player_id,metadata={'card_id':cid}))
            q=a.opponent_id
            if (not cards or len({effective_color(state,cid,a.player_id) for cid in cards})!=1
                    or q is None or not state.players[q].is_alive or not hand(state,q)):
                return StepResult.complete()
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_CARD,'【智愚】弃置一张手牌',player=q,eligible_card_ids=hand(state,q))
        card,f.decision=f.decision,None
        self.transfer(state,a,(card,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,actor=a.opponent_id)
        return StepResult.complete()


def damage_reaction(state,f,skills):
    if f.step_index!=1 or skills is None: return None
    a=f.action; p=state.players[a.target_id]
    if not p.is_alive: return None
    for skill in ('quanji','zhiyu','shiyong'):
        key='yj2012:'+skill
        if f.local.get(key): continue
        f.local[key]=True
        if not skills.has(state,a.target_id,skill): continue
        if skill=='shiyong':
            virtual=getattr(a,'virtual_card',None)
            definition=(virtual.definition_id if virtual else state.cards[a.card_id].definition_id
                        if a.card_id in state.cards else '')
            if (getattr(a,'card_kind','') != 'slash'
                    or definition not in ('basic.slash','basic.fire_slash','basic.thunder_slash')): continue
            color=virtual.color if virtual else effective_color(state,a.card_id,a.source_id)
            if color is not Color.RED and not getattr(a,'wine_enhanced',False): continue
            return StepResult.push(LoseMaxHpAction(a.action_id+':shiyong',a.target_id))
        return StepResult.push(YJ2012Action(a.action_id+':'+skill,a.target_id,skill,a.source_id,
                                          amount=int(f.local['amount'])))
    return None


def play_options(state,pid,skills):
    if (skills.has(state,pid,'paiyi') and state.play_usage is not None
            and not state.play_usage.count('skill.paiyi') and state.cards_in(power_zone(pid))):
        options=['skill:paiyi']
    else:
        options=[]
    from .military_equipment import discardable
    if skills.has(state,pid,'gongqi') and not state.play_usage.count('skill.gongqi') and discardable(state,pid):
        options.append('skill:gongqi')
    if skills.has(state,pid,'jiefan') and not state.players[pid].marks.get('jiefan_used'):
        options.append('skill:jiefan')
    from .card_limits import card_allowed
    if skills.has(state,pid,'qice') and not state.play_usage.count('skill.qice') and hand(state,pid) and card_allowed(state,pid,hand(state,pid)):
        options.append('skill:qice')
    others=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive)
    if skills.has(state,pid,'anxu') and not state.play_usage.count('skill.anxu') and len({len(hand(state,q)) for q in others})>1:
        options.append('skill:anxu')
    return options


def register(registry,skills,moves,definitions,deck):
    registry.register(YJ2012Action,YJ2012Handler(skills,moves,definitions,deck))

"""Remaining God skills on the existing stack, moves, and damage pipeline."""
from dataclasses import dataclass
from .actions import Action,StepResult
from .yj2011_tier3 import YJSkillHandler
from .requests import RequestType
from .card_moves import CardMoveReason
from .military_basics import MilitaryDamageAction
from .events import Event
from .card_rules import InvalidCardUse
from sanguosha.model.enums import Phase,DamageNature
from sanguosha.model.zones import ZoneRef,ZoneType


@dataclass(frozen=True,slots=True)
class RemainingGodAction(Action):
    player_id: str
    skill: str
    opponent_id: str | None = None


def region(state,pid):
    return tuple(c for ref,z in state.zones.items() if ref.player_id==pid
                 and ref.zone_type in (ZoneType.HAND,ZoneType.EQUIPMENT,ZoneType.JUDGMENT)
                 for c in z.card_ids)


def gain_junlve(state,source,target,amount,skills):
    if skills is None:return
    for pid in (source,target):
        if pid in state.players and state.players[pid].is_alive and skills.has(state,pid,'junlve'):
            p=state.players[pid];p.marks['junlve']=p.marks.get('junlve',0)+amount


def camp_source(state,holder,skills):
    if skills is None or not state.players[holder].marks.get('camp'):return None
    owners=tuple(q for q in state.seat_order if state.players[q].is_alive and skills.has(state,q,'jieying_ganning'))
    source=state.metadata.get('camp_sources',{}).get(holder)
    return source if source in owners else owners[0] if owners else None


def camp_bonus(state,holder,skills):
    return int(camp_source(state,holder,skills) is not None)


def camp_start(state,pid,skills):
    if skills is None or not skills.has(state,pid,'jieying_ganning'):return
    if not any(p.is_alive and p.marks.get('camp') for p in state.players.values()):
        state.players[pid].marks['camp']=1
        state.metadata.setdefault('camp_sources',{})[pid]=pid


def clear_camp(state,holder):
    state.players[holder].marks.pop('camp',None)
    state.metadata.get('camp_sources',{}).pop(holder,None)


class RemainingGodHandler(YJSkillHandler):
    def duorui(self,state,f):
        from sanguosha.model.enums import EquipmentSlot
        from .skill_leases import leases,begin_lease
        from .zhangliao import borrowable
        a=f.action;pid=a.player_id;target=a.opponent_id;p=state.players[pid]
        if target not in state.players or not state.players[target].is_alive or pid==target or pid in leases(state):return StepResult.complete()
        eligible=borrowable(state,target,self.skills)
        if not eligible:return StepResult.complete()
        if f.step_index==0:
            if state.current_player_id!=pid or state.current_phase is not Phase.PLAY:return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【夺锐】是否废除一个装备栏并借用该角色的技能？',subject_player_id=target)
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            slots=tuple(slot.value for slot in EquipmentSlot if slot not in p.abolished_equipment_slots)
            f.step_index=2
            if slots:return self.ask(f,RequestType.CHOOSE_OPTION,'【夺锐】选择废除的装备栏',choices=slots)
            f.decision=None
        if f.step_index==2:
            choice,f.decision=f.decision,None
            if choice is not None:
                slot=EquipmentSlot(choice);p.abolished_equipment_slots.add(slot)
                cards=state.cards_in(ZoneRef(ZoneType.EQUIPMENT,pid,slot))
                if cards:self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
                self.moves.recorder.record(Event(a.action_id+':abolished','equipment_slot_abolished',pid,metadata={'slot':slot.value}))
            f.step_index=3
            return StepResult.continue_()
        if f.step_index==3:
            f.step_index=4
            return self.ask(f,RequestType.CHOOSE_OPTION,'【夺锐】选择借用的技能',choices=eligible,subject_player_id=target)
        skill,f.decision=f.decision,None
        if skill in eligible:
            begin_lease(state,pid,target,skill)
            self.moves.recorder.record(Event(a.action_id+':borrowed','skill_borrowed',pid,(target,),metadata={'skill_id':skill}))
        return StepResult.complete()

    def zhiti_restore(self,state,f):
        from sanguosha.model.enums import EquipmentSlot
        a=f.action;pid=a.player_id;p=state.players[pid]
        slots=tuple(slot.value for slot in EquipmentSlot if slot in p.abolished_equipment_slots)
        if not slots:return StepResult.complete()
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_OPTION,'【止啼】选择恢复一个装备栏',choices=slots)
        choice,f.decision=f.decision,None
        p.abolished_equipment_slots.discard(EquipmentSlot(choice))
        self.moves.recorder.record(Event(a.action_id+':restored','equipment_slot_restored',pid,metadata={'slot':choice}))
        return StepResult.complete()

    def longnu(self,state,f):
        from .hp import LoseHpAction,LoseMaxHpAction
        from .deck import DrawCardsAction
        a=f.action;pid=a.player_id;p=state.players[pid]
        if f.step_index==0:
            active=2 if p.marks.get('longnu_next')==2 else 1
            f.local['form']=active;p.marks['longnu_next']=1 if active==2 else 2
            p.marks.pop('longnu_form',None);f.step_index=1
            return StepResult.push((LoseHpAction if active==1 else LoseMaxHpAction)(a.action_id+':cost',pid,1))
        if f.step_index==1:
            f.step_index=2
            return StepResult.push(DrawCardsAction(a.action_id+':draw',pid,1))
        p.marks['longnu_form']=f.local['form']
        return StepResult.complete()

    def jieying_liubei(self,state,f):
        from .chaining import set_chained
        a=f.action;pid=a.player_id
        targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive and not state.players[q].chained)
        if f.step_index==0:
            set_chained(state,pid,True,self.skills)
            if not targets:return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【结营】选择一名其他未连环角色',allowed_player_ids=targets,min_count=1,max_count=1)
        target,f.decision=f.decision,None
        if target in targets:
            set_chained(state,target,True,self.skills)
            self.moves.recorder.record(Event(a.action_id+':chain','player_chained',pid,(target,),metadata={'skill_id':'jieying_liubei'}))
        return StepResult.complete()

    def validate_start(self,state,a):
        if a.skill in ('poxi','zhanhuo'):
            if not self.skills.has(state,a.player_id,a.skill):raise InvalidCardUse('角色不具有该技能')
            if state.current_player_id!=a.player_id or state.current_phase is not Phase.PLAY:raise InvalidCardUse('技能仅出牌阶段使用')
            if a.skill=='poxi':
                from .yj2011_tier3 import hand
                if state.play_usage is None or state.play_usage.count('skill.poxi') or not any(q!=a.player_id and state.players[q].is_alive and hand(state,q) for q in state.seat_order):raise InvalidCardUse('魄袭次数或目标不合法')
            else:
                p=state.players[a.player_id]
                if p.marks.get('zhanhuo_used') or p.marks.get('junlve',0)<=0 or not any(q.is_alive and q.chained for q in state.players.values()):raise InvalidCardUse('绽火次数、军略或目标不合法')

    def step(self,state,f):
        a=f.action
        if a.skill=='poxi' and (not state.players[a.player_id].is_alive or not self.skills.has(state,a.player_id,'poxi')):
            state.metadata.pop('poxi_reveal',None)
            return StepResult.complete()
        if not self.skills.has(state,a.player_id,'jieying_ganning' if a.skill in ('camptransfer','campend') else 'zhiti' if a.skill=='zhiti_restore' else a.skill):
            if a.skill=='zhanhuo' and f.step_index==0:raise InvalidCardUse('角色不具有绽火')
            return StepResult.complete()
        return super().step(state,f)

    def camptransfer(self,state,f):
        a=f.action;pid=a.player_id
        if not state.players[pid].marks.get('camp'):return StepResult.complete()
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【劫营】是否将营标记交给一名其他角色？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive)
            if not targets:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【劫营】选择获得营标记的角色',allowed_player_ids=targets,min_count=1,max_count=1)
        target,f.decision=f.decision,None
        clear_camp(state,pid)
        state.players[target].marks['camp']=1
        state.metadata.setdefault('camp_sources',{})[target]=pid
        return StepResult.complete()

    def campend(self,state,f):
        from .yj2011_tier3 import hand
        a=f.action;holder=a.opponent_id
        if holder not in state.players or not state.players[holder].marks.get('camp'):return StepResult.complete()
        clear_camp(state,holder)
        cards=hand(state,holder)
        if cards:self.transfer(state,a,cards,ZoneRef(ZoneType.HAND,a.player_id),actor=a.player_id)
        return StepResult.complete()

    def poxi(self,state,f):
        from .yj2011_tier3 import hand
        from .suits import effective_suit
        from .hp import LoseMaxHpAction
        from .recovery import RecoverAction
        from .deck import DrawCardsAction
        a=f.action;pid=a.player_id;p=state.players[pid]
        if f.step_index==0:
            self.validate_active(state,a)
            targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive and hand(state,q))
            if not targets:raise InvalidCardUse('魄袭没有可观看的手牌')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【魄袭】观看一名其他角色的手牌',allowed_player_ids=targets,min_count=1,max_count=1)
        if f.step_index==1:
            target,f.decision=f.decision,None;f.local['target']=target
            state.play_usage.record('skill.poxi')
            state.metadata['poxi_reveal']={'actor':pid,'target':target}
            cards=(*hand(state,pid),*hand(state,target))
            groups={}
            for cid in cards:groups.setdefault(effective_suit(state,cid),[]).append(cid)
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_CARDS,'【魄袭】弃置你与其手牌中四张花色各异的牌，或空选放弃',eligible_card_ids=cards,min_count=0,max_count=4,minimum_nonempty_count=4,exclusive_card_groups=tuple(tuple(ids) for ids in groups.values()),subject_player_id=target)
        if f.step_index==2:
            cards,f.decision=tuple(f.decision),None
            state.metadata.pop('poxi_reveal',None)
            if not cards:return StepResult.complete()
            n=sum(c in hand(state,pid) for c in cards);f.local['n']=n
            self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            f.step_index=3
            return StepResult.continue_()
        n=f.local['n']
        if f.step_index==3:
            f.step_index=4
            if n==0:return StepResult.push(LoseMaxHpAction(a.action_id+':maxhp',pid,1))
            if n==1:
                p.marks['poxi_end_play']=1;p.marks['poxi_hand_limit']=state.turn_number
            if n==3:return StepResult.push(RecoverAction(a.action_id+':recover',pid,pid,1))
            if n==4:return StepResult.push(DrawCardsAction(a.action_id+':draw',pid,4))
        return StepResult.complete()

    def cuike(self,state,f):
        a=f.action;pid=a.player_id
        if state.status.value == "finished" or not state.players[pid].is_alive:
            return StepResult.complete()
        if f.step_index==0:
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【摧克】是否对一名角色造成伤害，或横置并弃牌？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if wanted:
                f.step_index=2
                return self.ask(f,RequestType.CHOOSE_PLAYER,'【摧克】选择角色',allowed_player_ids=tuple(q for q in state.seat_order if state.players[q].is_alive),min_count=1,max_count=1)
            f.step_index=4
        if f.step_index==2:
            target,f.decision=f.decision,None;f.local['target']=target
            f.step_index=4
            if state.players[pid].marks.get('junlve',0)%2:
                return StepResult.push(MilitaryDamageAction(a.action_id+':odd',pid,target,1))
            state.players[target].chained=True
            self.moves.recorder.record(Event(a.action_id+':chain','player_chained',target,metadata={'chained':True}))
            cards=region(state,target)
            if cards:
                f.step_index=3
                return self.ask(f,RequestType.CHOOSE_CARD,'【摧克】弃置目标区域内一张牌',eligible_card_ids=cards,subject_player_id=target)
        if f.step_index==3:
            card,f.decision=f.decision,None
            self.transfer(state,a,(card,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            f.step_index=4
            return StepResult.continue_()
        if f.step_index==4:
            if state.players[pid].marks.get('junlve',0)<=7:return StepResult.complete()
            f.step_index=5
            return self.ask(f,RequestType.YES_NO,'【摧克】是否移去全部军略，对所有其他角色各造成一点伤害？')
        if f.step_index==5:
            wanted,f.decision=f.decision is True,None
            if not wanted:return StepResult.complete()
            state.players[pid].marks['junlve']=0
            start=state.seat_order.index(pid)
            f.local['targets']=tuple(q for q in state.seat_order[start+1:]+state.seat_order[:start] if q!=pid)
            f.step_index=6
        targets=f.local['targets']
        while f.cursor<len(targets) and not state.players[targets[f.cursor]].is_alive:f.cursor+=1
        if f.cursor>=len(targets):return StepResult.complete()
        target=targets[f.cursor];f.cursor+=1
        return StepResult.push(MilitaryDamageAction(a.action_id+':burst:'+target,pid,target,1))

    def zhanhuo(self,state,f):
        a=f.action;pid=a.player_id;p=state.players[pid]
        if f.step_index==0:
            if state.current_player_id!=pid or state.current_phase is not Phase.PLAY or p.marks.get('zhanhuo_used') or p.marks.get('junlve',0)<=0:raise InvalidCardUse('绽火时机、次数或军略不合法')
            targets=tuple(q for q in state.seat_order if state.players[q].is_alive and state.players[q].chained)
            if not targets:raise InvalidCardUse('绽火需要已横置的目标')
            f.step_index=1
            return self.ask(f,RequestType.CHOOSE_PLAYERS,'【绽火】选择至多军略数量的已横置角色',allowed_player_ids=targets,min_count=1,max_count=min(len(targets),p.marks['junlve']))
        if f.step_index==1:
            selected,f.decision=tuple(f.decision),None
            f.local['targets']=tuple(q for q in state.seat_order if q in selected)
            p.marks['zhanhuo_used']=1;p.marks['junlve']=0;f.step_index=2
        targets=f.local['targets']
        if f.step_index==2:
            if f.cursor<len(targets):
                target=targets[f.cursor];f.cursor+=1
                cards=tuple(c for ref,z in state.zones.items() if ref.player_id==target and ref.zone_type is ZoneType.EQUIPMENT for c in z.card_ids)
                if state.players[target].is_alive and cards:self.transfer(state,a,cards,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,actor=target)
                return StepResult.continue_()
            living=tuple(q for q in targets if state.players[q].is_alive)
            if not living:return StepResult.complete()
            f.step_index=3
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【绽火】对其中一名角色造成一点火焰伤害',allowed_player_ids=living,min_count=1,max_count=1)
        if f.step_index==3:
            target,f.decision=f.decision,None;f.step_index=4
            return StepResult.push(MilitaryDamageAction(a.action_id+':fire',pid,target,1,DamageNature.FIRE))
        return StepResult.complete()


def play_options(state,pid,skills):
    p=state.players[pid]
    from .yj2011_tier3 import hand
    options=['skill:poxi'] if skills.has(state,pid,'poxi') and state.play_usage is not None and not state.play_usage.count('skill.poxi') and any(q!=pid and state.players[q].is_alive and hand(state,q) for q in state.seat_order) else []
    return options + (['skill:zhanhuo'] if (skills.has(state,pid,'zhanhuo') and p.marks.get('junlve',0)>0
        and not p.marks.get('zhanhuo_used') and any(q.is_alive and q.chained for q in state.players.values())) else [])


def register(registry,skills,moves,definitions,deck):
    registry.register(RemainingGodAction,RemainingGodHandler(skills,moves,definitions,deck))

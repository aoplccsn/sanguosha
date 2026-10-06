"""Physical equipment loss reactions and explicit weapon choices."""
from dataclasses import dataclass
from .actions import Action,StepResult
from .card_moves import CardMoveService,CardMove,CardMoveReason
from .requests import PendingRequest,RequestType
from .recovery import RecoverAction
from .deck import DrawCardsAction
from sanguosha.model.enums import EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType

class MilitaryMoveService(CardMoveService):
    def __init__(self,events,skills=None):
        super().__init__(events)
        self.reactions=[]
        self.skills=skills
    def _departure_facts(self,state,move):
        owner=move.from_zone.player_id
        lost_last_hand=(move.from_zone.zone_type is ZoneType.HAND and owner is not None
                        and self.skills is not None and self.skills.has(state,owner,'lianying')
                        and len(state.cards_in(move.from_zone))==len(move.card_ids))
        lost_equipment=(move.from_zone.zone_type is ZoneType.EQUIPMENT and owner is not None
                        and self.skills is not None and self.skills.has(state,owner,'xiaoji'))
        silver=move.from_zone.zone_type is ZoneType.EQUIPMENT and any(
            state.cards[cid].definition_id=='equipment.armor.silver_lion' for cid in move.card_ids)
        return owner, lost_last_hand, lost_equipment, silver
    def move(self,state,move):
        facts=self._departure_facts(state,move)
        owner=move.from_zone.player_id
        if (move.reason is CardMoveReason.DISCARD and move.to_zone.zone_type is ZoneType.DISCARD_PILE
                and move.from_zone.zone_type in (ZoneType.HAND,ZoneType.EQUIPMENT)
                and owner is not None and state.players[owner].is_alive
                and self.skills is not None and self.skills.has(state,owner,'zongxuan')):
            from dataclasses import replace
            from .zongxuan import PendingDiscard
            # Reserve the outgoing cards, before publishing any discard or loss reaction.
            # The original move and departure facts resume on the ordinary reaction stack.
            super().move(state,replace(move,move_id=move.move_id+':reserved',to_zone=ZoneRef(ZoneType.SPECIAL,owner,special_key='committed:zongxuan:'+move.move_id),reason=CardMoveReason.SYSTEM,related_action_id=None,triggers_rules=False))
            index=next((i for i,x in enumerate(self.reactions) if not isinstance(x,PendingDiscard)),len(self.reactions))
            self.reactions.insert(index,PendingDiscard(move.move_id+':zongxuan',owner,move,facts))
            return
        super().move(state,move)
        self._after_departure(state,move,facts)
    def _after_departure(self,state,move,facts):
        owner,lost_last_hand,lost_equipment,silver=facts
        if silver and state.players[owner].is_alive:
            self.reactions.append(RecoverAction(move.move_id+':silver-lion-loss',owner,owner,1))
        if lost_last_hand and state.players[owner].is_alive:
            from .skills import LianyingAction
            self.reactions.append(LianyingAction(move.move_id+':lianying',owner))
        if lost_equipment and state.players[owner].is_alive:
            from .skills import XiaojiAction
            self.reactions.append(XiaojiAction(move.move_id+':xiaoji',owner,len(move.card_ids)))
        if (owner is not None and move.from_zone.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                and (state.current_player_id != owner or state.current_phase is None)
                and not (move.to_zone.player_id == owner
                    and move.to_zone.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT))
                and state.players[owner].is_alive
                and self.skills is not None and self.skills.has(state, owner, 'tuntian')):
            from .mountain import TuntianAction
            self.reactions.append(TuntianAction(move.move_id + ':tuntian', owner))
    def next_reaction(self,state):
        from sanguosha.model.state import GameStatus
        if state.status is GameStatus.FINISHED:
            self.reactions.clear()
            state.metadata['reaction_event_cursor']=len(self.recorder.events)
            return None
        cursor = state.metadata.get('reaction_event_cursor', 0)
        from .events import CardMovedEvent
        new_events = [event for event in self.recorder.events[cursor:]
                      if not isinstance(event, CardMovedEvent) or event.triggers_rules]
        from .qiaoshui import before_reactions
        window,blocked=before_reactions(state,new_events,self.skills,getattr(self,'definitions',None))
        if blocked:return window
        state.metadata['reaction_event_cursor'] = len(self.recorder.events)
        if self.skills is not None:
            from .events import CardUsedEvent, AfterDamageEvent
            from .suits import effective_color
            from sanguosha.model.enums import Color
            from .mountain import JiangAction, XinshengAction, BeigeAction
            for event in new_events:
                if isinstance(event,CardUsedEvent):
                    from dataclasses import replace
                    targets=state.metadata.get('qiaoshui_targets',{}).get(event.event_id.removesuffix(':used'))
                    if targets is not None:event=replace(event,target_ids=tuple(targets))
                from .zhangliao import event_reactions as zhangliao_event_reactions
                self.reactions.extend(zhangliao_event_reactions(state,event,self.skills,getattr(self,'definitions',None)))
                from .yj2013 import event_reactions as yj2013_event_reactions
                self.reactions.extend(yj2013_event_reactions(state,event,self.skills))
                from .yj2011 import event_reactions
                self.reactions.extend(event_reactions(state, event, self.skills, self.recorder))
                from .yj2011_tier3 import reactions
                self.reactions.extend(reactions(state, event, self.skills))
                if isinstance(event, AfterDamageEvent):
                    if (event.source_id is not None and event.source_id != event.target_id
                            and state.players[event.target_id].is_alive
                            and self.skills.has(state, event.target_id, 'wuhun')):
                        source = state.players[event.source_id]
                        source.marks['nightmare'] = source.marks.get('nightmare', 0) + event.amount
                    if (state.players[event.target_id].is_alive
                            and self.skills.has(state, event.target_id, 'xinsheng')):
                        self.reactions.append(XinshengAction(
                            event.event_id + ':xinsheng', event.target_id, event.amount))
                    if event.card_kind == 'slash':
                        for pid in state.seat_order:
                            if (pid != event.target_id and state.players[pid].is_alive
                                    and self.skills.has(state, pid, 'beige')):
                                self.reactions.append(BeigeAction(
                                    event.event_id + ':beige:' + pid, pid,
                                    event.target_id, event.source_id))
                    continue
                if not isinstance(event, CardUsedEvent):
                    continue
                definition = event.virtual_definition_id or state.cards[event.card_id].definition_id
                if (definition != 'trick.duel'
                        and (definition not in ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash')
                             or event.card_id not in state.cards
                             or effective_color(state, event.card_id, event.player_id) is not Color.RED)):
                    continue
                for pid in dict.fromkeys((event.player_id, *event.target_ids)):
                    if state.players[pid].is_alive and self.skills.has(state, pid, 'jiang'):
                        self.reactions.append(JiangAction(event.event_id + ':jiang:' + pid, pid))
        while self.reactions:
            action=self.reactions.pop(0)
            target=(getattr(action,'target_id',None) or getattr(action,'player_id',None)
                    or getattr(action,'owner_id',None))
            from .zongxuan import PendingDiscard
            if isinstance(action,PendingDiscard) or target is not None and state.players[target].is_alive:
                return action
        return None

def discardable(state,pid):
    return tuple(cid for ref,z in state.zones.items() if ref.player_id==pid and ref.zone_type in (ZoneType.HAND,ZoneType.EQUIPMENT) for cid in z.card_ids)

@dataclass(frozen=True,slots=True)
class WeaponChoice(Action):
    owner_id: str
    target_id: str
    weapon: str

class WeaponChoiceHandler:
    def __init__(self,moves):
        self.moves=moves
    def step(self,state,f):
        a=f.action
        if a.weapon=='double_sword':
            if f.step_index==0:
                f.step_index=1
                choices=('draw', 'discard') if state.cards_in(ZoneRef(ZoneType.HAND,a.target_id)) else ('draw',)
                return StepResult.ask(PendingRequest(a.action_id+':option',a.target_id,RequestType.CHOOSE_OPTION,
                    '雌雄双股剑：弃一张手牌或令使用者摸牌',a.action_id,f.frame_id,choices=choices))
            if f.step_index==1:
                choice=f.decision
                f.decision=None
                f.step_index=2
                if choice=='draw':
                    return StepResult.push(DrawCardsAction(a.action_id+':draw',a.owner_id,1))
                return StepResult.ask(PendingRequest(a.action_id+':discard',a.target_id,RequestType.CHOOSE_CARD,
                    '雌雄双股剑：选择弃牌',a.action_id,f.frame_id,
                    eligible_card_ids=state.cards_in(ZoneRef(ZoneType.HAND,a.target_id))))
            if f.decision is not None:
                cid=f.decision
                f.decision=None
                self.moves.move(state,CardMove(a.action_id+':move',(cid,),ZoneRef(ZoneType.HAND,a.target_id),
                    ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,a.target_id))
            return StepResult.complete()
        if a.weapon=='ice_sword':
            if not state.players[a.target_id].is_alive or not state.players[a.owner_id].is_alive:
                return StepResult.complete()
            if f.step_index==1:
                cid=f.decision;f.decision=None
                ref=next(ref for ref,z in state.zones.items() if cid in z.card_ids)
                self.moves.move(state,CardMove(a.action_id+':move:'+str(f.cursor),(cid,),ref,
                    ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,a.owner_id))
                f.cursor+=1;f.step_index=0
                return StepResult.continue_()
            cards=discardable(state,a.target_id)
            if f.cursor>=2 or not cards:return StepResult.complete()
            f.step_index=1
            return StepResult.ask(PendingRequest(a.action_id+':card:'+str(f.cursor),a.owner_id,RequestType.CHOOSE_CARD,
                '\u5bd2\u51b0\u5251\uff1a\u5f03\u7f6e\u76ee\u6807\u4e00\u5f20\u724c',a.action_id,f.frame_id,
                eligible_card_ids=cards,subject_player_id=a.target_id))
        if f.step_index==0:
            cards=discardable(state,a.target_id)
            if a.weapon=='kylin_bow':
                cards=tuple(cid for ref,z in state.zones.items() if ref.player_id==a.target_id and ref.equipment_slot in
                    (EquipmentSlot.OFFENSIVE_HORSE,EquipmentSlot.DEFENSIVE_HORSE) for cid in z.card_ids)
            count=min(2,len(cards)) if a.weapon=='ice_sword' else 1
            if not cards:
                return StepResult.complete()
            f.step_index=1
            return StepResult.ask(PendingRequest(a.action_id+':cards',a.owner_id,RequestType.CHOOSE_CARDS,
                '寒冰剑：弃置目标两张牌' if a.weapon=='ice_sword' else '麒麟弓：弃置目标一张马',
                a.action_id,f.frame_id,eligible_card_ids=cards,min_count=count,max_count=count,subject_player_id=a.target_id))
        for cid in f.decision:
            ref=next(ref for ref,z in state.zones.items() if cid in z.card_ids)
            self.moves.move(state,CardMove(a.action_id+':move:'+cid,(cid,),ref,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,a.owner_id))
        f.decision=None
        return StepResult.complete()



def axe_materials(state,pid):
    """Axe's own equipped physical card cannot pay its two-card cost."""
    axe=state.cards_in(ZoneRef(ZoneType.EQUIPMENT,pid,EquipmentSlot.WEAPON))
    return tuple(cid for cid in discardable(state,pid) if cid not in axe)

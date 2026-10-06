"""Next-card target adjustment shared by physical and virtual card effects."""
from dataclasses import dataclass
from .actions import Action,StepResult
from .requests import PendingRequest,RequestType
from .events import CardUsedEvent,CardRespondedEvent,VirtualResponseEvent,TrickTargetsDeclaredEvent
from sanguosha.model.enums import Phase

GLOBAL=('trick.savage_assault','trick.archery_attack','trick.god_salvation','trick.amazing_grace')
SELF=('basic.peach','basic.wine','trick.ex_nihilo')

def prohibited(state,pid,definition):
    return state.players[pid].marks.get('qiaoshui_trick_lock')==state.turn_number and (definition.startswith('trick.') or definition.startswith('delayed.'))

def declared_targets(state,event,definition):
    if definition in SELF:return (event.player_id,)
    if definition in GLOBAL:
        index=state.seat_order.index(event.player_id);order=state.seat_order[index:]+state.seat_order[:index]
        return tuple(q for q in order if state.players[q].is_alive and (q!=event.player_id or definition not in GLOBAL[:2]))
    return event.target_ids

def take_targets(state,action_id,default):
    overrides=state.metadata.get('qiaoshui_targets',{})
    key=next((k for k in overrides if action_id.startswith(k+':')),None)
    return tuple(overrides.pop(key)) if key else tuple(default)

@dataclass(frozen=True,slots=True)
class QiaoshuiTargets(Action):
    player_id: str
    event: CardUsedEvent
    definition: str

class QiaoshuiTargetsHandler:
    def __init__(self,skills,definitions,recorder):self.skills,self.definitions,self.recorder=skills,definitions,recorder
    def extra(self,state,a,targets):
        from .fuhuanghou import target_allowed
        from .military_tricks import MilitaryTrickRule
        from .forest import weimu_blocks
        from .yj2011_tier3 import hand
        from .distance import DistanceSystem
        class UnlimitedDistance(DistanceSystem):
            def distance_between(self,state,source,target):return 1
        definition=a.definition;pid=a.player_id
        if definition in GLOBAL:return ()
        if definition.startswith('trick.'):
            candidates=MilitaryTrickRule(definition,UnlimitedDistance(self.definitions),self.skills).target_candidates(state,pid) if definition not in SELF else state.seat_order
        else:candidates=state.seat_order
        return tuple(q for q in candidates if q not in targets and state.players[q].is_alive
            and target_allowed(state,pid,q)
            and (state.players[pid].marks.get('yj_zishou')!=state.turn_number or q==pid)
            and (definition not in ('basic.slash','basic.fire_slash','basic.thunder_slash') or q!=pid and not (self.skills.has(state,q,'kongcheng') and not hand(state,q)))
            and (definition!='basic.peach' or state.players[q].hp<state.players[q].max_hp)
            and not weimu_blocks(state,q,a.event.card_id,definition,pid,self.skills,a.event.virtual_card))
    def ask(self,f,kind,prompt,**kw):
        return StepResult.ask(PendingRequest(f.action.action_id+':'+str(f.step_index),f.action.player_id,kind,prompt,f.action.action_id,f.frame_id,**kw))
    def step(self,state,f):
        a=f.action;targets=declared_targets(state,a.event,a.definition)
        if f.step_index==0:
            extra=self.extra(state,a,targets);f.local['extra']=extra;f.local['targets']=targets
            choices=('cancel',)+(('add',) if extra else ())+ (('remove',) if len(targets)>1 else ())
            f.step_index=1
            if len(choices)>1:return self.ask(f,RequestType.CHOOSE_OPTION,'【巧说】增加或减少此牌的一个目标，或放弃',choices=choices)
            f.decision='cancel'
        if f.step_index==1:
            mode,f.decision=f.decision,None;f.local['mode']=mode
            if mode!='cancel':
                f.step_index=2
                return self.ask(f,RequestType.CHOOSE_PLAYER,f'【巧说】选择新增目标（无距离限制）〔{self.definitions.get(a.definition).name}〕' if mode=='add' else f'【巧说】选择移除目标〔{self.definitions.get(a.definition).name}〕',allowed_player_ids=f.local['extra'] if mode=='add' else targets)
        elif f.step_index==2:
            target,f.decision=f.decision,None
            if f.local['mode']=='remove':targets=tuple(q for q in targets if q!=target)
            else:
                index=state.seat_order.index(a.player_id);order=state.seat_order[index:]+state.seat_order[:index]
                targets=tuple(q for q in order if q in (*targets,target))
            root=a.event.event_id.removesuffix(':used')
            state.metadata.setdefault('qiaoshui_targets',{})[root]=targets
            self.recorder.record(TrickTargetsDeclaredEvent(root+':qiaoshui-targets',a.player_id,a.event.card_id,a.definition,targets))
        state.metadata.pop('qiaoshui_pending',None)
        return StepResult.complete()

def before_reactions(state,events,skills,definitions):
    if state.metadata.get('qiaoshui_pending'):return None,True
    for event in events:
        if isinstance(event,(CardRespondedEvent,VirtualResponseEvent)) and event.response_definition_id in ('basic.peach','basic.wine','trick.nullification'):
            # Rescue and counter cards are uses; ordinary Slash/Dodge responses are not.
            if state.players[event.player_id].marks.get('qiaoshui_success')==state.turn_number:
                state.players[event.player_id].marks.pop('qiaoshui_success',None)
            continue
        if not isinstance(event,CardUsedEvent):continue
        p=state.players[event.player_id]
        if p.marks.get('qiaoshui_success')!=state.turn_number:continue
        definition=event.virtual_definition_id or state.cards[event.card_id].definition_id
        if not (definition.startswith('basic.') or definition.startswith('trick.')):continue
        if definition=='trick.iron_chain' and not event.target_ids:continue
        p.marks.pop('qiaoshui_success',None)
        if state.current_player_id!=event.player_id or state.current_phase is not Phase.PLAY:continue
        # An iron-chain recast has no target and is not a use.
        if definition=='trick.iron_chain' and not event.target_ids:continue
        state.metadata['qiaoshui_pending']=event.event_id
        return QiaoshuiTargets(event.event_id+':qiaoshui',event.player_id,event,definition),True
    return None,False

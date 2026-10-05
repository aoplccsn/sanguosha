"""YJ2013 actions on the shared resumable resolution stack."""
from dataclasses import dataclass
from .actions import Action, StepResult
from .deck import DrawCardsAction
from .events import CardUsedEvent, TurnStartedEvent
from .requests import RequestType
from .yj2011_tier3 import YJSkillHandler

@dataclass(frozen=True, slots=True)
class YJ2013Action(Action):
    player_id: str
    skill: str
    opponent_id: str | None = None

def cards_used_this_turn(events, player_id):
    count = 0
    for event in reversed(events):
        if isinstance(event, TurnStartedEvent):
            break
        if isinstance(event, CardUsedEvent) and event.player_id == player_id:
            count += 1
    return count

class YJ2013Handler(YJSkillHandler):
    def step(self, state, frame):
        action = frame.action
        if not state.players[action.player_id].is_alive or not self.skills.has(state, action.player_id, action.skill):
            return StepResult.complete()
        return super().step(state,frame)

    def juece(self,state,f):
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .military_basics import MilitaryDamageAction
        a=f.action; pid=a.player_id
        targets=tuple(q for q in state.seat_order if q!=pid and state.players[q].is_alive
            and not state.cards_in(ZoneRef(ZoneType.HAND,q)))
        if f.step_index==0:
            if not targets: return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【绝策】是否对无手牌角色造成一点伤害？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted or not targets:return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_PLAYER,'【绝策】选择无手牌目标',allowed_player_ids=targets)
        if f.step_index==2:
            target,f.decision=f.decision,None
            if target not in targets: return StepResult.complete()
            f.step_index=3
            return StepResult.push(MilitaryDamageAction(a.action_id+':damage',pid,target,1))
        return StepResult.complete()

    def duodao(self,state,f):
        from sanguosha.model.enums import EquipmentSlot
        from sanguosha.model.zones import ZoneRef, ZoneType
        from .card_moves import CardMoveReason
        from .military_equipment import discardable
        a=f.action; pid=a.player_id; source=a.opponent_id
        def weapon():
            return state.cards_in(ZoneRef(ZoneType.EQUIPMENT,source,EquipmentSlot.WEAPON)) if source in state.players and state.players[source].is_alive else ()
        if f.step_index==0:
            costs=discardable(state,pid)
            if not costs or not weapon(): return StepResult.complete()
            f.step_index=1
            return self.ask(f,RequestType.YES_NO,'【夺刀】是否弃一张牌获得伤害来源的武器？')
        if f.step_index==1:
            wanted,f.decision=f.decision is True,None
            if not wanted or not weapon(): return StepResult.complete()
            f.step_index=2
            return self.ask(f,RequestType.CHOOSE_CARD,'【夺刀】选择弃牌成本',eligible_card_ids=discardable(state,pid))
        if f.step_index==2:
            cost,f.decision=f.decision,None
            self.transfer(state,a,(cost,),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD)
            f.step_index=3
            return StepResult.continue_()
        cards=weapon()
        if cards: self.transfer(state,a,cards,ZoneRef(ZoneType.HAND,pid))
        return StepResult.complete()

    def jingce(self,state,frame):
        action=frame.action
        if frame.step_index == 0:
            if cards_used_this_turn(self.moves.recorder.events, action.player_id) < state.players[action.player_id].hp:
                return StepResult.complete()
            frame.step_index = 1
            return self.ask(frame, RequestType.YES_NO, '【精策】是否摸两张牌？')
        if frame.step_index == 1:
            wanted, frame.decision = frame.decision is True, None
            frame.step_index = 2
            if wanted:
                return StepResult.push(DrawCardsAction(action.action_id + ':draw', action.player_id, 2))
        return StepResult.complete()

def register(registry, skills, moves, definitions, deck):
    registry.register(YJ2013Action, YJ2013Handler(skills, moves, definitions, deck))


def damage_reaction(state,frame,skills):
    a=frame.action
    if (frame.step_index==1 and not frame.local.get('yj2013_duodao') and skills is not None
            and state.players[a.target_id].is_alive and getattr(a,'card_kind','')=='slash'
            and skills.has(state,a.target_id,'duodao')):
        frame.local['yj2013_duodao']=True
        return StepResult.push(YJ2013Action(a.action_id+':duodao',a.target_id,'duodao',a.source_id))
    return None

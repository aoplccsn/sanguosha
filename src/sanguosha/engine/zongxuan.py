"""Before-discard selection on the existing move/reaction stack."""
from dataclasses import dataclass,replace
from .actions import Action,StepResult
from .card_moves import CardMoveService,CardMoveReason
from .events import CardMovedEvent, Event
from .requests import PendingRequest,RequestType
from sanguosha.model.zones import ZoneRef,ZoneType

@dataclass(frozen=True,slots=True)
class PendingDiscard(Action):
    player_id: str
    move: object
    departure_facts: tuple

class PendingDiscardHandler:
    def __init__(self,moves,skills):self.moves,self.skills=moves,skills
    def step(self,state,f):
        a=f.action;move=a.move
        if f.step_index==0:
            f.step_index=1
            if state.players[a.player_id].is_alive and self.skills.has(state,a.player_id,'zongxuan'):
                return StepResult.ask(PendingRequest(a.action_id+':cards',a.player_id,RequestType.CHOOSE_CARDS,
                    '【纵玄】依次选择要置于牌堆顶的牌，最后一张在最上方（可空选）',a.action_id,f.frame_id,
                    eligible_card_ids=move.card_ids,min_count=0,max_count=len(move.card_ids),subject_player_id=a.player_id))
            f.decision=()
        selected,f.decision=tuple(f.decision or ()),None
        source=ZoneRef(ZoneType.SPECIAL,a.player_id,special_key='committed:zongxuan:'+move.move_id)
        for index,cid in enumerate(selected):
            CardMoveService.move(self.moves,state,replace(move,move_id=move.move_id+':top:'+str(index),
                card_ids=(cid,),from_zone=source,to_zone=ZoneRef(ZoneType.DRAW_PILE),to_top=True,triggers_rules=False))
            self.moves.recorder.record(CardMovedEvent(move.move_id+':top-fact:'+str(index),
                (cid,),move.from_zone,ZoneRef(ZoneType.DRAW_PILE),move.reason.value,move.actor_id,move.related_action_id))
            self.moves.recorder.record(Event(move.move_id+':top-reveal:'+str(index),
                'card_revealed',a.player_id,metadata={'card_id':cid,'skill_id':'zongxuan','reason':'top'}))
        remaining=tuple(c for c in move.card_ids if c not in selected)
        if remaining:
            # Publish only the final discard, with its original source and reason.
            CardMoveService.move(self.moves,state,replace(move,move_id=move.move_id+':commit',card_ids=remaining,from_zone=source,reason=CardMoveReason.SYSTEM,related_action_id=None,triggers_rules=False))
            self.moves.recorder.record(CardMovedEvent(move.move_id,remaining,move.from_zone,move.to_zone,move.reason.value,move.actor_id,move.related_action_id))
        self.moves._after_departure(state,move,a.departure_facts)
        return StepResult.complete()

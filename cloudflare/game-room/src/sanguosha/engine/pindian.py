"""Reusable authoritative pindian with two private selections and one public reveal."""
from dataclasses import dataclass
from sanguosha.model.zones import ZoneRef, ZoneType
from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .card_rules import InvalidCardUse
from .events import Event
from .requests import PendingRequest, RequestType

@dataclass(frozen=True, slots=True)
class PindianAction(Action):
    source_id: str
    opponent_id: str

class PindianHandler:
    def __init__(self, moves, events):
        self.moves, self.events = moves, events

    def _hand(self, state, player_id):
        return state.cards_in(ZoneRef(ZoneType.HAND, player_id))

    def validate_start(self, state, action):
        if (action.source_id == action.opponent_id
                or not state.players[action.source_id].is_alive
                or not state.players[action.opponent_id].is_alive
                or not self._hand(state, action.source_id)
                or not self._hand(state, action.opponent_id)):
            raise InvalidCardUse('拼点双方必须存活且各有手牌')

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            self.validate_start(state, action)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(action.action_id + ':source', action.source_id,
                RequestType.CHOOSE_CARD, '拼点：选择一张手牌', action.action_id, frame.frame_id,
                eligible_card_ids=self._hand(state, action.source_id)))
        if frame.step_index == 1:
            card_id = frame.decision
            frame.decision = None
            if card_id not in self._hand(state, action.source_id):
                raise InvalidCardUse('拼点牌已不可用')
            frame.local['source_card'] = card_id
            frame.step_index = 2
            return StepResult.ask(PendingRequest(action.action_id + ':opponent', action.opponent_id,
                RequestType.CHOOSE_CARD, '拼点：选择一张手牌', action.action_id, frame.frame_id,
                eligible_card_ids=self._hand(state, action.opponent_id)))
        processing=ZoneRef(ZoneType.PROCESSING)
        if frame.step_index==2:
            self.validate_start(state, action)
            source_card,opponent_card=frame.local['source_card'],frame.decision
            frame.decision=None
            if source_card not in self._hand(state,action.source_id) or opponent_card not in self._hand(state,action.opponent_id):
                raise InvalidCardUse('拼点牌已不可用')
            frame.local['opponent_card']=opponent_card
            for player_id,card_id in ((action.source_id,source_card),(action.opponent_id,opponent_card)):
                self.moves.move(state,CardMove(action.action_id+':reveal:'+player_id,(card_id,),ZoneRef(ZoneType.HAND,player_id),processing,CardMoveReason.SYSTEM,player_id))
            source_rank,opponent_rank=state.cards[source_card].rank,state.cards[opponent_card].rank
            frame.local['source_win']=source_rank>opponent_rank
            self.events.record(Event(action.action_id+':shown','pindian_revealed',action.source_id,(action.opponent_id,),
                metadata={'source_card_id':str(source_card),'opponent_card_id':str(opponent_card),'source_rank':source_rank,'opponent_rank':opponent_rank}))
            # The frozen classic version gives the initiating holder priority if both have Zongshi.
            skills=getattr(self.moves,'skills',None)
            owner=None
            if skills is not None:
                if skills.has(state,action.source_id,'zongshi_jianyong'):owner=action.source_id
                elif skills.has(state,action.opponent_id,'zongshi_jianyong'):owner=action.opponent_id
            if owner is not None:
                wins=source_rank>opponent_rank if owner==action.source_id else opponent_rank>source_rank
                own=source_card if owner==action.source_id else opponent_card
                other=opponent_card if owner==action.source_id else source_card
                candidate=other if wins else own
                frame.local['zongshi_owner']=owner;frame.local['zongshi_card']=candidate
            frame.step_index=3
            return StepResult.continue_()
        if frame.step_index==3:
            owner=frame.local.get('zongshi_owner');candidate=frame.local.get('zongshi_card')
            skills=getattr(self.moves,'skills',None)
            if owner is not None and state.players[owner].is_alive and skills.has(state,owner,'zongshi_jianyong') and candidate in state.cards_in(processing):
                frame.step_index=4
                return StepResult.ask(PendingRequest(action.action_id+':zongshi',owner,RequestType.YES_NO,'【纵适】是否获得此次拼点的牌？',action.action_id,frame.frame_id))
            frame.step_index=5
            return StepResult.continue_()
        if frame.step_index==4:
            wanted,frame.decision=frame.decision is True,None
            owner=frame.local['zongshi_owner'];candidate=frame.local['zongshi_card'];skills=getattr(self.moves,'skills',None)
            if wanted and state.players[owner].is_alive and skills.has(state,owner,'zongshi_jianyong') and candidate in state.cards_in(processing):
                self.moves.move(state,CardMove(action.action_id+':zongshi-obtain',(candidate,),processing,ZoneRef(ZoneType.HAND,owner),CardMoveReason.SYSTEM,owner))
            frame.step_index=5
            return StepResult.continue_()
        cards=tuple(c for c in (frame.local['source_card'],frame.local['opponent_card']) if c in state.cards_in(processing))
        if cards:
            self.moves.move(state,CardMove(action.action_id+':discard',cards,processing,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,action.source_id))
        return StepResult.complete(frame.local['source_win'])

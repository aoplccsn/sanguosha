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
        self.validate_start(state, action)
        source_card, opponent_card = frame.local['source_card'], frame.decision
        frame.decision = None
        if source_card not in self._hand(state, action.source_id) or opponent_card not in self._hand(state, action.opponent_id):
            raise InvalidCardUse('拼点牌已不可用')
        processing = ZoneRef(ZoneType.PROCESSING)
        for player_id, card_id in ((action.source_id, source_card), (action.opponent_id, opponent_card)):
            self.moves.move(state, CardMove(action.action_id + ':reveal:' + player_id, (card_id,),
                ZoneRef(ZoneType.HAND, player_id), processing, CardMoveReason.SYSTEM, player_id))
        source_rank, opponent_rank = state.cards[source_card].rank, state.cards[opponent_card].rank
        self.events.record(Event(action.action_id + ':shown', 'pindian_revealed', action.source_id,
            metadata={'source_card_id': str(source_card), 'opponent_card_id': str(opponent_card),
                      'source_rank': source_rank, 'opponent_rank': opponent_rank}))
        self.moves.move(state, CardMove(action.action_id + ':discard', (source_card, opponent_card),
            processing, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD, action.source_id))
        return StepResult.complete(source_rank > opponent_rank)


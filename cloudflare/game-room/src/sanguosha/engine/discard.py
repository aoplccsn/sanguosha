"""Play-independent hand-limit discard phase."""

from sanguosha.model.ids import CardInstanceId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .errors import ResolutionError
from .events import CardRespondedEvent, CardUsedEvent, TurnStartedEvent
from .requests import PendingRequest, RequestType
from .resolution import ResolutionFrame


class DiscardPhaseBody:
    def __init__(self, moves: CardMoveService, skills=None, events=None, hand_limit=None) -> None:
        self.moves = moves
        self.skills = skills
        self.events = events
        self.hand_limit = hand_limit or (lambda state, player_id: max(0, state.players[player_id].hp))

    def _may_keji(self, state, player_id):
        if self.skills is None or self.events is None or not self.skills.has(state, player_id, 'keji'):
            return False
        usage = state.play_usage
        if (usage is not None and usage.player_id == player_id and usage.turn_number == state.turn_number
                and any(usage.count(slash) for slash in ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash'))):
            return False
        turn_events = self.events.events
        start = next((index for index in range(len(turn_events)-1, -1, -1)
                      if isinstance(turn_events[index], TurnStartedEvent)
                      and turn_events[index].player_id == player_id), -1)
        if start < 0:
            return False
        for event in turn_events[start+1:]:
            if isinstance(event, CardUsedEvent) and event.player_id == player_id:
                definition = str(state.cards[event.card_id].definition_id)
            elif isinstance(event, CardRespondedEvent) and event.player_id == player_id:
                definition = event.response_definition_id or str(state.cards[event.card_id].definition_id)
            else:
                continue
            if definition in ('basic.slash', 'basic.fire_slash', 'basic.thunder_slash'):
                return False
        return True

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        hand = ZoneRef(ZoneType.HAND, action.player_id)
        if frame.step_index == 1:
            eligible = state.cards_in(hand)
            limit = self.hand_limit(state, action.player_id)
            excess = len(eligible) - limit
            if excess <= 0:
                return StepResult.complete()
            if self._may_keji(state, action.player_id):
                frame.step_index = 3
                return StepResult.ask(PendingRequest(
                    f"{action.action_id}:keji", action.player_id, RequestType.YES_NO,
                    '是否发动【克己】跳过弃牌阶段？', action.action_id, frame.frame_id))
            return self._ask_discard(state, frame, eligible, excess)
        if frame.step_index == 3:
            skip = frame.decision
            frame.decision = None
            if skip:
                return StepResult.complete(0)
            eligible = state.cards_in(hand)
            excess = len(eligible) - self.hand_limit(state, action.player_id)
            if excess <= 0:
                return StepResult.complete(0)
            return self._ask_discard(state, frame, eligible, excess)
        if frame.step_index == 2:
            choice = frame.decision
            if not isinstance(choice, tuple):
                raise ResolutionError("discard choice is missing")
            frame.decision = None
            self.moves.move(state, CardMove(
                f"{action.action_id}:move-discard", tuple(CardInstanceId(card_id) for card_id in choice),
                hand, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
                action.player_id, action.action_id,
            ))
            return StepResult.complete(len(choice))
        raise ResolutionError("invalid discard phase step")

    def _ask_discard(self, state, frame, eligible, excess):
        action = frame.action
        frame.step_index = 2
        return StepResult.ask(PendingRequest(
            f"{action.action_id}:discard", action.player_id,
            RequestType.CHOOSE_CARDS, f"Discard {excess} card(s)",
            action.action_id, frame.frame_id,
            eligible_card_ids=eligible, min_count=excess, max_count=excess,
        ))

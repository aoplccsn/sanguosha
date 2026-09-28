"""Play-independent hand-limit discard phase."""

from sanguosha.model.ids import CardInstanceId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .errors import ResolutionError
from .requests import PendingRequest, RequestType
from .resolution import ResolutionFrame


class DiscardPhaseBody:
    def __init__(self, moves: CardMoveService) -> None:
        self.moves = moves

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        hand = ZoneRef(ZoneType.HAND, action.player_id)
        if frame.step_index == 1:
            eligible = state.cards_in(hand)
            limit = max(0, state.players[action.player_id].hp)
            excess = len(eligible) - limit
            if excess <= 0:
                return StepResult.complete()
            frame.step_index = 2
            return StepResult.ask(PendingRequest(
                f"{action.action_id}:discard", action.player_id,
                RequestType.CHOOSE_CARDS, f"Discard {excess} card(s)",
                action.action_id, frame.frame_id,
                eligible_card_ids=eligible, min_count=excess, max_count=excess,
            ))
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

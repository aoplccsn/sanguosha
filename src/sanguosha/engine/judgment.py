"""One-card judgment lifecycle, kept on a resolution frame for future replacement."""

from dataclasses import dataclass

from sanguosha.model.enums import Color, Suit
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .events import Event, EventRecorder
from .resolution import ResolutionFrame


@dataclass(frozen=True, slots=True)
class JudgmentPattern:
    suit: Suit | None = None
    color: Color | None = None
    ranks: frozenset[int] | None = None

    def matches(self, state: GameState, card_id: CardInstanceId) -> bool:
        card = state.cards[card_id]
        return ((self.suit is None or card.suit is self.suit)
                and (self.color is None or card.color is self.color)
                and (self.ranks is None or card.rank in self.ranks))


@dataclass(frozen=True, slots=True)
class JudgmentAction(Action):
    player_id: PlayerId
    pattern: JudgmentPattern


class JudgmentHandler:
    def __init__(self, moves: CardMoveService, recorder: EventRecorder, deck=None) -> None:
        self.moves = moves
        self.recorder = recorder
        self.deck = deck

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, JudgmentAction)
        draw = ZoneRef(ZoneType.DRAW_PILE)
        processing = ZoneRef(ZoneType.PROCESSING)
        if frame.step_index == 0:
            self.recorder.record(Event(f"{action.action_id}:before", "before_judgment", action.player_id))
            if self.deck is not None:
                self.deck.ensure_draw(state, action.action_id)
            available = state.cards_in(draw)
            if not available:
                raise ValueError("judgment draw pile is empty")
            card_id = available[0]
            self.moves.move(state, CardMove(f"{action.action_id}:reveal", (card_id,), draw, processing,
                                            CardMoveReason.SYSTEM, action.player_id, action.action_id))
            frame.local["card_id"] = str(card_id)
            self.recorder.record(Event(f"{action.action_id}:revealed", "judgment_card_revealed",
                                       action.player_id, metadata={"card_id": str(card_id)}))
            frame.step_index = 1
            return StepResult.continue_()
        card_id = CardInstanceId(str(frame.local["card_id"]))
        if frame.step_index == 1:
            if card_id not in state.cards_in(processing):
                raise ValueError("judgment card left processing before result")
            matched = action.pattern.matches(state, card_id)
            frame.local["matched"] = matched
            self.recorder.record(Event(f"{action.action_id}:result", "judgment_result",
                                       action.player_id, metadata={"card_id": str(card_id), "matched": matched}))
            frame.step_index = 2
            return StepResult.continue_()
        self.moves.move(state, CardMove(f"{action.action_id}:discard", (card_id,), processing,
                                        ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM,
                                        action.player_id, action.action_id))
        self.recorder.record(Event(f"{action.action_id}:after", "after_judgment", action.player_id,
                                   metadata={"card_id": str(card_id), "matched": bool(frame.local["matched"])}))
        return StepResult.complete(bool(frame.local["matched"]))

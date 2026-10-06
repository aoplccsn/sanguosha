"""Specific physical-card response, including explicit pass."""

from dataclasses import dataclass

from sanguosha.model.ids import CardDefinitionId, CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason, CardMoveService
from .errors import EngineError, ResolutionError
from .events import CardRespondedEvent, EventRecorder
from .requests import PASS_RESPONSE, PendingRequest, RequestType
from .resolution import ResolutionFrame


class InvalidResponse(EngineError):
    pass


@dataclass(frozen=True, slots=True)
class RespondWithCardAction(Action):
    player_id: PlayerId
    required_definition_id: CardDefinitionId
    source_action_id: str
    prompt: str = "Respond with a card or pass"
    subject_player_id: PlayerId | None = None
    allow_armor: bool = True
    response_number: int = 1
    response_total: int = 1


class RespondWithCardHandler:
    def __init__(self, moves: CardMoveService, recorder: EventRecorder) -> None:
        self.moves = moves
        self.recorder = recorder

    def step(self, state: GameState, frame: ResolutionFrame) -> StepResult:
        action = frame.action
        assert isinstance(action, RespondWithCardAction)
        hand = ZoneRef(ZoneType.HAND, action.player_id)
        if frame.step_index == 0:
            eligible = tuple(
                card_id for card_id in state.cards_in(hand)
                if state.cards[card_id].definition_id == action.required_definition_id
            )
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                f"{action.action_id}:request", action.player_id,
                RequestType.RESPOND_WITH_CARD, action.prompt,
                action.action_id, frame.frame_id,
                required_definition_id=action.required_definition_id,
                eligible_card_ids=eligible, allow_pass=True,
                subject_player_id=action.subject_player_id,
            ))
        choice = frame.decision
        frame.decision = None
        if choice is PASS_RESPONSE:
            return StepResult.complete()
        if not isinstance(choice, str):
            raise InvalidResponse("response choice is missing")
        card_id = CardInstanceId(choice)
        if card_id not in state.cards_in(hand) or state.cards[card_id].definition_id != action.required_definition_id:
            raise InvalidResponse("response card is no longer eligible")
        processing = ZoneRef(ZoneType.PROCESSING)
        discard = ZoneRef(ZoneType.DISCARD_PILE)
        self.moves.move(state, CardMove(f"{action.action_id}:to-processing", (card_id,), hand, processing, CardMoveReason.RESPONSE, action.player_id, action.action_id))
        self.recorder.record(CardRespondedEvent(f"{action.action_id}:responded", action.player_id, card_id,
                                                action.source_action_id, str(action.required_definition_id),
                                                action.response_number, action.response_total))
        self.moves.move(state, CardMove(f"{action.action_id}:to-discard", (card_id,), processing, discard, CardMoveReason.RESPONSE, action.player_id, action.action_id))
        return StepResult.complete(str(card_id))


def dodge_gift_options(state,skills,pid):
    """Method-none Jink offers: transfer physical subcards without a response event."""
    from .yj2011_tier3 import canonical_definition
    from .suits import effective_color
    from sanguosha.model.enums import Color
    hand=state.cards_in(ZoneRef(ZoneType.HAND,pid))
    offers={c:(c,) for c in hand if canonical_definition(state,skills,pid,state.cards[c].definition_id,c)=='basic.dodge'}
    if skills.has(state,pid,'qingguo'):
        offers.update({'virtual:qingguo:'+c:(c,) for c in hand if effective_color(state,c,pid) is Color.BLACK})
    if skills.has(state,pid,'longdan'):
        offers.update({'virtual:longdan:'+c:(c,) for c in hand if canonical_definition(state,skills,pid,state.cards[c].definition_id,c) in ('basic.slash','basic.fire_slash','basic.thunder_slash')})
    if skills.has(state,pid,'longhun'):
        from .gods import longhun_materials,longhun_option
        offers.update({longhun_option(cards):cards for cards in longhun_materials(state,pid,'basic.dodge')})
    return offers

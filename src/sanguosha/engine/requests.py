"""Typed serial decision requests and their validation."""

from dataclasses import dataclass
from enum import Enum, StrEnum

from sanguosha.model.ids import CardDefinitionId, CardInstanceId, PlayerId

from .errors import InvalidDecision


class RequestType(StrEnum):
    YES_NO = "yes_no"
    CHOOSE_OPTION = "choose_option"
    CHOOSE_PLAYER = "choose_player"
    CHOOSE_PLAYERS = "choose_players"
    CHOOSE_CARD = "choose_card"
    CHOOSE_CARDS = "choose_cards"
    RESPOND_WITH_CARD = "respond_with_card"
    USE_CARD = "use_card"


class ResponsePass(Enum):
    PASS = "pass"


PASS_RESPONSE = ResponsePass.PASS
ChoiceValue = bool | str | PlayerId | CardInstanceId | ResponsePass | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PendingRequest:
    request_id: str
    player_id: PlayerId
    request_type: RequestType
    prompt: str
    originating_action_id: str
    originating_frame_id: str
    choices: tuple[str, ...] = ()
    allowed_player_ids: tuple[PlayerId, ...] = ()
    required_definition_id: CardDefinitionId | None = None
    eligible_card_ids: tuple[CardInstanceId, ...] = ()
    allow_pass: bool = False
    min_count: int = 0
    max_count: int = 0
    subject_player_id: PlayerId | None = None

    def validate(self, value: ChoiceValue) -> None:
        kind = self.request_type
        if kind is RequestType.YES_NO:
            valid = type(value) is bool
        elif kind is RequestType.CHOOSE_OPTION:
            valid = type(value) is str and value in self.choices
        elif kind is RequestType.CHOOSE_PLAYER:
            valid = type(value) is str and value in self.allowed_player_ids
        elif kind is RequestType.RESPOND_WITH_CARD:
            valid = (value is PASS_RESPONSE and self.allow_pass) or (
                type(value) is str and value in self.eligible_card_ids
            )
        elif kind is RequestType.CHOOSE_CARD:
            valid = type(value) is str and value in self.eligible_card_ids
        elif kind is RequestType.CHOOSE_CARDS:
            valid = (
                type(value) is tuple
                and self.min_count <= len(value) <= self.max_count
                and all(type(card_id) is str and card_id in self.eligible_card_ids for card_id in value)
                and len(value) == len(set(value))
            )
        elif kind is RequestType.CHOOSE_PLAYERS:
            valid = (
                type(value) is tuple
                and self.min_count <= len(value) <= self.max_count
                and all(type(player_id) is str and player_id in self.allowed_player_ids for player_id in value)
                and len(value) == len(set(value))
            )
        else:
            # Other request shapes are reserved for later rule stages.
            raise InvalidDecision(f"request type {kind} has no T2 validator")
        if not valid:
            raise InvalidDecision(f"illegal choice for {kind}: {value!r}")


@dataclass(frozen=True, slots=True)
class Decision:
    request_id: str
    player_id: PlayerId
    value: ChoiceValue

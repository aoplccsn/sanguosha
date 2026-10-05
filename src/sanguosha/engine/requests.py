"""Typed serial decision requests and their validation."""

from dataclasses import dataclass, field
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
ChoiceValue = bool | str | PlayerId | CardInstanceId | ResponsePass | tuple[str, ...] | dict


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
    play_card_targets: dict[str, tuple[tuple[str, ...], int, int]] = field(default_factory=dict)

    minimum_nonempty_count: int = 0
    legal_card_sets: tuple[tuple[CardInstanceId, ...], ...] = ()

    def has_legal_response(self) -> bool:
        """The rule handler supplies physical and virtual response candidates here."""
        return self.request_type is RequestType.RESPOND_WITH_CARD and bool(self.eligible_card_ids)

    def timeout_value(self) -> ChoiceValue:
        """A deterministic legal fallback, submitted through the normal Decision API."""
        if self.request_type is RequestType.RESPOND_WITH_CARD and self.allow_pass:
            value = PASS_RESPONSE
        elif self.request_type is RequestType.YES_NO:
            value = False
        elif self.request_type is RequestType.CHOOSE_OPTION:
            from .phases import END_PLAY_PHASE
            value = END_PLAY_PHASE if END_PLAY_PHASE in self.choices else self.choices[0]
        elif self.request_type is RequestType.CHOOSE_PLAYER:
            value = self.allowed_player_ids[0]
        elif self.request_type is RequestType.CHOOSE_PLAYERS:
            value = self.allowed_player_ids[:self.min_count]
        elif self.request_type is RequestType.CHOOSE_CARD:
            value = self.eligible_card_ids[0]
        elif self.request_type is RequestType.CHOOSE_CARDS:
            value = self.legal_card_sets[0] if self.legal_card_sets else self.eligible_card_ids[:self.min_count]
        else:
            raise InvalidDecision(f"no timeout fallback for {self.request_type}")
        self.validate(value)
        return value

    def validate(self, value: ChoiceValue) -> None:
        kind = self.request_type
        if kind is RequestType.YES_NO:
            valid = type(value) is bool
        elif kind is RequestType.CHOOSE_OPTION:
            valid = type(value) is str and value in self.choices
            if type(value) is dict and set(value) == {'option', 'targets'}:
                option, targets = value['option'], value['targets']
                spec = self.play_card_targets.get(option) if type(option) is str else None
                valid = (spec is not None and type(targets) is tuple
                         and spec[1] <= len(targets) <= spec[2]
                         and len(targets) == len(set(targets))
                         and all(type(target) is str and target in spec[0] for target in targets))
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
                and (not value or len(value) >= self.minimum_nonempty_count)
                and all(type(card_id) is str and card_id in self.eligible_card_ids for card_id in value)
                and len(value) == len(set(value))
                and (not self.legal_card_sets or any(set(value) == set(cards) for cards in self.legal_card_sets))
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

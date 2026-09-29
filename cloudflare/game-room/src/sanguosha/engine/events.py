"""Small immutable fact records; no trigger dispatch in T2."""

from dataclasses import dataclass, field
from typing import Mapping

from sanguosha.model.enums import Phase
from sanguosha.model.enums import Identity
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.zones import ZoneRef


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    event_type: str
    source_id: PlayerId | None = None
    target_ids: tuple[PlayerId, ...] = ()
    metadata: Mapping[str, str | int | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TurnStartedEvent:
    event_id: str
    player_id: PlayerId
    turn_number: int


@dataclass(frozen=True, slots=True)
class TurnEndedEvent:
    event_id: str
    player_id: PlayerId
    turn_number: int


@dataclass(frozen=True, slots=True)
class PhaseStartedEvent:
    event_id: str
    player_id: PlayerId
    phase: Phase


@dataclass(frozen=True, slots=True)
class PhaseEndedEvent:
    event_id: str
    player_id: PlayerId
    phase: Phase


@dataclass(frozen=True, slots=True)
class PhaseSkippedEvent:
    event_id: str
    player_id: PlayerId
    phase: Phase


@dataclass(frozen=True, slots=True)
class CardMovedEvent:
    event_id: str
    card_ids: tuple[CardInstanceId, ...]
    from_zone: ZoneRef
    to_zone: ZoneRef
    reason: str
    actor_id: PlayerId | None
    related_action_id: str | None


@dataclass(frozen=True, slots=True)
class CardUsedEvent:
    event_id: str
    player_id: PlayerId
    card_id: CardInstanceId
    target_ids: tuple[PlayerId, ...]
    virtual_definition_id: str = ''


@dataclass(frozen=True, slots=True)
class TrickTargetsDeclaredEvent:
    event_id: str
    player_id: PlayerId
    card_id: CardInstanceId
    definition_id: str
    target_ids: tuple[PlayerId, ...]


@dataclass(frozen=True, slots=True)
class CardRespondedEvent:
    event_id: str
    player_id: PlayerId
    card_id: CardInstanceId
    source_action_id: str
    response_definition_id: str = ''
    response_number: int = 1
    response_total: int = 1


@dataclass(frozen=True, slots=True)
class VirtualResponseEvent:
    event_id: str
    player_id: PlayerId
    source_action_id: str
    response_definition_id: str
    response_number: int = 1
    response_total: int = 1


@dataclass(frozen=True, slots=True)
class CardResolvedEvent:
    event_id: str
    player_id: PlayerId
    card_id: CardInstanceId


@dataclass(frozen=True, slots=True)
class BeforeDamageEvent:
    event_id: str
    source_id: PlayerId | None
    target_id: PlayerId
    amount: int


@dataclass(frozen=True, slots=True)
class DamageDealtEvent:
    event_id: str
    source_id: PlayerId | None
    target_id: PlayerId
    amount: int
    hp_after: int


@dataclass(frozen=True, slots=True)
class AfterDamageEvent:
    event_id: str
    source_id: PlayerId | None
    target_id: PlayerId
    amount: int


@dataclass(frozen=True, slots=True)
class DyingRequiredEvent:
    event_id: str
    target_id: PlayerId
    hp: int


@dataclass(frozen=True, slots=True)
class HpRecoveredEvent:
    event_id: str
    source_id: PlayerId | None
    target_id: PlayerId
    amount: int
    hp_after: int


@dataclass(frozen=True, slots=True)
class DyingRescuedEvent:
    event_id: str
    player_id: PlayerId
    hp: int


@dataclass(frozen=True, slots=True)
class PlayerDiedEvent:
    event_id: str
    player_id: PlayerId
    identity: Identity
    killer_id: PlayerId | None


@dataclass(frozen=True, slots=True)
class KillRewardEvent:
    event_id: str
    killer_id: PlayerId
    rebel_id: PlayerId
    cards_drawn: int


@dataclass(frozen=True, slots=True)
class LordPenaltyEvent:
    event_id: str
    lord_id: PlayerId
    loyalist_id: PlayerId


@dataclass(frozen=True, slots=True)
class GameEndedEvent:
    event_id: str
    label: str
    winner_ids: tuple[PlayerId, ...]


RecordedEvent = (
    Event | TurnStartedEvent | TurnEndedEvent | PhaseStartedEvent | PhaseEndedEvent | PhaseSkippedEvent
    | CardMovedEvent | CardUsedEvent | TrickTargetsDeclaredEvent | CardRespondedEvent | VirtualResponseEvent | CardResolvedEvent
    | BeforeDamageEvent | DamageDealtEvent | AfterDamageEvent | DyingRequiredEvent | HpRecoveredEvent
    | DyingRescuedEvent | PlayerDiedEvent | KillRewardEvent | LordPenaltyEvent | GameEndedEvent
)


class EventRecorder:
    def __init__(self) -> None:
        self.events: list[RecordedEvent] = []

    def record(self, event: RecordedEvent) -> None:
        self.events.append(event)

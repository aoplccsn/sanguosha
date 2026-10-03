"""Game snapshot with basic structural validation, no rule execution."""

from dataclasses import dataclass, field
from enum import StrEnum
from .card import CardInstance
from .enums import Phase
from .ids import CardInstanceId, PlayerId
from .player import PlayerState
from .zones import CardZone, ZoneRef
from .usage import PlayUsageState
from .victory import VictoryResult


class GameStatus(StrEnum):
    SETUP = "setup"
    ACTIVE = "active"
    FINISHED = "finished"


@dataclass(slots=True)
class GameState:
    ruleset_id: str
    players: dict[PlayerId, PlayerState] = field(default_factory=dict)
    seat_order: tuple[PlayerId, ...] = ()
    cards: dict[CardInstanceId, CardInstance] = field(default_factory=dict)
    zones: dict[ZoneRef, CardZone] = field(default_factory=dict)
    current_player_id: PlayerId | None = None
    current_phase: Phase | None = None
    turn_number: int = 0
    status: GameStatus = GameStatus.SETUP
    metadata: dict[str, object] = field(default_factory=dict)
    play_usage: PlayUsageState | None = None
    revealed_identities: set[PlayerId] = field(default_factory=set)
    victory: VictoryResult | None = None
    extra_turn_queue: list[PlayerId] = field(default_factory=list)
    extra_turn_anchor: PlayerId | None = None

    def __post_init__(self) -> None:
        if not self.ruleset_id:
            raise ValueError("ruleset_id is required")
        if self.turn_number < 0:
            raise ValueError("turn_number must be nonnegative")
        if len(self.seat_order) != len(set(self.seat_order)) or set(self.seat_order) != set(self.players):
            raise ValueError("seat_order must contain every player exactly once")
        if any(player.player_id != key for key, player in self.players.items()):
            raise ValueError("player keys must match player IDs")
        if len({p.seat for p in self.players.values()}) != len(self.players):
            raise ValueError("seats must be unique")
        if self.seat_order and tuple(sorted(self.seat_order, key=lambda p: self.players[p].seat)) != self.seat_order:
            raise ValueError("seat_order must follow seat numbers")
        if self.current_player_id is not None and self.current_player_id not in self.players:
            raise ValueError("current player must exist")
        if any(player_id not in self.players for player_id in self.extra_turn_queue):
            raise ValueError("extra turn queue contains an unknown player")
        if self.extra_turn_anchor is not None and self.extra_turn_anchor not in self.players:
            raise ValueError("extra turn anchor is unknown")
        if any(card.instance_id != key for key, card in self.cards.items()):
            raise ValueError("card keys must match instance IDs")
        located: list[CardInstanceId] = []
        for ref, zone in self.zones.items():
            if zone.ref != ref:
                raise ValueError("zone keys must match their references")
            if ref.player_id is not None and ref.player_id not in self.players:
                raise ValueError("zone player must exist")
            located.extend(zone.card_ids)
        if len(located) != len(set(located)) or set(located) != set(self.cards):
            raise ValueError("every card must be in exactly one zone")

    def get_player(self, player_id: PlayerId) -> PlayerState:
        return self.players[player_id]

    def cards_in(self, ref: ZoneRef) -> tuple[CardInstanceId, ...]:
        zone = self.zones.get(ref)
        return tuple(zone.card_ids) if zone is not None else ()

"""Atomic zone movement; the only formal rule path that mutates card locations."""

from dataclasses import dataclass
from enum import StrEnum

from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameState
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType

from .errors import EngineError
from .events import CardMovedEvent, EventRecorder


class InvalidCardMove(EngineError):
    pass


class CardMoveReason(StrEnum):
    USE = "use"
    RESPONSE = "response"
    DISCARD = "discard"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class CardMove:
    move_id: str
    card_ids: tuple[CardInstanceId, ...]
    from_zone: ZoneRef
    to_zone: ZoneRef
    reason: CardMoveReason
    actor_id: PlayerId | None = None
    related_action_id: str | None = None


class CardMoveService:
    def __init__(self, recorder: EventRecorder) -> None:
        self.recorder = recorder

    def move(self, state: GameState, move: CardMove) -> None:
        ids = move.card_ids
        if not move.move_id or not ids or len(ids) != len(set(ids)):
            raise InvalidCardMove("move needs a unique id and distinct cards")
        if move.from_zone == move.to_zone:
            raise InvalidCardMove("source and destination must differ")
        if any(card_id not in state.cards for card_id in ids):
            raise InvalidCardMove("move contains unknown card")
        source = state.zones.get(move.from_zone)
        if source is None or any(card_id not in source.card_ids for card_id in ids):
            raise InvalidCardMove("card is not in source zone")
        if move.from_zone.player_id is not None and move.from_zone.player_id not in state.players:
            raise InvalidCardMove("source player does not exist")
        if move.to_zone.player_id is not None and move.to_zone.player_id not in state.players:
            raise InvalidCardMove("destination player does not exist")
        for card_id in ids:
            if sum(zone.card_ids.count(card_id) for zone in state.zones.values()) != 1:
                raise InvalidCardMove("card has no unique current location")
        destination = state.zones.get(move.to_zone)
        dest_ids = list(destination.card_ids) if destination is not None else []
        if move.to_zone.zone_type is ZoneType.EQUIPMENT and len(dest_ids) + len(ids) > 1:
            raise InvalidCardMove("equipment slot capacity exceeded")
        if any(card_id in dest_ids for card_id in ids):
            raise InvalidCardMove("card already exists in destination")
        new_source = [card_id for card_id in source.card_ids if card_id not in ids]
        new_destination = [*dest_ids, *ids]
        # All validation is complete. Commit both zones before publishing a fact.
        source.card_ids[:] = new_source
        if destination is None:
            state.zones[move.to_zone] = CardZone(move.to_zone, new_destination)
        else:
            destination.card_ids[:] = new_destination
        if move.from_zone.zone_type is ZoneType.JUDGMENT and move.to_zone.zone_type is not ZoneType.JUDGMENT:
            virtual_delayed = state.metadata.get('virtual_delayed_cards', {})
            for card_id in ids:
                virtual_delayed.pop(card_id, None)
        self.recorder.record(CardMovedEvent(
            move.move_id, ids, move.from_zone, move.to_zone,
            move.reason.value, move.actor_id, move.related_action_id,
        ))

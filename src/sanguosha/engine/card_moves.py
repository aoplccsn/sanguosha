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
    to_top: bool = False


class CardMoveService:
    def __init__(self, recorder: EventRecorder) -> None:
        self.recorder = recorder

    def obtain_cards(self, state, card_ids, recipient_id, actor_id, acquisition_id):
        """One acquisition can draw from several zones of the same card owner."""
        from .events import Event
        if (not acquisition_id or not card_ids or len(card_ids) != len(set(card_ids))
                or recipient_id not in state.players or not state.players[recipient_id].is_alive):
            raise InvalidCardMove("invalid acquisition")
        destination = ZoneRef(ZoneType.HAND, recipient_id)
        groups, counts = {}, {}
        for cid in card_ids:
            refs = [ref for ref, z in state.zones.items() if cid in z.card_ids]
            if cid not in state.cards or len(refs) != 1 or refs[0] == destination:
                raise InvalidCardMove("acquisition card has no valid source")
            ref = refs[0]
            groups.setdefault(ref, []).append(cid)
            if ref.player_id is not None:
                counts[ref.player_id] = counts.get(ref.player_id, 0) + 1
        # No choice or callback runs between these moves. The published summary
        # binds the whole acquisition, including cards from different zones.
        for index, (ref, ids) in enumerate(groups.items()):
            self.move(state, CardMove(acquisition_id + ':part:' + str(index), tuple(ids),
                ref, destination, CardMoveReason.SYSTEM, actor_id, 'acquisition:' + acquisition_id))
        for source, count in counts.items():
            self.recorder.record(Event(acquisition_id + ':obtained:' + source, 'cards_obtained',
                recipient_id, metadata={'from_player_id': source, 'count': count}))

    def exchange_equipment(self, state, transaction):
        """Validate every departure and slot before publishing an atomic exchange."""
        from sanguosha.model.enums import EquipmentSlot
        if not transaction.transaction_id or len(transaction.player_ids) != 2:
            raise InvalidCardMove("exchange requires an id and exactly two players")
        a, b = transaction.player_ids
        if a == b or any(pid not in state.players or not state.players[pid].is_alive for pid in (a, b)):
            raise InvalidCardMove("exchange requires distinct living players")
        moves = []
        final = {}
        for slot in EquipmentSlot:
            ar = ZoneRef(ZoneType.EQUIPMENT, a, slot)
            br = ZoneRef(ZoneType.EQUIPMENT, b, slot)
            ac, bc = state.cards_in(ar), state.cards_in(br)
            for ref, ids in ((ar, ac), (br, bc)):
                if len(ids) > 1 or any(cid not in state.cards or
                        sum(z.card_ids.count(cid) for z in state.zones.values()) != 1 for cid in ids):
                    raise InvalidCardMove("invalid equipment location")
            final[ar], final[br] = list(bc), list(ac)
            for source, dest, ids in ((ar, br, ac), (br, ar, bc)):
                if ids:
                    moves.append(CardMove(transaction.transaction_id + ':' + source.player_id + ':' + slot.value,
                        ids, source, dest, CardMoveReason.SYSTEM, transaction.actor_id,
                        'equipment-exchange:' + transaction.transaction_id))
        # Capture departure reactions against the old state. No mutation occurs
        # until every slot and card has passed validation.
        facts = [(move, self._departure_facts(state, move)) for move in moves]
        for ref, ids in final.items():
            if ref not in state.zones:
                state.zones[ref] = CardZone(ref, ids)
            else:
                state.zones[ref].card_ids[:] = ids
        for move, fact in facts:
            self.recorder.record(CardMovedEvent(move.move_id, move.card_ids, move.from_zone,
                move.to_zone, move.reason.value, move.actor_id, move.related_action_id))
            self._after_departure(state, move, fact)
        from .events import Event
        for owner in (a, b):
            departed = sum(len(move.card_ids) for move in moves if move.from_zone.player_id == owner)
            if departed:
                self.recorder.record(Event(transaction.transaction_id + ':equipment-left:' + owner,
                    'equipment_departure_batch', owner, metadata={'count': departed}))

    def _departure_facts(self, state, move):
        return None

    def _after_departure(self, state, move, facts):
        pass

    def move(self, state: GameState, move: CardMove) -> None:
        ids = move.card_ids
        if not move.move_id or not ids or len(ids) != len(set(ids)):
            raise InvalidCardMove("move needs a unique id and distinct cards")
        if move.from_zone == move.to_zone:
            raise InvalidCardMove("source and destination must differ")
        if move.to_top and move.to_zone.zone_type is not ZoneType.DRAW_PILE:
            raise InvalidCardMove("top placement requires draw pile destination")
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
        new_destination = [*ids, *dest_ids] if move.to_top else [*dest_ids, *ids]
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
        if (move.from_zone.zone_type is ZoneType.DISCARD_PILE
                or move.to_zone.zone_type not in (ZoneType.PROCESSING, ZoneType.DISCARD_PILE)):
            concealed = state.metadata.get('concealed_discard_cards', {})
            for card_id in ids:
                concealed.pop(card_id, None)
        self.recorder.record(CardMovedEvent(
            move.move_id, ids, move.from_zone, move.to_zone,
            move.reason.value, move.actor_id, move.related_action_id,
        ))


@dataclass(frozen=True, slots=True)
class EquipmentExchangeTransaction:
    transaction_id: str
    player_ids: tuple[str, str]
    actor_id: str

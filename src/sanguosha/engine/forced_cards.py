"""Reusable forced discards and private hand exchanges."""

from dataclasses import dataclass

from sanguosha.model.zones import ZoneRef, ZoneType

from .actions import Action, StepResult
from .card_moves import CardMove, CardMoveReason
from .requests import PendingRequest, RequestType


def discardable_cards(state, player_id):
    return tuple(cid for ref, zone in state.zones.items()
                 if ref.player_id == player_id
                 and ref.zone_type in (ZoneType.HAND, ZoneType.EQUIPMENT)
                 for cid in zone.card_ids)


@dataclass(frozen=True, slots=True)
class ForcedDiscardAction(Action):
    player_id: str
    count: int


class ForcedDiscardHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        if frame.step_index == 0:
            if not state.players[action.player_id].is_alive:
                return StepResult.complete(0)
            cards = discardable_cards(state, action.player_id)
            count = min(max(0, action.count), len(cards))
            if not count:
                return StepResult.complete(0)
            frame.step_index = 1
            return StepResult.ask(PendingRequest(
                action.action_id + ':cards', action.player_id, RequestType.CHOOSE_CARDS,
                f'请选择弃置的 {count} 张牌', action.action_id, frame.frame_id,
                eligible_card_ids=cards, min_count=count, max_count=count))
        selected = tuple(frame.decision)
        frame.decision = None
        if not set(selected).issubset(discardable_cards(state, action.player_id)):
            return StepResult.complete(0)
        for index, card_id in enumerate(selected):
            source = next(ref for ref, zone in state.zones.items()
                          if ref.player_id == action.player_id and card_id in zone.card_ids)
            self.moves.move(state, CardMove(
                f'{action.action_id}:discard:{index}', (card_id,), source,
                ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.DISCARD,
                action.player_id, action.action_id))
        return StepResult.complete(len(selected))


@dataclass(frozen=True, slots=True)
class SwapHandsAction(Action):
    first_id: str
    second_id: str


class SwapHandsHandler:
    def __init__(self, moves):
        self.moves = moves

    def step(self, state, frame):
        action = frame.action
        first, second = action.first_id, action.second_id
        if first == second or not all(state.players[pid].is_alive for pid in (first, second)):
            return StepResult.complete(False)
        first_ref, second_ref = ZoneRef(ZoneType.HAND, first), ZoneRef(ZoneType.HAND, second)
        first_cards, second_cards = state.cards_in(first_ref), state.cards_in(second_ref)
        # Snapshot both original hands before either move. Both moves are hand-to-hand,
        # so no hidden card is exposed through a public processing zone.
        if second_cards:
            self.moves.move(state, CardMove(action.action_id + ':second-to-first',
                second_cards, second_ref, first_ref, CardMoveReason.SYSTEM,
                first, action.action_id))
        if first_cards:
            self.moves.move(state, CardMove(action.action_id + ':first-to-second',
                first_cards, first_ref, second_ref, CardMoveReason.SYSTEM,
                first, action.action_id))
        return StepResult.complete(True)

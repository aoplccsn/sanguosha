"""Seat-order lookup, independent of the resolution engine."""

from sanguosha.model.ids import PlayerId
from sanguosha.model.enums import Identity
from sanguosha.model.state import GameState

from .errors import EngineError


class InvalidTurn(EngineError):
    pass


def next_alive_player(state: GameState, current: PlayerId) -> PlayerId:
    if current not in state.seat_order:
        raise InvalidTurn(f"player {current!r} is not seated")
    order = state.seat_order
    start = order.index(current)
    for offset in range(1, len(order) + 1):
        candidate = order[(start + offset) % len(order)]
        if state.players[candidate].is_alive:
            return candidate
    raise InvalidTurn("no living player remains")


def queue_extra_turn(state: GameState, player_id: PlayerId) -> None:
    if player_id not in state.players or not state.players[player_id].is_alive:
        raise InvalidTurn(f"player {player_id!r} cannot receive an extra turn")
    state.extra_turn_queue.append(player_id)


def next_scheduled_player(state: GameState) -> PlayerId:
    while state.extra_turn_queue:
        player_id = state.extra_turn_queue.pop(0)
        if state.players[player_id].is_alive:
            if state.extra_turn_anchor is None:
                state.extra_turn_anchor = state.current_player_id
            return player_id
    if state.extra_turn_anchor is not None:
        anchor = state.extra_turn_anchor
        state.extra_turn_anchor = None
        return next_alive_player(state, anchor)
    current = state.current_player_id
    if current is None:
        return next(pid for pid in state.seat_order
                    if state.players[pid].is_alive and state.players[pid].identity is Identity.LORD)
    return next_alive_player(state, current)

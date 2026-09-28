"""Seat-order lookup, independent of the resolution engine."""

from sanguosha.model.ids import PlayerId
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

"""In-memory room registry for cloud authoritative matches."""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass, field

from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase

LOG = logging.getLogger(__name__)
ROOM_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


@dataclass(slots=True)
class ManagedRoom:
    code: str
    game: MultiplayerRoom
    created_at: float = field(default_factory=time.monotonic)
    last_active: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        self.last_active = time.monotonic()

    @property
    def connected_humans(self) -> int:
        return sum(1 for seat in self.game.seats.values() if seat.connected)


class RoomManager:
    def __init__(self, *, max_rooms: int = 1000, room_ttl: float = 7200.0,
                 reconnect_grace: float = 300.0, timeout_seconds: float = 30.0):
        self.max_rooms = max_rooms
        self.room_ttl = room_ttl
        self.reconnect_grace = reconnect_grace
        self.timeout_seconds = timeout_seconds
        self.rooms: dict[str, ManagedRoom] = {}

    def create(self, *, seed: int | None = None) -> ManagedRoom:
        if len(self.rooms) >= self.max_rooms:
            raise ValueError("server room limit reached")
        for _ in range(100):
            code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
            if code not in self.rooms:
                managed = ManagedRoom(code, MultiplayerRoom(seed=seed, timeout_seconds=self.timeout_seconds))
                self.rooms[code] = managed
                LOG.info("room created code=%s", code)
                return managed
        raise RuntimeError("unable to allocate a room code")

    def get(self, code: str) -> ManagedRoom:
        normalized = (code or "").strip().upper()
        try:
            managed = self.rooms[normalized]
        except KeyError as exc:
            raise ValueError("room not found") from exc
        managed.touch()
        return managed

    def remove(self, code: str) -> None:
        if self.rooms.pop(code, None) is not None:
            LOG.info("room released code=%s", code)

    def poll(self) -> None:
        now = time.monotonic()
        for code, managed in tuple(self.rooms.items()):
            managed.game.poll()
            age = now - managed.last_active
            if managed.game.phase is RoomPhase.FINISHED and age >= self.reconnect_grace:
                self.remove(code)
            elif managed.connected_humans == 0 and age >= self.reconnect_grace:
                self.remove(code)
            elif age >= self.room_ttl:
                self.remove(code)

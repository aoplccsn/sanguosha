from __future__ import annotations

import os
from dataclasses import dataclass


def integer(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(slots=True)
class RelayConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    public_base_url: str = "ws://127.0.0.1:8765"
    room_ttl: int = 7200
    host_reconnect_grace: int = 60
    max_rooms: int = 1000
    max_connections_per_ip: int = 20
    room_creations_per_minute: int = 10
    log_level: str = "INFO"

    @classmethod
    def from_env(cls):
        return cls(
            host=os.environ.get("RELAY_HOST", "0.0.0.0"),
            port=integer("RELAY_PORT", 8765),
            public_base_url=os.environ.get("PUBLIC_BASE_URL", "ws://127.0.0.1:8765"),
            room_ttl=integer("ROOM_TTL", 7200),
            host_reconnect_grace=integer("HOST_RECONNECT_GRACE", 60),
            max_rooms=integer("MAX_ROOMS", 1000),
            max_connections_per_ip=integer("MAX_CONNECTIONS_PER_IP", 20),
            room_creations_per_minute=integer("ROOM_CREATIONS_PER_MINUTE", 10),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

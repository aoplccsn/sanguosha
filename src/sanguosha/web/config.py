"""Environment-backed Web Edition configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WebConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    public_origin: str = "http://localhost:5173"
    secret_key: str = "development-only-change-me"
    room_ttl: float = 7200.0
    reconnect_grace: float = 300.0
    log_level: str = "INFO"
    max_rooms: int = 1000
    max_websockets: int = 5000
    message_size_limit: int = 256_000
    heartbeat_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "WebConfig":
        return cls(
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8000")),
            public_origin=os.getenv("PUBLIC_ORIGIN", "http://localhost:5173"),
            secret_key=os.getenv("SECRET_KEY", "development-only-change-me"),
            room_ttl=float(os.getenv("ROOM_TTL", "7200")),
            reconnect_grace=float(os.getenv("RECONNECT_GRACE", "300")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_rooms=int(os.getenv("MAX_ROOMS", "1000")),
            max_websockets=int(os.getenv("MAX_WEBSOCKETS", "5000")),
            message_size_limit=int(os.getenv("MESSAGE_SIZE_LIMIT", "256000")),
            heartbeat_seconds=float(os.getenv("HEARTBEAT_SECONDS", "20")),
        )

    def validate_production(self) -> None:
        if self.public_origin.startswith("https://") and self.secret_key == "development-only-change-me":
            raise RuntimeError("SECRET_KEY must be configured in production")

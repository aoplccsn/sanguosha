"""Environment-backed Web Edition configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WebConfig:
    production: bool = False
    domain: str = ""
    trusted_hosts: tuple[str, ...] = ()
    host: str = "127.0.0.1"
    port: int = 8000
    public_origin: str = "http://localhost:5173"
    secret_key: str = "development-only-change-me"
    room_ttl: float = 7200.0
    reconnect_grace: float = 300.0
    log_level: str = "INFO"
    max_rooms: int = 1000
    max_websockets: int = 5000
    max_connections: int = 5000
    room_creations_per_minute: int = 10
    message_size_limit: int = 256_000
    heartbeat_seconds: float = 20.0
    ai_presentation: bool = True

    @classmethod
    def from_env(cls) -> "WebConfig":
        render = os.getenv("RENDER", "").lower() == "true"
        zeabur = os.getenv("ZEABUR", "").lower() == "true"
        back4app = os.getenv("BACK4APP", "").lower() == "true"
        return cls(
            production=render or zeabur or back4app or os.getenv("APP_ENV", "development").lower() == "production",
            domain=(os.getenv("DOMAIN") or (os.getenv("RENDER_EXTERNAL_HOSTNAME") if render else None)
                    or (os.getenv("ZEABUR_WEB_DOMAIN") if zeabur else None) or "").strip().lower(),
            trusted_hosts=tuple(host.strip().lower() for host in os.getenv("TRUSTED_HOSTS", "").split(",") if host.strip()),
            host="0.0.0.0" if render or zeabur or back4app else os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "10000" if render else "8000")),
            public_origin=os.getenv("PUBLIC_ORIGIN") or (os.getenv("RENDER_EXTERNAL_URL") if render else None)
                          or (os.getenv("ZEABUR_WEB_URL") if zeabur else None) or "http://localhost:5173",
            secret_key=os.getenv("SECRET_KEY", "development-only-change-me"),
            room_ttl=float(os.getenv("ROOM_TTL", "7200")),
            reconnect_grace=float(os.getenv("RECONNECT_GRACE", "300")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_rooms=int(os.getenv("MAX_ROOMS", "1000")),
            max_websockets=int(os.getenv("MAX_CONNECTIONS", os.getenv("MAX_WEBSOCKETS", "5000"))),
            max_connections=int(os.getenv("MAX_CONNECTIONS", "5000")),
            room_creations_per_minute=int(os.getenv("ROOM_CREATIONS_PER_MINUTE", "10")),
            message_size_limit=int(os.getenv("MESSAGE_SIZE_LIMIT", "256000")),
            heartbeat_seconds=float(os.getenv("HEARTBEAT_SECONDS", "20")),
        )

    def validate_production(self) -> None:
        if not self.production:
            return
        if not self.domain or ":" in self.domain or "/" in self.domain:
            raise RuntimeError("DOMAIN must be a DNS hostname in production")
        if any(not host or any(char in host for char in "*/: \t\r\n") for host in self.trusted_hosts):
            raise RuntimeError("TRUSTED_HOSTS must contain explicit hostnames without scheme, port, or wildcard")
        if not 1 <= self.port <= 65535:
            raise RuntimeError("PORT must be between 1 and 65535 in production")
        if self.public_origin != f"https://{self.domain}":
            raise RuntimeError("PUBLIC_ORIGIN must equal https://DOMAIN in production")
        if not self.secret_key or self.secret_key == "development-only-change-me" or len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be a unique secret of at least 32 characters in production")

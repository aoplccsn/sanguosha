from __future__ import annotations

import json
from typing import Any

from sanguosha.version import APP_VERSION, PROTOCOL_VERSION, RELAY_PROTOCOL_VERSION

MAX_RELAY_MESSAGE_BYTES = 300_000
ROOM_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ROOM_CODE_LENGTH = 6
MESSAGE_TYPES = frozenset({
    "CREATE_ROOM", "ROOM_CREATED", "JOIN_ROOM", "ROOM_JOINED", "GUEST_JOINED",
    "CHANNEL_DATA", "CHANNEL_CLOSED", "CLOSE_ROOM", "ROOM_STATE",
    "HOST_RECONNECTING", "PING", "PONG", "ERROR",
})


class RelayProtocolError(ValueError):
    pass


def envelope(kind: str, **fields: Any) -> dict[str, Any]:
    payload = {
        "type": kind,
        "relay_version": RELAY_PROTOCOL_VERSION,
        "app_version": APP_VERSION,
        "game_protocol_version": PROTOCOL_VERSION,
        **fields,
    }
    validate(payload)
    return payload


def validate(payload: Any) -> None:
    if not isinstance(payload, dict) or payload.get("type") not in MESSAGE_TYPES:
        raise RelayProtocolError("unknown relay message")
    if payload.get("relay_version") != RELAY_PROTOCOL_VERSION:
        raise RelayProtocolError("中继协议版本不一致，请更新客户端")
    if payload.get("game_protocol_version") != PROTOCOL_VERSION:
        raise RelayProtocolError("游戏协议版本不一致，请更新客户端")
    if payload.get("app_version") != APP_VERSION:
        raise RelayProtocolError("游戏版本不一致，请更新客户端")


def encode(payload: dict[str, Any]) -> str:
    validate(payload)
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(data.encode("utf-8")) > MAX_RELAY_MESSAGE_BYTES:
        raise RelayProtocolError("relay message is too large")
    return data


def decode(data: str | bytes) -> dict[str, Any]:
    if isinstance(data, bytes):
        if len(data) > MAX_RELAY_MESSAGE_BYTES:
            raise RelayProtocolError("relay message is too large")
        data = data.decode("utf-8")
    elif len(data.encode("utf-8")) > MAX_RELAY_MESSAGE_BYTES:
        raise RelayProtocolError("relay message is too large")
    try:
        payload = json.loads(data)
    except (UnicodeError, ValueError) as exc:
        raise RelayProtocolError("malformed relay JSON") from exc
    validate(payload)
    return payload

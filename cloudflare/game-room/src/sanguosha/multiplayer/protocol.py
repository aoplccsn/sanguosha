"""Versioned JSON wire schema. No Python objects cross the trust boundary."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from sanguosha.engine.requests import Decision, PASS_RESPONSE, PendingRequest, RequestType
from sanguosha.model.ids import PlayerId
from sanguosha.projection import CardView, PlayerView, TableView

from sanguosha.version import PROTOCOL_VERSION

DEFAULT_GAME_PORT = 28765
MAX_MESSAGE_BYTES = 256_000
MESSAGE_TYPES = frozenset({
    "HELLO", "WELCOME", "CREATE_ROOM", "ROOM_CREATED", "JOIN_ROOM", "LEAVE_ROOM", "RECONNECT",
    "LOBBY_STATE", "READY", "START_GAME", "CONFIGURE_ROOM", "KICK_PLAYER", "KICKED",
    "DRAFT_REQUEST", "PROJECTION_UPDATE", "PENDING_REQUEST", "SUBMIT_DECISION",
    "DECISION_ACCEPTED", "DECISION_RESULT", "PUBLIC_EVENT", "PING", "PONG", "PLAYER_DISCONNECTED",
    "PLAYER_RECONNECTED", "TAKEOVER_AI", "GAME_OVER", "VERSION_MISMATCH", "ERROR",
})


class ProtocolError(ValueError):
    pass


def encode(message: dict[str, Any]) -> bytes:
    check_message(message)
    try:
        data = json.dumps(message, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError("message is not JSON serializable") from exc
    if len(data) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message is too large")
    return data + b"\n"


def decode(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message is too large")
    try:
        message = json.loads(data)
    except (UnicodeError, ValueError) as exc:
        raise ProtocolError("malformed JSON") from exc
    check_message(message)
    return message


def check_message(message: Any) -> None:
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        raise ProtocolError("message must have a type")
    if message["type"] not in MESSAGE_TYPES:
        raise ProtocolError("unknown message type")
    if message.get("version") != PROTOCOL_VERSION:
        raise ProtocolError("incompatible protocol version")


def envelope(kind: str, **fields: Any) -> dict[str, Any]:
    message = {"type": kind, "version": PROTOCOL_VERSION, **fields}
    check_message(message)
    return message


def serialize_projection(view: TableView) -> dict[str, Any]:
    """TableView is already viewer-specific; only its explicit fields go on wire."""
    return asdict(view)


def deserialize_projection(payload: dict[str, Any]) -> TableView:
    """Reconstruct display-only records, never a GameState."""
    def card(raw: dict) -> CardView:
        return CardView(**raw)

    def player(raw: dict) -> PlayerView:
        return PlayerView(**{**raw,
                             "equipment": tuple(card(x) for x in raw["equipment"]),
                             "judgments": tuple(card(x) for x in raw["judgments"]),
                             "skill_labels": tuple(raw["skill_labels"]),
                             "transformation_pool": tuple(raw.get("transformation_pool", ())),
                             "revealed_hand": tuple(card(x) for x in raw.get("revealed_hand", ())),
                             "special_piles": {key: tuple(card(x) for x in cards)
                                               for key, cards in raw.get("special_piles", {}).items()}})

    return TableView(tuple(player(x) for x in payload["players"]),
                     tuple(card(x) for x in payload["hand"]), payload["current_phase"],
                     payload["turn_number"], payload["deck_count"], payload["discard_count"],
                     payload["result"], card(payload["discard_top"]) if payload["discard_top"] else None,
                     tuple(card(x) for x in payload["shared_cards"]))


def serialize_request(request: PendingRequest, remaining_ms: int) -> dict[str, Any]:
    return {
        "request_id": request.request_id, "player_id": str(request.player_id),
        "request_type": request.request_type.value, "prompt": request.prompt,
        "choices": list(request.choices), "allowed_player_ids": list(request.allowed_player_ids),
        "required_definition_id": request.required_definition_id,
        "eligible_card_ids": list(request.eligible_card_ids), "allow_pass": request.allow_pass,
        "min_count": request.min_count, "max_count": request.max_count,
        "subject_player_id": request.subject_player_id, "remaining_ms": remaining_ms,
        "play_card_targets": {option: {"targets": list(spec[0]), "min": spec[1], "max": spec[2]}
                              for option, spec in request.play_card_targets.items()},
    }


def decision_from_wire(payload: Any, player_id: PlayerId) -> Decision:
    if not isinstance(payload, dict) or not isinstance(payload.get("request_id"), str):
        raise ProtocolError("decision requires request_id")
    value = payload.get("value")
    if isinstance(value, dict):
        if value == {"pass": True}:
            value = PASS_RESPONSE
        elif (set(value) == {"option", "targets"} and type(value["option"]) is str
              and type(value["targets"]) is list and len(value["targets"]) <= 8
              and all(type(item) is str for item in value["targets"])):
            value = {"option": value["option"], "targets": tuple(value["targets"])}
        else:
            raise ProtocolError("invalid decision value")
    elif isinstance(value, list):
        if not all(type(item) is str for item in value):
            raise ProtocolError("invalid decision list")
        value = tuple(value)
    elif type(value) not in (bool, str):
        raise ProtocolError("invalid decision value")
    return Decision(payload["request_id"], player_id, value)


def decision_to_wire(decision: Decision) -> dict[str, Any]:
    value = decision.value
    return {"request_id": decision.request_id,
            "value": {"pass": True} if value is PASS_RESPONSE else list(value) if isinstance(value, tuple)
            else {"option": value["option"], "targets": list(value["targets"])} if isinstance(value, dict) else value}

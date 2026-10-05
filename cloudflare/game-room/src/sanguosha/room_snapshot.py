"""Versioned authoritative room and lobby state for Durable Object storage."""

from __future__ import annotations

import json

from sanguosha.engine.rng import PythonRandomSource
from sanguosha.model.ids import PlayerId
from sanguosha.multiplayer.room import Controller, MultiplayerRoom, RoomPhase
from sanguosha.pregame import Pregame
from sanguosha.snapshot import _encode, _decode, restore_session, snapshot_session


ROOM_SNAPSHOT_SCHEMA_VERSION = 1


def snapshot_room(room: MultiplayerRoom) -> bytes:
    pregame = None
    if room.pregame is not None:
        pregame = {
            "identities": _encode(room.pregame.identities),
            "candidates": _encode(room.pregame.candidates),
            "stage": _encode(room.pregame.stage),
            "generals": _encode(room.pregame.generals),
            "human_id": str(room.pregame.human_id),
            "rng_state": _encode(room.pregame.rng._random.getstate()),
            "mode_id": room.pregame.mode_id,
        }
    data = {
        "schema_version": ROOM_SNAPSHOT_SCHEMA_VERSION,
        "phase": room.phase.value,
        "host_id": str(room.host_id) if room.host_id is not None else None,
        "seed": room.seed,
        "review_god_lvbu": room.review_god_lvbu,
        "mode_id": room.mode.mode_id,
        "allow_gods": room.allow_gods,
        "timeout_seconds": room.timeout_seconds,
        "seats": [{
            "player_id": str(seat.player_id),
            "name": seat.name,
            "controller": seat.controller.value,
            "ready": seat.ready,
            "token": seat.token,
            "connected": seat.connected,
        } for seat in room.seats.values()],
        "pregame": pregame,
        "draft_requests": _encode(room.draft_requests),
        "draft_deadlines": _encode(room.draft_deadlines),
        "session": json.loads(snapshot_session(room.session)) if room.session else None,
        "request_deadline": room.request_deadline,
        "ai_presentation": room.ai_presentation,
        "presentation_speed": room.presentation_speed,
        "ai_deadline": room.ai_deadline,
        "ai_wait_request": room._ai_wait_request,
        "last_request_id": room._last_request_id,
        "seen_events": room._seen_events,
        "revision": room._revision,
        "accepted_request_id": getattr(room, "accepted_request_id", None),
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def restore_room(blob: bytes) -> MultiplayerRoom:
    data = json.loads(blob)
    version = data.get("schema_version")
    if version != ROOM_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(f"incompatible RoomSnapshot schema: {version!r}")
    room = MultiplayerRoom(seed=data["seed"], timeout_seconds=data["timeout_seconds"],
                           review_god_lvbu=data.get("review_god_lvbu", False),
                           mode_id=data.get('mode_id', 'military-five'),
                           allow_gods=data.get('allow_gods', False))
    room.phase = RoomPhase(data["phase"])
    room.host_id = PlayerId(data["host_id"]) if data["host_id"] is not None else None
    for seat_data in data["seats"]:
        seat = room.seats[PlayerId(seat_data["player_id"])]
        seat.name = seat_data["name"]
        seat.controller = Controller(seat_data["controller"])
        seat.ready = seat_data["ready"]
        seat.token = seat_data["token"]
        # Connections are rebound from hibernating WebSocket attachments.
        seat.connected = False
        seat.send = None
    if data["pregame"] is not None:
        value = data["pregame"]
        rng = PythonRandomSource(0)
        rng._random.setstate(_decode(value["rng_state"]))
        room.pregame = Pregame(rng, _decode(value["identities"]),
                               _decode(value["candidates"]), _decode(value["stage"]),
                               _decode(value["generals"]), PlayerId(value["human_id"]),
                               value.get('mode_id', room.mode.mode_id))
    room.draft_requests = _decode(data["draft_requests"])
    room.draft_deadlines = _decode(data["draft_deadlines"])
    if data["session"] is not None:
        room.session = restore_session(json.dumps(data["session"], ensure_ascii=False,
                                          separators=(",", ":")).encode("utf-8"))
        if room.pregame is not None:
            room.pregame.rng = room.session.rng
    room.presentation_speed = data.get("presentation_speed", "normal")
    room.ai_presentation = data.get("ai_presentation", False)
    room.ai_deadline = data.get("ai_deadline")
    room._ai_wait_request = data.get("ai_wait_request")
    room.request_deadline = data["request_deadline"]
    room._last_request_id = data["last_request_id"]
    room._seen_events = data["seen_events"]
    room._revision = data["revision"]
    room.accepted_request_id = data.get("accepted_request_id")
    return room

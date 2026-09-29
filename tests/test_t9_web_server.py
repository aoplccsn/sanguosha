from __future__ import annotations

from fastapi.testclient import TestClient

from sanguosha.multiplayer.protocol import PROTOCOL_VERSION
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig


def message(kind: str, **fields):
    return {"type": kind, "version": PROTOCOL_VERSION, **fields}


def receive_until(socket, kind: str, limit: int = 20):
    for _ in range(limit):
        item = socket.receive_json()
        if item["type"] == kind:
            return item
    raise AssertionError(f"missing {kind}")


def test_health_and_version_endpoints():
    with TestClient(create_app(WebConfig())) as client:
        assert client.get("/health").json()["status"] == "ok"
        payload = client.get("/api/version").json()
        assert payload["protocol_version"] == PROTOCOL_VERSION
        assert payload["app_version"]
        assert payload["build_commit"]


def test_two_browser_room_ready_and_start():
    app = create_app(WebConfig())
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as host, client.websocket_connect("/ws") as guest:
            host.send_json(message("HELLO"))
            guest.send_json(message("HELLO"))
            receive_until(host, "WELCOME")
            receive_until(guest, "WELCOME")
            host.send_json(message("CREATE_ROOM", name="房主"))
            code = receive_until(host, "ROOM_CREATED")["room_code"]
            host_welcome = receive_until(host, "WELCOME")
            guest.send_json(message("JOIN_ROOM", room_code=code, name="来宾"))
            guest_welcome = receive_until(guest, "WELCOME")
            assert host_welcome["seat_id"] != guest_welcome["seat_id"]
            guest.send_json(message("READY", ready=True))
            lobby = receive_until(host, "LOBBY_STATE")
            while not any(seat["ready"] for seat in lobby["seats"]):
                lobby = receive_until(host, "LOBBY_STATE")
            host.send_json(message("START_GAME"))
            assert receive_until(host, "DRAFT_REQUEST")["identity"]
            assert receive_until(guest, "DRAFT_REQUEST")["identity"]


def test_reconnect_restores_private_draft_request():
    app = create_app(WebConfig())
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as first:
            first.send_json(message("HELLO"))
            receive_until(first, "WELCOME")
            first.send_json(message("CREATE_ROOM", name="房主"))
            code = receive_until(first, "ROOM_CREATED")["room_code"]
            welcome = receive_until(first, "WELCOME")
            first.send_json(message("START_GAME"))
            draft = receive_until(first, "DRAFT_REQUEST")
            assert len(draft["request"]["choices"]) == 10
        with client.websocket_connect("/ws") as restored:
            restored.send_json(message("HELLO"))
            receive_until(restored, "WELCOME")
            restored.send_json(message(
                "RECONNECT", room_code=code, name="房主", token=welcome["reconnect_token"]
            ))
            assert receive_until(restored, "WELCOME")["seat_id"] == welcome["seat_id"]
            assert receive_until(restored, "DRAFT_REQUEST")["request"]["request_id"] == draft["request"]["request_id"]

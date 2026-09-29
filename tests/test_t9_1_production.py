import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.version import PROTOCOL_VERSION


def production(**overrides):
    values = dict(production=True, domain="game.example.com",
                  public_origin="https://game.example.com", secret_key="s" * 48)
    values.update(overrides)
    return WebConfig(**values)


def test_production_requires_domain_origin_and_secret():
    for config in (production(secret_key="development-only-change-me"),
                   production(public_origin="https://other.example.com"),
                   production(domain="")):
        with pytest.raises(RuntimeError):
            create_app(config)


def test_production_rejects_untrusted_host_and_websocket_origin():
    with TestClient(create_app(production())) as client:
        assert client.get("/health", headers={"host": "evil.example.com"}).status_code == 400
        assert client.get("/health", headers={"host": "game.example.com"}).status_code == 200
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws", headers={"host": "game.example.com", "origin": "https://evil.example.com"}):
                pass


def test_production_limits_room_creations_per_client():
    headers = {"host": "game.example.com", "origin": "https://game.example.com"}
    with TestClient(create_app(production(room_creations_per_minute=1))) as client:
        with client.websocket_connect("/ws", headers=headers) as first:
            first.send_json({"type": "HELLO", "version": PROTOCOL_VERSION})
            assert first.receive_json()["type"] == "WELCOME"
            first.send_json({"type": "CREATE_ROOM", "version": PROTOCOL_VERSION, "name": "one"})
            assert first.receive_json()["type"] == "ROOM_CREATED"
        with client.websocket_connect("/ws", headers=headers) as second:
            second.send_json({"type": "HELLO", "version": PROTOCOL_VERSION})
            assert second.receive_json()["type"] == "WELCOME"
            second.send_json({"type": "CREATE_ROOM", "version": PROTOCOL_VERSION, "name": "two"})
            assert second.receive_json()["type"] == "ERROR"

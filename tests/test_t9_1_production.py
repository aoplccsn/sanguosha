import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.web import __main__ as web_main
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


def test_render_uses_platform_port_and_one_worker(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "friends.onrender.com")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://friends.onrender.com")
    monkeypatch.setenv("PORT", "12345")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.delenv("DOMAIN", raising=False)
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    config = WebConfig.from_env()
    assert (config.host, config.port, config.domain, config.public_origin) == (
        "0.0.0.0", 12345, "friends.onrender.com", "https://friends.onrender.com")
    config.validate_production()
    calls = []
    monkeypatch.setattr(web_main.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    web_main.main()
    assert calls[0][1]["host"] == "0.0.0.0"
    assert calls[0][1]["port"] == 12345
    assert calls[0][1]["workers"] == 1
    assert calls[0][1]["proxy_headers"] is False


def test_render_host_and_origin_are_exact(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "friends.onrender.com")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://friends.onrender.com")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.delenv("DOMAIN", raising=False)
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    with TestClient(create_app(WebConfig.from_env())) as client:
        assert client.get("/health", headers={"host": "friends.onrender.com"}).status_code == 200
        assert client.get("/api/version", headers={"host": "friends.onrender.com"}).status_code == 200
        assert client.get("/health", headers={"host": "other.onrender.com"}).status_code == 400
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws", headers={"host": "friends.onrender.com", "origin": "https://other.onrender.com"}):
                pass
        with client.websocket_connect("/ws", headers={"host": "friends.onrender.com", "origin": "https://friends.onrender.com"}) as socket:
            socket.send_json({"type": "HELLO", "version": PROTOCOL_VERSION})
            assert socket.receive_json()["type"] == "WELCOME"


def test_zeabur_uses_port_and_one_worker(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("ZEABUR", "true")
    monkeypatch.setenv("ZEABUR_WEB_DOMAIN", "friends.zeabur.app")
    monkeypatch.setenv("ZEABUR_WEB_URL", "https://friends.zeabur.app")
    monkeypatch.setenv("PORT", "31876")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.delenv("DOMAIN", raising=False)
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    config = WebConfig.from_env()
    assert config.production
    assert (config.host, config.port, config.domain, config.public_origin) == (
        "0.0.0.0", 31876, "friends.zeabur.app", "https://friends.zeabur.app")
    config.validate_production()
    calls = []
    monkeypatch.setattr(web_main.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    web_main.main()
    assert calls[0][1]["host"] == "0.0.0.0"
    assert calls[0][1]["port"] == 31876
    assert calls[0][1]["workers"] == 1
    assert calls[0][1]["proxy_headers"] is False


def test_zeabur_exact_host_origin_and_explicit_override(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("ZEABUR", "true")
    monkeypatch.setenv("ZEABUR_WEB_DOMAIN", "wrong.zeabur.app")
    monkeypatch.setenv("ZEABUR_WEB_URL", "https://wrong.zeabur.app")
    monkeypatch.setenv("DOMAIN", "friends.zeabur.app")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://friends.zeabur.app")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    with TestClient(create_app(WebConfig.from_env())) as client:
        assert client.get("/health", headers={"host": "friends.zeabur.app"}).status_code == 200
        assert client.get("/api/version", headers={"host": "friends.zeabur.app"}).status_code == 200
        assert client.get("/health", headers={"host": "wrong.zeabur.app"}).status_code == 400
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws", headers={"host": "friends.zeabur.app", "origin": "https://wrong.zeabur.app"}):
                pass
        with client.websocket_connect("/ws", headers={"host": "friends.zeabur.app", "origin": "https://friends.zeabur.app"}) as socket:
            socket.send_json({"type": "HELLO", "version": PROTOCOL_VERSION})
            assert socket.receive_json()["type"] == "WELCOME"

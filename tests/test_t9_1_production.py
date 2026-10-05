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


def test_back4app_uses_default_port_one_worker_and_strict_host_origin(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("ZEABUR", raising=False)
    monkeypatch.setenv("BACK4APP", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DOMAIN", "friends.example.b4a.run")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://friends.example.b4a.run")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.delenv("PORT", raising=False)
    config = WebConfig.from_env()
    assert (config.production, config.host, config.port) == (True, "0.0.0.0", 8000)
    calls = []
    monkeypatch.setattr(web_main.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    web_main.main()
    assert calls[0][1]["workers"] == 1
    assert calls[0][1]["proxy_headers"] is False
    with TestClient(create_app(config)) as client:
        headers = {"host": config.domain, "origin": config.public_origin}
        assert client.get("/health", headers=headers).status_code == 200
        assert client.get("/api/version", headers=headers).status_code == 200
        assert client.get("/health", headers={"host": "other.b4a.run"}).status_code == 400
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws", headers={"host": config.domain, "origin": "https://other.b4a.run"}):
                pass
        with client.websocket_connect("/ws", headers=headers) as socket:
            socket.send_json({"type": "HELLO", "version": PROTOCOL_VERSION})
            assert socket.receive_json()["type"] == "WELCOME"


def test_back4app_requires_assigned_domain_before_first_start(monkeypatch):
    monkeypatch.setenv("BACK4APP", "true")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    monkeypatch.delenv("DOMAIN", raising=False)
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    with pytest.raises(RuntimeError, match="DOMAIN"):
        WebConfig.from_env().validate_production()


def test_cn_container_uses_platform_port_same_origin_and_health(monkeypatch):
    for key in ("RENDER", "ZEABUR", "BACK4APP"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "34567")
    monkeypatch.setenv("DOMAIN", "game.example.cn")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://game.example.cn")
    monkeypatch.setenv("SECRET_KEY", "s" * 48)
    config = WebConfig.from_env()
    assert (config.host, config.port) == ("0.0.0.0", 34567)
    config.validate_production()
    calls = []
    monkeypatch.setattr(web_main.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    web_main.main()
    assert calls[0][1]["workers"] == 1
    with TestClient(create_app(config)) as client:
        headers = {"host": config.domain, "origin": config.public_origin}
        assert client.get("/api/health", headers=headers).json()["status"] == "ok"
        assert client.get("/api/version", headers=headers).status_code == 200
        with client.websocket_connect("/ws", headers=headers) as socket:
            socket.send_json({"type": "HELLO", "version": PROTOCOL_VERSION})
            assert socket.receive_json()["type"] == "WELCOME"


def test_container_serves_dist_outside_installed_package(monkeypatch, tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<h1>container spa</h1>", encoding="utf-8")
    (tmp_path / "assets" / "check.txt").write_text("asset ready", encoding="utf-8")
    monkeypatch.setenv("WEB_DIST_DIR", str(tmp_path))
    with TestClient(create_app(production())) as client:
        headers = {"host": "game.example.com"}
        assert "container spa" in client.get("/", headers=headers).text
        assert "container spa" in client.get("/room/ABC123", headers=headers).text
        assert client.get("/assets/check.txt", headers=headers).text == "asset ready"

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "cloudflare" / "game-room" / "src" / "main.py"


@pytest.fixture(scope="module")
def worker_module():
    js = types.ModuleType("js")
    js.WebSocketPair = object
    workers = types.ModuleType("workers")
    workers.DurableObject = type("DurableObject", (), {})
    workers.WorkerEntrypoint = type("WorkerEntrypoint", (), {})
    workers.Response = object
    old_js = sys.modules.get("js")
    old_workers = sys.modules.get("workers")
    sys.modules["js"] = js
    sys.modules["workers"] = workers
    try:
        spec = importlib.util.spec_from_file_location("t92_worker", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        yield module
    finally:
        if old_js is None:
            sys.modules.pop("js", None)
        else:
            sys.modules["js"] = old_js
        if old_workers is None:
            sys.modules.pop("workers", None)
        else:
            sys.modules["workers"] = old_workers


def test_room_codes_are_protocol_safe(worker_module):
    codes = {worker_module._room_code() for _ in range(1000)}
    assert len(codes) > 990
    assert all(worker_module._normalize_room_code(code.lower()) == code for code in codes)


@pytest.mark.parametrize("value", ["", "ABC", "ABCDEF0", "ABC10I", "ABC-12"])
def test_invalid_room_codes_are_rejected(worker_module, value):
    with pytest.raises(ValueError, match="invalid room code"):
        worker_module._normalize_room_code(value)


def test_worker_bundle_uses_authoritative_room_and_snapshot():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "MultiplayerRoom" in source
    assert "snapshot_room" in source
    assert "restore_room" in source
    assert "acceptWebSocket" in source
    assert "serializeAttachment" in source
    assert "json.dumps(value" in source
    assert "setAlarm" in source
    assert 'kind == "HELLO"' in source
    assert "self.room._send_current(pid)" in source
    assert "self.room = MultiplayerRoom(seed=seed" in source
    assert "mode_id=message.get('mode_id'" in source
    assert "asyncio.sleep" not in source

def test_worker_engine_bundle_matches_authoritative_source():
    source_root = ROOT / "src" / "sanguosha"
    worker_root = ROOT / "cloudflare" / "game-room" / "src" / "sanguosha"
    excluded = {"ui", "relay", "web"}
    source_files = {
        path.relative_to(source_root): path.read_bytes()
        for path in source_root.rglob("*.py")
        if not excluded.intersection(path.relative_to(source_root).parts)
    }
    worker_files = {
        path.relative_to(worker_root): path.read_bytes()
        for path in worker_root.rglob("*.py")
    }
    assert worker_files == source_files


def test_http_room_status_route(worker_module, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    calls = []

    class FakeResponse:
        @staticmethod
        def json(payload, status=200):
            return SimpleNamespace(status=status, payload=payload)

    class FakeStub:
        async def fetch(self, request):
            calls.append(("stub", request.url))
            return FakeResponse.json({"room_code": "ABC234", "phase": "IN_GAME"})

    class FakeRooms:
        def getByName(self, code):
            calls.append(("room", code))
            return FakeStub()

    class FakeAssets:
        async def fetch(self, request):
            calls.append(("assets", request.url))
            return SimpleNamespace(status=200, payload="<html>SPA</html>")

    monkeypatch.setattr(worker_module, "Response", FakeResponse)
    worker = worker_module.Default()
    worker.env = SimpleNamespace(GAME_ROOMS=FakeRooms(), ASSETS=FakeAssets())

    def get(path):
        request = SimpleNamespace(
            url=f"https://example.test{path}",
            method="GET",
            headers={},
        )
        return asyncio.run(worker.fetch(request))

    active = get("/api/rooms/abc234")
    assert active.status == 200
    assert active.payload == {"room_code": "ABC234", "phase": "IN_GAME"}
    assert calls == [
        ("room", "ABC234"),
        ("stub", "https://example.test/api/rooms/abc234"),
    ]

    calls.clear()
    invalid = get("/api/rooms/ABC10I")
    assert invalid.status == 400
    assert invalid.payload == {"error": "invalid room code"}
    assert calls == []

    spa = get("/room/ABC234")
    assert spa.status == 200
    assert spa.payload == "<html>SPA</html>"
    assert calls == [("assets", "https://example.test/room/ABC234")]


def test_worker_catalog_matches_web_and_production_draft(worker_module, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from fastapi.testclient import TestClient
    from sanguosha.content.characters.standard import ALL_GENERAL_POOL, PLAYABLE_GENERAL_POOL
    from sanguosha.web.app import app

    class FakeResponse:
        @staticmethod
        def json(payload, status=200):
            return SimpleNamespace(status=status, payload=payload)

    monkeypatch.setattr(worker_module, "Response", FakeResponse)
    worker = worker_module.Default()
    request = SimpleNamespace(url="https://example.test/api/catalog/generals", method="GET", headers={})
    worker_catalog = asyncio.run(worker.fetch(request)).payload
    web_catalog = TestClient(app).get("/api/catalog/generals").json()
    python_ids = {str(character.id) for character in ALL_GENERAL_POOL}
    draft_ids = {str(character.id) for character in PLAYABLE_GENERAL_POOL}
    worker_ids = {row["id"] for row in worker_catalog}
    web_ids = {row["id"] for row in web_catalog}
    assert len(worker_catalog) == len(web_catalog) == len(python_ids) == len(draft_ids) == 108
    assert worker_ids == web_ids == python_ids == draft_ids
    assert {row["id"] for row in worker_catalog if row["id"].startswith("yj2011_")} == {
        "yj2011_zhang_chunhua", "yj2011_yu_jin", "yj2011_cao_zhi",
        "yj2011_fa_zheng", "yj2011_ma_su", "yj2011_xu_shu",
        "yj2011_ling_tong", "yj2011_xu_sheng", "yj2011_wu_guotai",
        "yj2011_chen_gong", "yj2011_gao_shun",
    }

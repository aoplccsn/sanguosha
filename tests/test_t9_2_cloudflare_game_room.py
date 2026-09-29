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
    assert "self.room.seed = seed" in source
    assert "asyncio.sleep" not in source

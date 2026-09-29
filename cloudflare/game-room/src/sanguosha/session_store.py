from __future__ import annotations

import json
import time

from .paths import local_app_data
from .version import APP_VERSION

SESSION_MAX_AGE_SECONDS = 86400


def session_path():
    return local_app_data() / "session.json"


def save_session(*, relay_url: str, room_code: str, player_id: str, reconnect_token: str) -> None:
    payload = {
        "relay_url": relay_url,
        "room_code": room_code,
        "player_id": player_id,
        "reconnect_token": reconnect_token,
        "game_version": APP_VERSION,
        "timestamp": int(time.time()),
    }
    path = session_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_session(*, max_age: int = SESSION_MAX_AGE_SECONDS):
    try:
        payload = json.loads(session_path().read_text(encoding="utf-8"))
        required = {"relay_url", "room_code", "player_id", "reconnect_token", "game_version", "timestamp"}
        if not required.issubset(payload) or payload["game_version"] != APP_VERSION:
            return None
        if time.time() - float(payload["timestamp"]) > max_age:
            clear_session()
            return None
        return payload
    except (OSError, ValueError, TypeError):
        return None


def clear_session() -> None:
    try:
        session_path().unlink()
    except FileNotFoundError:
        pass

from __future__ import annotations

import json
import os

from .paths import resource_path


def defaults() -> dict:
    try:
        return json.loads(resource_path("config", "defaults.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def relay_url() -> str:
    return os.environ.get(
        "SANGUOSHA_RELAY_URL",
        defaults().get("relay_url", "wss://relay.example.invalid"),
    )

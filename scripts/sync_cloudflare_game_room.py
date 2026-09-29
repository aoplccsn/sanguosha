"""Copy the authoritative engine package into the Python Worker bundle."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "sanguosha"
TARGET = ROOT / "cloudflare" / "game-room" / "src" / "sanguosha"

if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "ui", "relay", "web"))
print(TARGET)

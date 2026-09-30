import json
from pathlib import Path
from PySide6.QtGui import QImageReader

from sanguosha.content.characters.standard import PLAYABLE_57_GENERAL_POOL


def test_all_32_ordinary_myth_portraits_are_real_manifest_assets():
    root = Path(__file__).resolve().parents[1] / "assets"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    ordinary = [c for c in PLAYABLE_57_GENERAL_POOL if c.metadata.get("pack") != "standard"]
    assert len(ordinary) == 32
    hashes = set()
    for character in ordinary:
        key = f"general.{character.id}"
        path = root / manifest[key]
        assert path.is_file(), key
        reader = QImageReader(str(path))
        assert reader.canRead(), key
        assert reader.size().width() >= 280 and reader.size().height() >= 360, key
        digest = path.read_bytes()
        assert digest not in hashes, key
        hashes.add(digest)
    assert len(hashes) == 32

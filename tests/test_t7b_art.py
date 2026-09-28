"""Every standard general resolves to a distinct readable portrait."""

import hashlib
import json
from pathlib import Path

from PySide6.QtGui import QImageReader

from sanguosha.content.characters.standard import STANDARD_25_GENERAL_POOL


def test_twenty_five_standard_portraits_are_manifested_readable_and_unique():
    assets = Path(__file__).resolve().parents[1] / 'assets'
    manifest = json.loads((assets / 'manifest.json').read_text(encoding='utf-8'))
    hashes = set()
    for character in STANDARD_25_GENERAL_POOL:
        key = f'general.{character.id}'
        path = assets / manifest[key]
        assert path.is_file(), key
        reader = QImageReader(str(path))
        assert reader.canRead(), key
        assert reader.size().width() >= 280 and reader.size().height() >= 360, key
        digest = hashlib.sha256(path.read_bytes()).digest()
        assert digest not in hashes, key
        hashes.add(digest)
    assert len(hashes) == 25

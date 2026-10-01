"""The reviewed V3 portraits are the images resolved by the live manifest."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from PySide6.QtGui import QImageReader

from sanguosha.content.characters.standard import PLAYABLE_57_GENERAL_POOL, STANDARD_25_GENERAL_POOL
from sanguosha.ui.resources import RESOURCES


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "t10_art"


def test_all_playable_v3_portraits_are_live_and_readable():
    inventory = json.loads((ART / "v3_review" / "portrait_inventory.json").read_text(encoding="utf-8"))
    readiness = json.loads((ART / "v3_review" / "candidate_readiness.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "assets" / "manifest.json").read_text(encoding="utf-8"))
    assert len(inventory) == len(PLAYABLE_57_GENERAL_POOL) == 57
    assert len(STANDARD_25_GENERAL_POOL) == 25
    assert Counter(row["pack"] for row in inventory) == {
        "standard": 25, "wind": 8, "fire": 8, "forest": 8, "mountain": 8,
    }
    assert {row["runtime_general_id"] for row in inventory} == {str(c.id) for c in PLAYABLE_57_GENERAL_POOL}
    reviewed = {candidate["general_id"]: candidate["sha256"]
                for pack in readiness["packs"].values() for candidate in pack["candidates"]}
    assert len(reviewed) == 57

    digests = set()
    for row in inventory:
        key = f"general.{row['runtime_general_id']}"
        live = ROOT / "assets" / manifest[key]
        assert live == ROOT / row["当前资源路径"]
        assert hashlib.sha256(live.read_bytes()).hexdigest() == reviewed[row["general_id"]], key
        reader = QImageReader(str(live))
        assert reader.canRead() and not reader.read().isNull(), key
        digest = hashlib.sha256(live.read_bytes()).hexdigest()
        assert digest not in digests, key
        digests.add(digest)
        portrait = RESOURCES.general_portrait(str(row["runtime_general_id"]), row["中文名"])
        assert not portrait.isNull() and portrait.width() == 280 and portrait.height() == 360, key

    zhang = next(row for row in inventory if row["general_id"] == "wind_zhang_jiao")
    assert reviewed["wind_zhang_jiao"] == zhang["sha256"]

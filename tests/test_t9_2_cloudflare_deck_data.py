import json
from pathlib import Path

from sanguosha.engine import deck
from sanguosha.engine.cloudflare_deck_data import MANIFEST
from sanguosha.engine.rng import PythonRandomSource


def test_generated_worker_manifest_matches_canonical_json(monkeypatch, tmp_path):
    canonical = Path(__file__).resolve().parents[1] / "data" / "decks" / "classic_military.json"
    assert MANIFEST == json.loads(canonical.read_text(encoding="utf-8"))
    monkeypatch.setattr(deck, "CLASSIC_MILITARY_MANIFEST", tmp_path / "not-bundled.json")
    cards, draw_zone = deck.classic_military_deck(PythonRandomSource(6))
    assert len(cards) == len(draw_zone.card_ids) == 160

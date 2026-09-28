"""Every newly playable definition resolves to its own genuine PNG asset."""
import hashlib,json
from pathlib import Path
from PySide6.QtGui import QImage
from sanguosha.session import GameSession
from sanguosha.ui.resources import ResourceManager

def test_all_40_new_definitions_have_independent_decodable_original_art():
    root=Path(__file__).resolve().parents[1]/'assets'
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    s=GameSession.new_game(military=True)
    ids={c.definition_id for c in s.state.cards.values()}-{'basic.slash','basic.dodge','basic.peach'}
    assert len(ids)==40
    resources=ResourceManager(root)
    hashes=[]
    for definition in ids:
        relative=manifest[definition]
        assert relative.startswith('cards/military/')
        if definition.startswith('equipment.'):assert relative.endswith('-v2.png')
        path=root/relative
        assert path.is_file() and not QImage(str(path)).isNull()
        assert not resources.card_art(definition).isNull()
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
    assert len(set(hashes))==40

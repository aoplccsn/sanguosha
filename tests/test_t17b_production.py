import hashlib,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sanguosha.content.characters.standard import ALL_GENERAL_POOL,PLAYABLE_GENERAL_POOL,ORDINARY_GENERAL_POOL,ALL_65_GENERAL_POOL,ALL_SKILL_CATALOGUE
from sanguosha.content.characters.yj2011 import YJ2011_GENERAL_POOL
from sanguosha.web.app import app
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.engine.requests import Decision
from sanguosha.engine.skills import SkillRegistry
from sanguosha.engine.yj2011_tier3 import hand
from sanguosha.projection import project_for_human
from test_t17b_tier1 import game
from test_t17b_tier3 import active
from test_t6_military_basics import put


def test_production_76_registry_catalog_and_locked_11():
    assert len(ALL_GENERAL_POOL)==len(PLAYABLE_GENERAL_POOL)==108
    assert len(ALL_65_GENERAL_POOL)==65 and len(ORDINARY_GENERAL_POOL)==92
    registry=SkillRegistry(); ids={str(c.id) for c in YJ2011_GENERAL_POOL}
    catalog=TestClient(app).get('/api/catalog/generals').json()
    assert len(catalog)==108 and len({c['id'] for c in catalog})==108
    skills={str(s.id):s for s in ALL_SKILL_CATALOGUE}
    yj=[s.id for s in ALL_SKILL_CATALOGUE if s.metadata.get('pack')=='yj2011']
    assert len(yj)==len(set(yj))==19
    for row in catalog:
        assert row['implemented'] and row['playable']
        if row['id'] in ids:
            assert row['pack']=='yj2011' and row['skills']
            assert row['portrait'].rsplit('.', 1)[0] == f"/assets/generals/{row['kingdom']}/{row['id']}"
            assert (Path(__file__).resolve().parents[1] / row['portrait'].lstrip('/')).is_file()
            c=registry.characters[row['id']]
            assert c.metadata['implemented'] and c.metadata['playable'] and not c.metadata['development_only']
            assert [s['description'] for s in row['skills']]==[skills[str(sid)].description for sid in c.skill_ids]
    assert len([c for c in catalog if c['id'].startswith(('yj2012','yj2013'))])==23


@pytest.mark.parametrize('mode',['military-five','military-eight'])
def test_production_draft_and_ai_selection_cover_all_yj2011(mode):
    required={str(c.id) for c in YJ2011_GENERAL_POOL}; offers=set(); selected=set()
    for seed in range(50):
        room=MultiplayerRoom(seed=seed,mode_id=mode)
        pid,_=room.join('host',lambda _:None); room.start(pid)
        r=room.draft_requests[pid]; offers.update(r.choices)
        choice=next((c for c in r.choices if c in required),r.choices[0])
        room.submit(pid,Decision(r.request_id,pid,choice))
        selected.update(str(p.character_id) for p in room.session.state.players.values())
    assert required<=offers and required<=selected


def test_jinjiu_projection_owner_sees_slash_physical_identity_unchanged():
    s=game(); active(s,'gao_shun'); cid=put(s,'basic.wine')
    view=project_for_human(s.state,s.definitions,'p1',s.character_names)
    card=next(c for c in view.hand if c.card_id==cid)
    assert card.definition_id=='basic.slash' and card.name=='杀'
    assert s.state.cards[cid].definition_id=='basic.wine'


def test_dynamic_media_all_hashes_unchanged():
    root=Path(__file__).resolve().parents[1]
    baseline=json.loads((root/'docs/t17/t17b_dynamic_hash_baseline.json').read_text(encoding='utf-8'))
    assert any('wind_zhang_jiao.mp4' in p for p in baseline)
    assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==sha for p,sha in baseline.items() if not p.endswith('.panel.mp4'))

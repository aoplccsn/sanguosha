import json
from pathlib import Path
from fastapi.testclient import TestClient
from sanguosha.web.app import create_app
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.engine.card_use import UseCardAction
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.enums import EquipmentSlot
from sanguosha.projection import project_for_human
from dataclasses import asdict
from test_t6_military_basics import game, put

def test_production_dist_catalog_and_all_card_art():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'web/dist/assets/manifest.json').read_text(encoding='utf-8'))
    client=TestClient(create_app())
    catalog=client.get('/api/catalog/generals').json()
    assert len(catalog)==76 and len({row['portrait'] for row in catalog})==76
    paths=[row['portrait'] for row in catalog]+['/assets/'+value for key,value in manifest.items() if key.startswith(('basic.','trick.','delayed.','equipment.'))]
    for path in paths:
        response=client.get(path)
        assert response.status_code==200, path
        assert response.headers['content-type'].startswith('image/') and len(response.content)>100
    assert all((root/'web/dist/assets'/v).is_file() for v in manifest.values())

def test_hidden_target_request_and_projection_have_no_secret_card_details():
    s=game(); secret=put(s,'basic.peach','p2'); source=put(s,'trick.snatch')
    put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    s.engine.start_action(UseCardAction('snatch','p1',source,('p2',)))
    from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
    while s.engine.pending_request.request_type is not RequestType.CHOOSE_CARD:
        req=s.engine.pending_request
        s.engine.submit_decision(Decision(req.request_id, req.player_id, PASS_RESPONSE))
    room=MultiplayerRoom();room.session=s
    payload=room._request_payload(s.engine.pending_request)
    assert secret not in json.dumps(payload)
    assert any(cid.startswith('hidden-hand:') for cid in payload['eligible_card_ids'])
    projection=asdict(project_for_human(s.state,s.definitions,'p1',s.character_names))
    assert secret not in json.dumps(projection)
    assert projection['hand']
    opponent=next(p for p in projection['players'] if p['player_id']=='p2')
    assert opponent['revealed_hand']==() and 'hand' not in opponent

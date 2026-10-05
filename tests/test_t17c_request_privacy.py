import json
from types import SimpleNamespace
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.engine.yj2012 import YJ2012Action
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.multiplayer.choice_labels import CHOICE_NAMES
from test_t6_military_basics import put
from test_t17c_juece import empty


def test_chengxiang_public_candidates_have_rank_labels_and_restore():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_cao_chong'
    s.engine.start_action(YJ2013Action('skill','p1','chengxiang'));answer(s,True)
    room=MultiplayerRoom();room.session=s
    r=s.engine.pending_request;p=room._request_payload(r)
    assert set(r.eligible_card_ids)<=set(p['choice_labels'])
    assert all(str(s.state.cards[c].rank) in p['choice_labels'][c] for c in r.eligible_card_ids)
    s=restore(s);room.session=s
    assert room._request_payload(s.engine.pending_request)==p


def test_anxu_hidden_choice_labels_never_include_physical_ids():
    s=setup('bu_lianshi');empty(s,'p2');put(s,'basic.dodge','p2')
    s.engine.start_action(YJ2012Action('anxu','p1','anxu'));answer(s,'p2');answer(s,'p3')
    r=s.engine.pending_request;room=MultiplayerRoom();room.session=s
    payload=room._request_payload(r);serialized=json.dumps(payload)
    assert all(c not in serialized for c in r.eligible_card_ids)
    assert all(c.startswith('hidden-hand:') for c in payload['eligible_card_ids'])
    assert set(payload['choice_labels'])==set(payload['eligible_card_ids'])
    s=restore(s);room.session=s
    assert room._request_payload(s.engine.pending_request)==payload


def test_new_fixed_branch_labels_explain_effects_in_chinese():
    for name in ('default','jiang','chi','continue','finish'):
        assert any('\u3400'<=c<='\u9fff' for c in CHOICE_NAMES[name])

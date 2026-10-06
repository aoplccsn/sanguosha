from test_t19_lusu import setup
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.mobile_gods import MobileGodAction
from sanguosha.engine.military_basics import MilitaryDamageAction, MilitaryStrike
from sanguosha.model.zones import ZoneRef, ZoneType


def sunce():
    s = setup(); p = s.state.players['p1']; p.character_id = 'mobile_god_sunce'; p.hp = 1; p.max_hp = 6
    return s


def test_yingba_both_max_cost_mark():
    s = sunce(); before = s.state.players['p2'].max_hp
    s.engine.start_action(MobileGodAction('yingba', 'p1', 'yingba')); answer(s, 'p2')
    assert s.state.players['p1'].max_hp == 5
    assert s.state.players['p2'].max_hp == before - 1
    assert s.state.players['p2'].marks['pingding'] == 1
    assert s.state.play_usage.count('skill.yingba') == 1


def test_pinghe_prevent_packet_give_and_mark():
    s = sunce(); p = s.state.players['p1']; before = len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    s.engine.start_action(MilitaryDamageAction('hurt', 'p2', 'p1', 3))
    assert '冯河' in s.engine.pending_request.prompt
    answer(s, 'p3'); card = s.engine.pending_request.eligible_card_ids[0]; answer(s, card)
    assert p.hp == 1 and p.max_hp == 5
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before - 1
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))
    assert s.state.players['p2'].marks['pingding'] == 1


def test_fuhai_marked_target_cannot_dodge():
    s = sunce(); target = s.state.players['p2']; target.marks['pingding'] = 1
    put(s, 'basic.dodge', 'p2'); slash = put(s, 'basic.slash', 'p1')
    hp = target.hp
    s.engine.start_action(MilitaryStrike('slash', 'p1', 'p2', slash, 'basic.dodge'))
    assert s.engine.pending_request is None
    assert target.hp == hp - 1

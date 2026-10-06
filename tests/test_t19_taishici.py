from test_t19_lusu import setup
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.mobile_gods import MobileGodAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.enums import EquipmentSlot
from sanguosha.snapshot import snapshot_session, restore_session


def taishici():
    s = setup(); s.state.players['p1'].character_id = 'mobile_god_taishici'
    return s


def test_powei_simultaneous_move_then_success():
    s = taishici(); key = 'wei:p1'; s.state.players['p2'].marks[key] = 2; s.state.players['p3'].marks[key] = 1
    s.engine.start_action(MobileGodAction('move', 'p1', 'powei_start', 'p1'))
    assert s.state.players['p3'].marks[key] == 2
    assert s.state.players['p4'].marks[key] == 1
    assert key not in s.state.players['p2'].marks
    for p in s.state.players.values(): p.marks.pop(key, None)
    s.engine.start_action(MobileGodAction('success', 'p1', 'powei_start', 'p1'))
    assert s.state.players['p1'].marks['powei_success'] == 1
    assert s.skills.has(s.state, 'p1', 'shenzhu')


def test_powei_failure_once_recovers_and_clears_equipment():
    s = taishici(); p = s.state.players['p1']; p.hp = 1
    put(s, 'equipment.weapon.crossbow', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    s.state.players['p2'].marks['wei:p1'] = 1
    s.engine.start_action(MilitaryDamageAction('lethal', 'p2', 'p1', 2))
    assert p.is_alive and p.hp == 1 and p.marks['powei_failed'] == 1
    assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON))
    assert 'wei:p1' not in s.state.players['p2'].marks
    assert not s.skills.has(s.state, 'p1', 'shenzhu')


def test_powei_hidden_hand_and_shenzhu_restore():
    s = taishici(); s.state.players['p2'].marks['wei:p1'] = 1
    before = len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    s.engine.start_action(MobileGodAction('take', 'p1', 'powei_start', 'p2'))
    assert not s.engine.pending_request.eligible_card_ids
    answer(s, 'take_hand')
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 1
    s.engine.start_action(MobileGodAction('draw', 'p1', 'shenzhu'))
    s = restore_session(snapshot_session(s)); answer(s, 'draw1_quota')
    assert s.state.players['p1'].marks['slash_quota_bonus'] == 1
    s.engine.start_action(MobileGodAction('draw3', 'p1', 'shenzhu')); answer(s, 'draw3_stop')
    assert s.state.players['p1'].marks['slash_prohibited'] == 1

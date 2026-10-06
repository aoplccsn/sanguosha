from test_t17b_tier1 import game, answer
from test_t6_military_basics import put
from sanguosha.engine.mobile_gods import MobileGodAction
from sanguosha.model.enums import Phase, EquipmentSlot, Identity
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.projection import project_for_human


def setup():
    s = game(); s.state.players['p1'].character_id = 'mobile_god_lusu'
    s.state.current_player_id = 'p1'; s.state.current_phase = Phase.PLAY
    s.state.play_usage = PlayUsageState('p1', 1)
    return s


def test_dingzhou_give_then_take_fields_restore():
    s = setup()
    field = put(s, 'equipment.weapon.crossbow', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    s.engine.start_action(MobileGodAction('dingzhou', 'p1', 'dingzhou'))
    answer(s, 'p2')
    request = s.engine.pending_request
    s = restore_session(snapshot_session(s)); assert s.engine.pending_request == request
    card = request.eligible_card_ids[0]; answer(s, (card,))
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert field in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert s.state.play_usage.count('skill.dingzhou') == 1


def test_zhimeng_ceil_shuffle_conservation_and_decline():
    s = setup(); put(s, 'basic.slash', 'p1')
    first = s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    second = s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    s.engine.start_action(MobileGodAction('decline', 'p1', 'zhimeng')); answer(s, False)
    assert s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')) == first
    s.engine.start_action(MobileGodAction('share', 'p1', 'zhimeng')); answer(s, True)
    s = restore_session(snapshot_session(s)); answer(s, 'p2')
    a = s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')); b = s.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    assert len(a) == (len(first) + len(second) + 1) // 2
    assert set(a + b) == set(first + second)
    projection = project_for_human(s.state, s.definitions, 'p3', s.character_names)
    assert not any(card in str(projection) for card in a + b)


def test_tamo_preserves_lord_and_updates_seats():
    s = setup()
    nonlords = tuple(q for q in s.state.seat_order if s.state.players[q].identity is not Identity.LORD)
    lord = next(q for q in s.state.seat_order if q not in nonlords)
    index = s.state.seat_order.index(lord)
    s.engine.start_action(MobileGodAction('tamo', 'p1', 'tamo')); answer(s, True)
    answer(s, tuple(reversed(nonlords)))
    assert s.state.seat_order[index] == lord
    assert tuple(q for q in s.state.seat_order if q != lord) == tuple(reversed(nonlords))
    assert all(s.state.players[q].seat == i for i,q in enumerate(s.state.seat_order))

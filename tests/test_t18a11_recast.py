"""Classic recast is neither card use nor discard; real request and reconnect paths."""
from dataclasses import replace
import pytest
from sanguosha.session import GameSession
from sanguosha.model.enums import Phase, Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.fire import FireViewAsTrick
from sanguosha.engine.events import CardUsedEvent, CardResolvedEvent, CardMovedEvent
from sanguosha.engine.requests import Decision
from sanguosha.snapshot import snapshot_session, restore_session
from test_t6_military_basics import put


def setup():
    s = GameSession.new_game(military=True, five_generals=True)
    s.state.current_player_id = 'p1'; s.state.current_phase = Phase.PLAY
    s.state.play_usage = PlayUsageState('p1', s.state.turn_number)
    return s


@pytest.mark.parametrize('skill', ('jizhi', 'wumou', 'jilue'))
def test_physical_iron_chain_recast_skips_use_skill_windows(skill):
    s = setup(); p = s.state.players['p1']
    p.granted_skills[skill] = 'audit'; p.marks.update(ren=1, rage=1)
    cid = put(s, 'trick.iron_chain')
    before = len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    s.engine.start_action(UseCardAction('recast', 'p1', cid))
    s = restore_session(snapshot_session(s))
    req = s.engine.pending_request
    s.engine.submit_decision(Decision(req.request_id, 'p1', ()))
    assert s.engine.pending_request is None
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before
    assert s.state.players['p1'].marks['ren'] == 1
    assert s.state.players['p1'].marks['rage'] == 1
    assert not any(isinstance(e, (CardUsedEvent, CardResolvedEvent)) and e.card_id == cid for e in s.events.events)
    assert s.state.play_usage.count('trick.iron_chain') == 0
    moves = [e for e in s.events.events if isinstance(e, CardMovedEvent)
             and cid in e.card_ids and e.to_zone.zone_type is ZoneType.DISCARD_PILE]
    assert len(moves) == 1 and moves[0].reason == 'recast'
    s.state.__post_init__()


@pytest.mark.parametrize('acquired', (False, True))
def test_lianhuan_recast_is_not_used_or_discarded_and_keeps_one_draw(acquired):
    s = setup(); p = s.state.players['p1']
    p.character_id = 'mountain_zuoci' if acquired else 'fire_pang_tong'
    if acquired:
        p.transformation_pool = ['fire_pang_tong'];p.active_transformation = 'fire_pang_tong';p.transformation_skill = 'lianhuan'
    cid = put(s, 'basic.peach')
    s.state.cards[cid] = replace(s.state.cards[cid], suit=Suit.CLUB)
    before = len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    s.engine.start_action(FireViewAsTrick('recast-lianhuan', 'p1', cid, 'lianhuan'))
    s = restore_session(snapshot_session(s));req = s.engine.pending_request
    s.engine.submit_decision(Decision(req.request_id, 'p1', ()))
    assert s.engine.pending_request is None
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before
    assert not any(isinstance(e, CardUsedEvent) and e.card_id == cid for e in s.events.events)
    assert s.state.play_usage.count('trick.iron_chain') == 0
    moves = [e for e in s.events.events if isinstance(e, CardMovedEvent)
             and cid in e.card_ids and e.to_zone.zone_type is ZoneType.DISCARD_PILE]
    assert len(moves) == 1 and moves[0].reason == 'recast'
    s.state.__post_init__()



def test_recast_public_faces_are_anonymous_and_desktop_log_is_distinct():
    from sanguosha.multiplayer.room import MultiplayerRoom
    from sanguosha.ui.log_panel import describe_event
    s = setup(); cid = put(s, 'trick.iron_chain')
    s.engine.start_action(UseCardAction('recast-face', 'p1', cid, targets_confirmed=True))
    assert s.engine.pending_request is None
    event = next(e for e in s.events.events if isinstance(e, CardMovedEvent)
        and cid in e.card_ids and e.to_zone.zone_type is ZoneType.DISCARD_PILE)
    room = MultiplayerRoom(); room.session = s
    public = room._public_event(event)
    assert public['reason'] == 'recast'
    assert public['cards'][0]['definition_id'] == 'trick.iron_chain'
    assert public['cards'][0]['card_id'] == 'public-card'
    assert cid not in str(public)
    assert '\u91cd\u94f8' in describe_event(event, s.state, s.definitions)


def test_targeted_iron_chain_still_is_use_and_keeps_jizhi_window():
    s = setup(); s.state.players['p1'].granted_skills['jizhi'] = 'audit'
    cid = put(s, 'trick.iron_chain')
    s.engine.start_action(UseCardAction('targeted-chain', 'p1', cid, ('p2',)))
    assert s.engine.pending_request.request_id == 'targeted-chain:jizhi'
    req = s.engine.pending_request
    s.engine.submit_decision(Decision(req.request_id, req.player_id, False))
    while s.engine.pending_request:
        req = s.engine.pending_request
        s.engine.submit_decision(Decision(req.request_id, req.player_id, req.timeout_value()))
    assert s.state.players['p2'].chained
    assert s.state.play_usage.count('trick.iron_chain') == 1
    assert sum(isinstance(e, CardUsedEvent) and e.card_id == cid for e in s.events.events) == 1


def test_recast_does_not_count_for_jingce_or_consume_qiaoshui_success():
    from sanguosha.engine.yj2013 import cards_used_this_turn
    s = setup(); p = s.state.players['p1']
    p.granted_skills['qiaoshui'] = 'audit'
    p.marks['qiaoshui_success'] = s.state.turn_number
    cid = put(s, 'trick.iron_chain')
    before = cards_used_this_turn(s.events.events, 'p1')
    s.engine.start_action(UseCardAction('recast-no-use', 'p1', cid, targets_confirmed=True))
    assert s.engine.pending_request is None
    assert cards_used_this_turn(s.events.events, 'p1') == before
    assert p.marks['qiaoshui_success'] == s.state.turn_number


@pytest.mark.parametrize('restriction', ('qiaoshui', 'qianxi'))
def test_use_prohibition_does_not_forbid_recast_but_still_forbids_targets(restriction):
    from sanguosha.engine.card_rules import InvalidCardUse
    s = setup(); cid = put(s, 'trick.iron_chain')
    if restriction == 'qiaoshui':
        s.state.players['p1'].marks['qiaoshui_trick_lock'] = s.state.turn_number
    else:
        s.state.metadata['qianxi_limits'] = {'p2': {'target': 'p1',
            'color': s.state.cards[cid].color.value, 'turn': s.state.turn_number}}
    handler = s.engine.registry.handler_for(UseCardAction('probe', 'p1', cid))
    assert handler.validator.can_offer(s.state, 'p1', cid)
    with pytest.raises(InvalidCardUse):
        handler.validate_start(s.state, UseCardAction('blocked-use', 'p1', cid, ('p2',)))
    s.engine.start_action(UseCardAction('allowed-recast', 'p1', cid, targets_confirmed=True))
    assert s.engine.pending_request is None
    assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

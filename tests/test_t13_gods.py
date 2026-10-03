"""Targeted classic God-general rule tests."""

from dataclasses import replace

from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.gods import WushenUse, WuhunDeathAction, ShelieAction, GongxinAction, QinyinAction, YeyanAction
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import Phase, Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session


def test_wushen_heart_card_uses_real_slash_pipeline():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_guanyu'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card] = replace(state.cards[card], suit=Suit.HEART,
                                definition_id='basic.peach')
    session.engine.start_action(WushenUse('wushen', 'p1', card))
    request = session.engine.pending_request
    assert 'p3' in request.allowed_player_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p3'))
    for _ in range(20):
        request = session.engine.pending_request
        if request is None:
            break
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                request.timeout_value()))
    assert state.play_usage.count('basic.slash') == 1
    assert card in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_wuhun_nonpeach_judgment_kills_max_nightmare_target():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_guanyu'
    state.players['p2'].marks['nightmare'] = 2
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    state.cards[top] = replace(state.cards[top], definition_id='basic.slash')
    session.engine.start_action(WuhunDeathAction('wuhun-death', 'p1'))
    assert not state.players['p2'].is_alive


def test_wuhun_nightmare_mark_survives_snapshot():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_god_guanyu'
    session.state.players['p2'].marks['nightmare'] = 3
    restored = restore_session(snapshot_session(session))
    assert restored.state.players['p2'].marks['nightmare'] == 3


def test_shelie_replaces_draw_with_one_card_per_suit():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_lvmeng'
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:5]
    for cid, suit in zip(top, (Suit.HEART, Suit.HEART, Suit.CLUB,
                               Suit.DIAMOND, Suit.SPADE)):
        state.cards[cid] = replace(state.cards[cid], suit=suit)
    session.engine.start_action(ShelieAction('shelie', 'p1'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    for cid in (top[0], top[2], top[3], top[4]):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', cid))
    assert all(cid in state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
               for cid in (top[0], top[2], top[3], top[4]))
    assert top[1] in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert state.players['p1'].marks['skip_draw'] == 1


def test_gongxin_places_selected_heart_on_draw_top():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'wind_god_lvmeng'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    heart = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[heart] = replace(state.cards[heart], suit=Suit.HEART)
    session.engine.start_action(GongxinAction('gongxin', 'p1'))
    for choice in ('p2', heart, 'top'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0] == heart
    assert state.play_usage.count('skill.gongxin') == 1


def test_qinyin_uses_recover_actions_for_all_living_players():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'fire_god_zhouyu'
    state.players['p2'].hp -= 1
    session.engine.start_action(QinyinAction('qinyin', 'p1'))
    for choice in (True, 'recover'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert state.players['p2'].hp == state.players['p2'].max_hp


def test_yeyan_small_deals_three_fire_damage_through_shared_pipeline():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'fire_god_zhouyu'
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    before = {pid: state.players[pid].hp for pid in ('p2', 'p3', 'p4')}
    session.engine.start_action(YeyanAction('yeyan-small', 'p1'))
    for choice in ('small', ('p2', 'p3', 'p4')):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert all(state.players[pid].hp == before[pid] - 1 for pid in before)
    assert state.players['p1'].marks['yeyan_used'] == 1


def test_yeyan_great_pays_four_distinct_suits_and_hp():
    session = GameSession.new_game(military=True, five_generals=True)
    state = session.state
    player = state.players['p1']
    player.character_id = 'fire_god_zhouyu'
    player.max_hp = 6
    player.hp = 6
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    cards = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[:4]
    suits = (Suit.HEART, Suit.DIAMOND, Suit.CLUB, Suit.SPADE)
    for cid, suit in zip(cards, suits):
        state.cards[cid] = replace(state.cards[cid], suit=suit)
    session.engine.start_action(YeyanAction('yeyan-great', 'p1'))
    for choice in ('great', 'p2', 'p2', *cards):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert player.hp == 3
    assert state.players['p2'].hp == state.players['p2'].max_hp - 3
    assert set(cards) <= set(state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))

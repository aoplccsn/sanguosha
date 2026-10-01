from sanguosha.engine.god_lvbu import WuqianAction, ShenfenAction
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import Phase
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.session import GameSession


def prepared_lvbu():
    session = GameSession.new_game(seed=13, military=True, five_generals=True)
    state = session.state
    state.players['p1'].character_id = 'forest_god_lvbu'
    state.players['p1'].hp = state.players['p1'].max_hp = 5
    state.players['p1'].marks['rage'] = 8
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    return session


def test_wuqian_and_shenfen_are_engine_events_with_authoritative_multi_target_damage():
    session = prepared_lvbu()
    state = session.state
    hp_before = {pid: state.players[pid].hp for pid in state.seat_order if pid != 'p1'}
    session.engine.start_action(WuqianAction('review:wuwei', 'p1'))
    request = session.engine.pending_request
    assert request.allowed_player_ids == ('p2', 'p3', 'p4', 'p5')
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'p2'))
    assert state.players['p1'].marks['rage'] == 6
    assert state.players['p1'].marks['wuwei'] == 1
    assert state.players['p2'].marks['wuwei_target_p1'] == 1
    assert session.skills.has(state, 'p1', 'wushuang')

    session.engine.start_action(ShenfenAction('review:shenfen', 'p1'))
    while session.engine.pending_request:
        request = session.engine.pending_request
        session.engine.submit_decision(session.ai.decide(state, request))
    assert {pid: state.players[pid].hp for pid in hp_before} == {
        pid: hp - 1 for pid, hp in hp_before.items()
    }
    assert all(not state.cards_in(ZoneRef(ZoneType.HAND, pid)) for pid in hp_before)
    assert state.players['p1'].face_up is False
    assert state.play_usage.count('skill.shenfen') == 1
    room = MultiplayerRoom()
    cues = [room._public_event(event) for event in session.events.events]
    cues = [cue for cue in cues if cue and cue['kind'] == 'GodSkillEvent']
    assert [(cue['skill_id'], cue['level']) for cue in cues] == [('wuwei', 2), ('shenfen', 3)]
    assert cues[1]['target_ids'] == ['p2', 'p3', 'p4', 'p5']
    state.__post_init__()


def test_shenfen_requires_six_rage_and_one_use_per_play_phase():
    session = prepared_lvbu()
    state = session.state
    state.players['p1'].marks['rage'] = 5
    from sanguosha.engine.card_rules import InvalidCardUse
    import pytest
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(ShenfenAction('blocked:shenfen', 'p1'))

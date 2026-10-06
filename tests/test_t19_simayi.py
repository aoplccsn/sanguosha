"""Current mobile Simayi core paths and serial pending learning."""
from test_t17b_tier1 import game, answer
from sanguosha.engine.gods import BaiyinAction
from sanguosha.engine.mobile_gods import MobileGodAction, start_normal_round
from sanguosha.engine.skill_grants import add_grant, remove_grant, grant_sources
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.snapshot import snapshot_session, restore_session


def setup():
    s = game()
    s.state.players['p1'].character_id = 'mountain_god_simayi'
    return s


def test_awaken_permanent_faction_skills():
    s = setup(); p = s.state.players['p1']; p.marks['ren'] = 4; before = p.max_hp
    s.engine.start_action(BaiyinAction('awaken', 'p1'))
    assert p.max_hp == before - 1
    assert s.skills.has(s.state, 'p1', 'guicai')
    assert s.skills.has(s.state, 'p1', 'wansha')
    remove_grant(s.state, 'p1', 'jilue', 'baoyin')
    assert s.skills.has(s.state, 'p1', 'guicai')


def test_learning_costs_restore_and_sources():
    s = setup(); p = s.state.players['p1']; p.marks['ren'] = 12
    add_grant(s.state, 'p1', 'jilue', 'test')
    for index, skill in enumerate(('fangzhu', 'jizhi', 'zhiheng')):
        before = s.state.players['p1'].marks['ren']
        s.engine.start_action(MobileGodAction('learn:' + str(index), 'p1', 'jilue'))
        request = s.engine.pending_request
        s = restore_session(snapshot_session(s))
        assert s.engine.pending_request == request
        answer(s, 'learn:' + skill)
        assert s.state.players['p1'].marks['ren'] == before - (2, 2, 3)[index]
        assert grant_sources(s.state, 'p1', skill) == ('jilue.permanent',)
    add_grant(s.state, 'p1', 'fangzhu', 'other')
    remove_grant(s.state, 'p1', 'fangzhu', 'other')
    assert s.skills.has(s.state, 'p1', 'fangzhu')


def test_nonresponse_round_cap_own_card_and_extra_turn():
    s = setup(); p = s.state.players['p1']
    for i in range(6):
        s.engine.start_action(RespondWithCardAction('reply:' + str(i), 'p1', 'basic.slash',
            'card:' + str(i), card_source_id='p2'))
        answer(s, PASS_RESPONSE)
    assert p.marks['ren'] == 4
    s.state.extra_turn_anchor = 'p2'
    start_normal_round(s.state, 'p1')
    assert p.marks['renjie_round_count'] == 4
    s.state.extra_turn_anchor = None
    start_normal_round(s.state, 'p1'); start_normal_round(s.state, 'p1')
    assert 'renjie_round_count' not in p.marks
    s.engine.start_action(RespondWithCardAction('own', 'p1', 'basic.slash', 'own-card',card_source_id='p1'))
    answer(s, PASS_RESPONSE)
    assert p.marks['ren'] == 4
    s.engine.start_action(RespondWithCardAction('delayed', 'p1', 'trick.nullification', 'delayed-card',delayed_card=True))
    answer(s, PASS_RESPONSE)
    assert p.marks['ren'] == 5



def test_lianpo_immediate_choice_once_extra_or_free_learning():
    s = setup(); p = s.state.players['p1']; s.state.turn_number = 3
    add_grant(s.state, 'p1', 'jilue', 'test')
    s.engine.start_action(MobileGodAction('kill1', 'p1', 'lianpo'))
    assert 'extra_turn' in s.engine.pending_request.choices
    answer(s, 'extra_turn')
    assert p.marks['lianpo_pending'] == 1
    s.engine.start_action(MobileGodAction('kill2', 'p1', 'lianpo'))
    assert 'extra_turn' not in s.engine.pending_request.choices
    answer(s, 'learn:jizhi')
    assert s.skills.has(s.state, 'p1', 'jizhi')
    assert p.marks.get('ren', 0) == 0

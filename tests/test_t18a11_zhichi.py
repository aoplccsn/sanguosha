"""Zhichi uses classic Damaged timing and the active turn lifetime."""
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.death import DeathAction
from sanguosha.engine.yj2011_tier3 import protected
from sanguosha.engine.requests import PASS_RESPONSE


def game():
    s=setup('xun_you');s.state.players['p1'].character_id='yj2011_chen_gong'
    s.state.current_player_id='p2'
    return s


def test_zhichi_fatal_damage_does_not_activate_until_rescued():
    s=game();s.state.players['p1'].hp=1
    peach=put(s,'basic.peach','p2')
    s.engine.start_action(MilitaryDamageAction('audit-zhichi-fatal','p3','p1',1))
    assert s.engine.pending_request is not None
    assert not protected(s.state,'p1')
    s=restore(s);answer(s,PASS_RESPONSE);s=restore(s);answer(s,peach)
    finish(s)
    assert s.state.players['p1'].hp==1 and protected(s.state,'p1')

@pytest.mark.parametrize('inactive',['no-phase','no-current','dead-current'])
def test_zhichi_requires_a_living_active_current_turn(inactive):
    from sanguosha.model.enums import PlayerStatus
    s=game()
    if inactive=='no-phase':s.state.current_phase=None
    if inactive=='no-current':s.state.current_player_id=None
    if inactive=='dead-current':s.state.players['p2'].status=PlayerStatus.DEAD
    s.engine.start_action(MilitaryDamageAction('audit-zhichi-inactive',None,'p1',1))
    finish(s)
    assert not protected(s.state,'p1')


def test_zhichi_all_marks_clear_immediately_when_current_player_dies():
    s=game()
    for pid in ('p1','p3'):s.state.players[pid].marks['yj_zhichi']=s.state.turn_number
    s.engine.start_action(DeathAction('audit-zhichi-current-death','p2',None));finish(s)
    assert all(not protected(s.state,pid) for pid in ('p1','p3'))

@pytest.mark.parametrize('kind',['suppressed','hp-loss','own-turn','prevented'])
def test_zhichi_does_not_grant_without_qualifying_damage(kind):
    from sanguosha.engine.hp import LoseHpAction
    from sanguosha.model.enums import DamageNature
    s=game()
    if kind=='suppressed':s.state.players['p1'].disabled_skills.add('zhichi')
    if kind=='own-turn':s.state.current_player_id='p1'
    if kind=='prevented':s.state.players['p1'].marks['fog:p3']=1
    action=(LoseHpAction('audit-zhichi-hp','p1',1) if kind=='hp-loss' else
            MilitaryDamageAction('audit-zhichi-negative',None,'p1',1,DamageNature.NORMAL))
    s.engine.start_action(action);finish(s)
    assert not protected(s.state,'p1')


def test_zhichi_already_granted_protection_survives_skill_suppression():
    from sanguosha.engine.military_tricks import TargetTrick
    from sanguosha.engine.military_basics import MilitaryStrike
    s=game();s.engine.start_action(MilitaryDamageAction('audit-zhichi-grant','p2','p1',1));finish(s)
    s.state.players['p1'].disabled_skills.add('zhichi');s=restore(s)
    cid=put(s,'basic.slash','p2');hp=s.state.players['p1'].hp
    s.engine.start_action(MilitaryStrike('audit-zhichi-slash','p2','p1',cid,'basic.dodge'));finish(s)
    s.engine.start_action(TargetTrick('audit-zhichi-chain','p2','p1',cid,'trick.iron_chain'));finish(s)
    assert s.state.players['p1'].hp==hp and not s.state.players['p1'].chained


def test_zhichi_protection_does_not_prevent_delayed_trick_damage():
    from sanguosha.model.enums import DamageNature
    s=game();s.engine.start_action(MilitaryDamageAction('audit-zhichi-grant','p2','p1',1));finish(s)
    s.state.players['p1'].hp=4
    cid=put(s,'delayed.lightning')
    s.engine.start_action(MilitaryDamageAction('audit-zhichi-lightning',None,'p1',3,DamageNature.THUNDER,cid,card_kind='trick'))
    finish(s)
    assert s.state.players['p1'].hp==1


def test_zhichi_death_of_non_current_player_keeps_other_protection():
    s=game();s.state.players['p1'].marks['yj_zhichi']=s.state.turn_number
    s.engine.start_action(DeathAction('audit-zhichi-other-death','p3',None));finish(s)
    assert protected(s.state,'p1')

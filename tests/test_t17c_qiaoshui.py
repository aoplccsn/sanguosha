from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.engine.yj2011_tier3 import AuthorizedVirtualUse
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.model.zones import ZoneRef,ZoneType

def game():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_jian_yong'
    for q in s.state.seat_order:empty(s,q)
    return s

def won(s):s.state.players['p1'].marks['qiaoshui_success']=s.state.turn_number

@pytest.mark.parametrize('virtual',[False,True])
def test_qiaoshui_add_slash_without_distance_reconnect_and_quota(virtual):
    s=game();won(s);c=put(s,'basic.slash')
    a=AuthorizedVirtualUse('extra','p1',('p2',),VirtualCard('basic.slash',(),None,None,'test')) if virtual else UseCardAction('extra','p1',c,('p2',))
    s.engine.start_action(a);s=restore(s)
    assert s.engine.pending_request.choices==('cancel','add')
    answer(s,'add');s=restore(s);assert 'p3' in s.engine.pending_request.allowed_player_ids
    answer(s,'p3');s=restore(s);finish(s)
    assert s.state.players['p2'].hp==3 and s.state.players['p3'].hp==3
    assert s.state.play_usage.count('basic.slash')==int(not virtual)
    assert not s.state.metadata.get('qiaoshui_targets')
    assert 'qiaoshui_success' not in s.state.players['p1'].marks

@pytest.mark.parametrize('definition',['basic.peach','basic.wine','trick.ex_nihilo'])
def test_qiaoshui_fixed_self_cards_extra_target(definition):
    s=game();won(s);s.state.players['p1'].hp=2;s.state.players['p3'].hp=2;c=put(s,definition)
    s.engine.start_action(UseCardAction('fixed','p1',c));answer(s,'add');s=restore(s);answer(s,'p3');finish(s)
    if definition=='basic.peach':assert s.state.players['p1'].hp==3 and s.state.players['p3'].hp==3
    elif definition=='basic.wine':assert s.state.players['p1'].marks['wine']==s.state.players['p3'].marks['wine']==1
    else:assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))==2
    assert not s.state.metadata.get('qiaoshui_targets')

def test_qiaoshui_remove_aoe_target():
    s=game();won(s);c=put(s,'trick.savage_assault')
    s.engine.start_action(UseCardAction('aoe','p1',c));assert s.engine.pending_request.choices==('cancel','remove')
    answer(s,'remove');s=restore(s);answer(s,'p2');finish(s)
    assert s.state.players['p2'].hp==4 and s.state.players['p3'].hp==3

def test_qiaoshui_cancel_consumes_next_card_and_equipment_does_not():
    s=game();won(s);c=put(s,'equipment.armor.vine');s.engine.start_action(UseCardAction('equip','p1',c))
    assert s.state.players['p1'].marks['qiaoshui_success']==s.state.turn_number
    c=put(s,'basic.slash');s.engine.start_action(UseCardAction('cancel','p1',c,('p2',)));answer(s,'cancel');finish(s)
    assert s.state.players['p2'].hp==3 and s.state.players['p3'].hp==4
    assert 'qiaoshui_success' not in s.state.players['p1'].marks

@pytest.mark.parametrize('rank,success',[(12,True),(3,False),(7,False)])
def test_qiaoshui_pindian_success_or_turn_trick_lock(rank,success):
    s=game();a=put(s,'basic.slash');b=put(s,'basic.dodge','p2')
    s.state.cards[a]=replace(s.state.cards[a],rank=rank);s.state.cards[b]=replace(s.state.cards[b],rank=7)
    s.state.players['p1'].disabled_skills.add('zongshi_jianyong')
    s.engine.start_action(YJ2013Action('talk','p1','qiaoshui'));answer(s,True);answer(s,'p2');s=restore(s)
    answer(s,a);s=restore(s);answer(s,b)
    assert s.state.players['p1'].marks['qiaoshui_success' if success else 'qiaoshui_trick_lock']==s.state.turn_number
    if not success:
        for definition in ('trick.duel','trick.ex_nihilo','delayed.lightning'):
            c=put(s,definition)
            with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('blocked:'+c,'p1',c,('p2',) if definition=='trick.duel' else ()))
        c=put(s,'trick.nullification');s.engine.start_action(RespondWithCardAction('counter','p1','trick.nullification','other'))
        assert s.engine.pending_request is None and c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))

def test_qiaoshui_decline_no_hand_and_prohibited_extra_targets():
    s=game();s.engine.start_action(YJ2013Action('empty','p1','qiaoshui'));assert s.engine.pending_request is None
    put(s,'basic.slash');put(s,'basic.slash','p2');s.engine.start_action(YJ2013Action('decline','p1','qiaoshui'));answer(s,False)
    assert not s.state.players['p1'].marks.get('qiaoshui_success')
    s=game();won(s);s.state.players['p3'].character_id='zhugeliang';c=put(s,'basic.slash')
    s.engine.start_action(UseCardAction('legal','p1',c,('p2',)));answer(s,'add')
    assert 'p3' not in s.engine.pending_request.allowed_player_ids
    answer(s,'p4');finish(s)


def test_qiaoshui_phase_hook_and_turn_scoped_cleanup():
    from sanguosha.engine.turns import TurnAction
    from sanguosha.engine.phases import END_PLAY_PHASE
    from sanguosha.model.enums import Phase
    s=game();put(s,'basic.slash');put(s,'basic.dodge','p2')
    s.engine.start_action(TurnAction('turn-talk','p1',(Phase.PLAY,)))
    assert '巧说' in s.engine.pending_request.prompt
    s=restore(s);answer(s,False);answer(s,END_PLAY_PHASE)
    assert not s.state.players['p1'].marks.get('qiaoshui_success')

def test_qiaoshui_jizhi_uses_adjusted_targets_and_preserves_draw_child():
    s=game();won(s);s.state.players['p1'].granted_skills['jizhi']='test';c=put(s,'trick.ex_nihilo')
    s.engine.start_action(UseCardAction('jizhi','p1',c));answer(s,'add');answer(s,'p3')
    assert '集智' in s.engine.pending_request.prompt
    answer(s,True);finish(s)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==3
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))==2


def test_black_self_lightning_weimu_is_rejected_before_cost_or_resolution():
    from sanguosha.model.enums import Suit
    s=game();s.state.players['p1'].character_id='forest_jia_xu';c=put(s,'delayed.lightning')
    s.state.cards[c]=replace(s.state.cards[c],suit=Suit.SPADE)
    handler=s.engine.registry.handler_for(UseCardAction('lightning','p1',c))
    assert not handler.validator.can_offer(s.state,'p1',c)
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('lightning','p1',c))
    assert c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')) and s.engine.stack.is_empty()


def test_qiaoshui_extra_wine_expires_at_current_turn_end():
    from sanguosha.engine.turns import TurnAction
    from sanguosha.engine.phases import END_PLAY_PHASE
    from sanguosha.model.enums import Phase
    s=game();won(s);c=put(s,'basic.wine')
    s.engine.start_action(UseCardAction('wine-extra','p1',c));answer(s,'add');answer(s,'p3')
    assert s.state.players['p3'].marks['wine']==1
    s.state.players['p1'].disabled_skills.add('qiaoshui')
    s.engine.start_action(TurnAction('wine-end','p1',(Phase.PLAY,)));answer(s,END_PLAY_PHASE)
    assert 'wine' not in s.state.players['p3'].marks and not s.state.metadata['qiaoshui_wine_targets']


@pytest.mark.parametrize('definition,consumed',[('trick.nullification',True),('basic.peach',True),('basic.wine',True),('basic.dodge',False),('basic.slash',False)])
def test_qiaoshui_response_uses_consume_success_but_regular_responses_do_not(definition,consumed):
    from sanguosha.engine.events import CardRespondedEvent
    from sanguosha.engine.qiaoshui import before_reactions
    s=game();won(s);c=put(s,definition)
    event=CardRespondedEvent('response','p1',c,'other',definition)
    assert before_reactions(s.state,[event],s.skills,s.definitions)==(None,False)
    assert ('qiaoshui_success' not in s.state.players['p1'].marks)==consumed

@pytest.mark.parametrize('definition,mode,expected',[('trick.ex_nihilo','add','p3'),('trick.god_salvation','remove','p2'),('trick.amazing_grace','remove','p2')])
def test_qiaoshui_beneficial_extra_target_ai_uses_public_friend_attitude(definition,mode,expected):
    from sanguosha.decisions.yj2013 import decide
    class PublicAttitude:
        def _priority(self,state,pid,target):return {'p2':2,'p3':-2}[target]
    s=game();won(s);c=put(s,definition)
    s.engine.start_action(UseCardAction('friendly','p1',c));answer(s,mode)
    request=replace(s.engine.pending_request,allowed_player_ids=('p2','p3'))
    assert decide(PublicAttitude(),s.state,request).value==expected

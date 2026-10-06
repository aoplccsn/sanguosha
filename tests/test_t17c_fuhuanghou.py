from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.military_basics import MilitaryStrike
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.engine.events import AfterDamageEvent,CardUsedEvent,CardRespondedEvent
from sanguosha.model.zones import ZoneRef,ZoneType

def game():
    s=setup('cao_zhang')
    for q in s.state.seat_order:empty(s,q)
    s.state.players['p2'].character_id='yj2013_fu_huanghou'
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return s

def ask(s,target='p3'):
    assert '求援' in s.engine.pending_request.prompt
    s=restore(s);answer(s,True);s=restore(s);answer(s,target)
    return restore(s)

def test_qiuyuan_gift_is_not_response_and_can_be_used_by_owner():
    s=game();slash=put(s,'basic.slash');dodge=put(s,'basic.dodge','p3')
    s.engine.start_action(UseCardAction('gift','p1',slash,('p2',)));s=ask(s)
    assert s.engine.pending_request.player_id=='p3'
    answer(s,(dodge,));s=restore(s)
    assert dodge in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
    assert not any(isinstance(e,CardRespondedEvent) for e in s.events.events)
    answer(s,dodge)
    assert s.state.players['p2'].hp==4 and s.state.players['p3'].hp==4
    assert s.state.play_usage.count('basic.slash')==1
    assert not s.state.metadata['slash_target_windows']

@pytest.mark.parametrize('standalone',[False,True])
def test_qiuyuan_empty_hand_extra_target_ignores_distance_and_restores(standalone):
    s=game();slash=put(s,'basic.fire_slash');s.state.players['p1'].marks['wine']=1
    action=MilitaryStrike('extra','p1','p2',slash,'basic.dodge',1) if standalone else UseCardAction('extra','p1',slash,('p2',))
    s.engine.start_action(action);s=ask(s)
    assert s.engine.pending_request.player_id=='p2'
    answer(s,PASS_RESPONSE);s=restore(s)
    assert s.engine.pending_request.player_id=='p3'
    answer(s,PASS_RESPONSE)
    assert s.state.players['p2'].hp==2 and s.state.players['p3'].hp==2
    assert not s.state.metadata['slash_target_windows']

def test_qiuyuan_declined_gift_and_repeat_target_does_not_loop():
    s=game();s.state.players['p3'].character_id='yj2013_fu_huanghou'
    slash=put(s,'basic.slash');dodge=put(s,'basic.dodge','p3')
    s.engine.start_action(UseCardAction('repeat','p1',slash,('p2',)));s=ask(s)
    answer(s,());answer(s,PASS_RESPONSE);s=ask(s,'p2');answer(s,PASS_RESPONSE)
    assert s.state.players['p2'].hp==3 and s.state.players['p3'].hp==3
    assert dodge in s.state.cards_in(ZoneRef(ZoneType.HAND,'p3'))
    assert len([e for e in s.events.events if isinstance(e,AfterDamageEvent)])==2
    assert not s.state.metadata['slash_target_windows']

def test_qiuyuan_kongcheng_prohibition_and_decline():
    s=game();s.state.players['p3'].character_id='zhugeliang';slash=put(s,'basic.slash')
    s.engine.start_action(UseCardAction('kong','p1',slash,('p2',)));s=ask(s);answer(s,PASS_RESPONSE)
    assert s.state.players['p2'].hp==3 and s.state.players['p3'].hp==4
    s=game();slash=put(s,'basic.slash');s.engine.start_action(UseCardAction('no','p1',slash,('p2',)))
    answer(s,False);answer(s,PASS_RESPONSE)
    assert s.state.players['p3'].hp==4

@pytest.mark.parametrize('ranks,won',[((12,3),True),((3,12),False),((7,7),False)])
def test_zhuikong_win_self_only_or_loss_directional_distance_restore(ranks,won):
    from sanguosha.engine.fuhuanghou import target_allowed,clear_turn
    s=game();s.state.players['p1'].character_id='yj2013_fu_huanghou';s.state.players['p1'].hp=2
    s.state.current_player_id='p3'
    cards=[put(s,'basic.slash',q) for q in ('p1','p3')]
    for c,n in zip(cards,ranks):s.state.cards[c]=replace(s.state.cards[c],rank=n)
    s.engine.start_action(YJ2013Action('fear','p1','zhuikong','p3'))
    s=restore(s);answer(s,True);s=restore(s);answer(s,cards[0]);s=restore(s);answer(s,cards[1]);s=restore(s)
    assert target_allowed(s.state,'p3','p3')
    assert target_allowed(s.state,'p3','p2') is (not won)
    distance=DistanceSystem(s.definitions)
    assert distance.distance_between(s.state,'p3','p1')==(2 if won else 1)
    assert distance.distance_between(s.state,'p1','p3')==2
    clear_turn(s.state,'p3')
    assert target_allowed(s.state,'p3','p2') and distance.distance_between(s.state,'p3','p1')==2

@pytest.mark.parametrize('condition',['full','empty','decline'])
def test_zhuikong_optional_conditions(condition):
    s=game();s.state.players['p2'].hp=4 if condition=='full' else 2
    if condition!='empty':put(s,'basic.slash','p2')
    put(s,'basic.slash','p1')
    s.engine.start_action(YJ2013Action('optional','p2','zhuikong','p1'))
    if condition=='decline':answer(s,False)
    assert s.engine.pending_request is None and not s.state.metadata.get('zhuikong_distance')


@pytest.mark.parametrize('character,definition,token',[('zhaoyun','basic.thunder_slash','longdan'),('zhenji','basic.slash','qingguo'),('mountain_god_zhaoyun','basic.slash','longhun')])
def test_qiuyuan_virtual_dodge_transfers_subcards_without_response(character,definition,token):
    from sanguosha.model.enums import Suit
    s=game();s.state.players['p3'].character_id=character;s.state.players['p3'].hp=1
    c=put(s,definition,'p3');s.state.cards[c]=replace(s.state.cards[c],suit=Suit.CLUB if token=='qingguo' else Suit.HEART if token=='longdan' else Suit.CLUB)
    slash=put(s,'basic.slash');s.engine.start_action(UseCardAction('viewas','p1',slash,('p2',)));s=ask(s)
    option=next(o for o in s.engine.pending_request.eligible_card_ids if o.startswith('virtual:'+token+':'))
    answer(s,(option,));s=restore(s)
    assert c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
    assert not any(isinstance(e,CardRespondedEvent) for e in s.events.events)
    finish(s)
    assert s.state.players['p3'].hp==1

def test_zhuikong_turn_hook_restriction_and_turn_end_cleanup():
    from sanguosha.engine.turns import TurnAction
    from sanguosha.engine.phases import END_PLAY_PHASE
    from sanguosha.engine.card_rules import InvalidCardUse
    from sanguosha.model.enums import Phase
    s=game();s.state.players['p2'].hp=2
    a=put(s,'basic.slash','p2');b=put(s,'basic.dodge','p3');c=put(s,'trick.duel','p3')
    s.state.cards[a]=replace(s.state.cards[a],rank=13);s.state.cards[b]=replace(s.state.cards[b],rank=1)
    s.engine.start_action(TurnAction('turn-fear','p3',(Phase.PLAY,)))
    assert s.engine.pending_request.player_id=='p2'
    answer(s,True);s=restore(s);answer(s,a);s=restore(s);answer(s,b);s=restore(s)
    assert 'use:'+c not in s.engine.pending_request.choices
    assert s.state.players['p3'].marks['zhuikong_self_only']==s.state.turn_number
    answer(s,END_PLAY_PHASE)
    assert 'zhuikong_self_only' not in s.state.players['p3'].marks

def test_qiuyuan_virtual_use_room_combat_dynamic_target_projection():
    from sanguosha.multiplayer.room import MultiplayerRoom
    from sanguosha.engine.yj2011_tier3 import AuthorizedVirtualUse
    from sanguosha.model.virtual_card import VirtualCard
    s=game();s.engine.start_action(AuthorizedVirtualUse('virtual-root','p1',('p2',),VirtualCard('basic.slash',(),None,None,'test')));s=ask(s)
    room=MultiplayerRoom();room.session=s
    context=room._combat_context()
    assert context['target_ids']==['p2','p3'] and context['current_target_id']=='p2'
    s=restore(s);room.session=s
    assert room._combat_context()==context
    finish(s)

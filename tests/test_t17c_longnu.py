from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put,resolve
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.engine.events import CardUsedEvent
from sanguosha.engine.yj2011_tier3 import canonical_definition
from sanguosha.model.enums import Phase,Suit
from sanguosha.projection import project_for_human


def game(form=0):
    s=setup('cao_zhang');s.state.players['p1'].character_id='shadow_god_liubei'
    for q in s.state.seat_order:empty(s,q)
    if form:s.state.players['p1'].marks['longnu_form']=form
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return s


def card(s,definition,suit=Suit.HEART):
    c=put(s,definition);s.state.cards[c]=replace(s.state.cards[c],suit=suit)
    return c


def test_longnu_alternates_actual_hp_and_maxhp_cost_and_clears_each_play_restore():
    s=game();p=s.state.players['p1'];hp=p.hp;maxhp=p.max_hp
    s.engine.start_action(PhaseAction('first','p1',Phase.PLAY));s=restore(s)
    assert s.state.players['p1'].hp==hp-1 and s.state.players['p1'].max_hp==maxhp
    assert s.state.players['p1'].marks['longnu_form']==1
    answer(s,'end_play_phase');assert 'longnu_form' not in s.state.players['p1'].marks
    s.engine.start_action(PhaseAction('second','p1',Phase.PLAY));s=restore(s)
    assert s.state.players['p1'].max_hp==maxhp-1 and s.state.players['p1'].marks['longnu_form']==2
    answer(s,'end_play_phase');assert 'longnu_form' not in s.state.players['p1'].marks


@pytest.mark.parametrize('physical',['basic.dodge','basic.peach','equipment.armor.vine','trick.duel','delayed.indulgence'])
def test_longnu_red_hand_forced_fire_slash_distant_target_and_projection(physical):
    s=game(1);c=card(s,physical)
    assert canonical_definition(s.state,s.skills,'p1',physical,c)=='basic.fire_slash'
    view=project_for_human(s.state,s.definitions,'p1',{})
    assert next(x for x in view.hand if x.card_id==c).definition_id=='basic.fire_slash'
    before=s.state.players['p3'].hp
    s.engine.start_action(UseCardAction('converted','p1',c,('p3',)));s=restore(s);resolve(s)
    assert s.state.players['p3'].hp==before-1
    e=next(e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='converted:used')
    assert e.virtual_card.definition_id=='basic.fire_slash' and e.virtual_card.skill_id=='longnu'
    assert s.state.cards[c].definition_id==physical and s.state.play_usage.count('basic.slash')==1


def test_longnu_black_slash_keeps_distance_and_red_fire_keeps_quota():
    s=game(1);black=card(s,'basic.slash',Suit.SPADE)
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('distant','p1',black,('p3',)))
    red=card(s,'basic.peach');s.engine.start_action(UseCardAction('fire','p1',red,('p2',)));resolve(s)
    second=card(s,'basic.dodge')
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('twice','p1',second,('p2',)))


def test_longnu_tricks_and_printed_thunder_unlimited_but_keep_distance_and_normal_quota():
    s=game(2)
    for i,physical in enumerate(('trick.duel','delayed.indulgence','basic.thunder_slash')):
        c=card(s,physical,Suit.SPADE);s.engine.start_action(UseCardAction('thunder'+str(i),'p1',c,('p2',)));resolve(s)
    assert s.state.play_usage.count('basic.slash')==3
    normal=card(s,'basic.slash',Suit.CLUB)
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('normal','p1',normal,('p5',)))
    distant=card(s,'trick.duel',Suit.CLUB)
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('distant','p1',distant,('p3',)))


@pytest.mark.parametrize('active,physical,suit,required,eligible',[
(1,'basic.dodge',Suit.HEART,'basic.dodge',False),
(1,'basic.peach',Suit.HEART,'basic.peach',False),
(1,'basic.dodge',Suit.HEART,'basic.slash',True),
(2,'trick.nullification',Suit.CLUB,'trick.nullification',False),
(2,'delayed.indulgence',Suit.CLUB,'basic.slash',True),
])
def test_longnu_physical_response_identity_uses_same_conversion_restore(active,physical,suit,required,eligible):
    s=game(active);c=card(s,physical,suit)
    s.engine.start_action(RespondWithCardAction('response','p1',required,'source'))
    s=restore(s);assert (c in s.engine.pending_request.eligible_card_ids)==eligible
    answer(s,c if eligible else PASS_RESPONSE)
    assert s.engine.pending_request is None


def test_longnu_converted_trick_does_not_trigger_jizhi_or_wumou():
    s=game(2);s.state.players['p1'].granted_skills.update({'jizhi':'test','wumou':'test'})
    c=card(s,'trick.duel',Suit.CLUB);hp=s.state.players['p1'].hp
    s.engine.start_action(UseCardAction('thunder','p1',c,('p2',)))
    assert s.engine.pending_request.player_id=='p2'
    resolve(s);assert s.state.players['p1'].hp==hp


def test_longnu_converted_slash_respects_qianxi_and_skill_suppression():
    s=game(1);c=card(s,'basic.dodge');s.state.metadata['qianxi_limits']={'p2':{'target':'p1','color':'red','turn':4}}
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('prohibited','p1',c,('p3',)))
    s.state.metadata.pop('qianxi_limits');s.state.players['p1'].disabled_skills.add('longnu')
    assert canonical_definition(s.state,s.skills,'p1','basic.dodge',c)=='basic.dodge'
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('disabled','p1',c,('p3',)))


def test_longnu_converted_savage_assault_is_not_acquired_by_juxiang():
    from sanguosha.model.zones import ZoneRef,ZoneType
    s=game(2);s.state.players['p3'].granted_skills['juxiang']='test'
    c=card(s,'trick.savage_assault',Suit.CLUB)
    s.engine.start_action(UseCardAction('thunder','p1',c,('p2',)));resolve(s)
    assert c in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_longnu_converted_slash_receives_luoyi_damage_bonus():
    s=game(1);s.state.players['p1'].marks['luoyi']=1;c=card(s,'basic.dodge')
    before=s.state.players['p2'].hp;s.engine.start_action(UseCardAction('fire','p1',c,('p2',)));resolve(s)
    assert s.state.players['p2'].hp==before-2

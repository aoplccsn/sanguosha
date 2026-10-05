from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t17c_juece import empty
from test_t6_military_basics import put
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.view_as import UseSpear
from sanguosha.engine.skills import WushengUse
from sanguosha.engine.events import CardUsedEvent
from sanguosha.model.enums import Suit,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType

def guan():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_guan_ping';return s

@pytest.mark.parametrize('suit,wanted',[(Suit.SPADE,True),(Suit.HEART,True),(Suit.HEART,False)])
def test_longyin_real_slash_quota_cost_color_and_restore(suit,wanted):
    s=guan();card=put(s,'basic.slash');s.state.cards[card]=replace(s.state.cards[card],suit=suit)
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    assert s.state.play_usage.count('basic.slash')==1
    s=restore(s);answer(s,wanted)
    if wanted:
        assert card not in s.engine.pending_request.eligible_card_ids
        s=restore(s);answer(s,s.engine.pending_request.eligible_card_ids[0])
    finish(s)
    assert s.state.play_usage.count('basic.slash')==int(not wanted)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before-1-int(wanted)+int(wanted and suit is Suit.HEART)

def test_two_longyin_owners_remove_only_this_slash_not_previous_count():
    s=guan();s.state.players['p3'].granted_skills['longyin']='test'
    s.state.play_usage.record('basic.slash');s.state.players['p1'].marks['slash_quota_bonus']=2
    c=put(s,'basic.slash');s.engine.start_action(UseCardAction('slash','p1',c,('p2',)))
    for pid in ('p1','p3'):
        assert s.engine.pending_request.player_id==pid
        s=restore(s);answer(s,True);s=restore(s);answer(s,s.engine.pending_request.eligible_card_ids[0])
        assert s.state.play_usage.count('basic.slash')==1
    finish(s)

@pytest.mark.parametrize('forced',[True,False])
def test_forced_and_xianzhen_uncounted_slash_do_not_erase_prior_quota(forced):
    s=guan();s.state.play_usage.record('basic.slash')
    if not forced:s.state.players['p1'].marks['yj_xianzhen:p2']=s.state.turn_number
    else:s.state.players['p1'].marks['slash_quota_bonus']=2
    c=put(s,'basic.slash');s.engine.start_action(UseCardAction('slash','p1',c,('p2',),forced=forced))
    answer(s,True);answer(s,s.engine.pending_request.eligible_card_ids[0]);finish(s)
    assert s.state.play_usage.count('basic.slash')==1

@pytest.mark.parametrize('mixed',[False,True])
def test_spear_virtual_color_and_longyin_event(mixed):
    s=guan();empty(s,'p1');put(s,'equipment.weapon.serpent_spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    materials=(put(s,'basic.dodge'),put(s,'basic.dodge'))
    for i,c in enumerate(materials):s.state.cards[c]=replace(s.state.cards[c],suit=Suit.SPADE if mixed and i else Suit.HEART)
    cost=put(s,'basic.slash');before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(UseSpear('spear','p1'));answer(s,materials);answer(s,'p2')
    s=restore(s);answer(s,True);answer(s,cost);finish(s)
    assert s.state.play_usage.count('basic.slash')==0
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before-3+int(not mixed)
    uses=[e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='spear:used']
    assert len(uses)==1 and uses[0].slash_counted

def test_wusheng_is_a_real_use_event_not_only_damage():
    s=guan();s.state.players['p1'].granted_skills['wusheng']='test'
    card=put(s,'basic.dodge');s.state.cards[card]=replace(s.state.cards[card],suit=Suit.HEART)
    s.engine.start_action(WushengUse('wusheng','p1',card));answer(s,'p2')
    assert s.engine.pending_request.player_id=='p1';answer(s,False);finish(s)
    uses=[e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='wusheng:used']
    assert len(uses)==1 and uses[0].slash_counted

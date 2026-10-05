from dataclasses import replace
import pytest
from test_t17c_first_batch import setup, restore
from test_t17b_tier1 import answer, finish
from test_t6_military_basics import put
from sanguosha.engine.yj2012 import YJ2012Action, YJ2012Handler
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.events import CardUsedEvent
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.model.enums import Suit, Color
from sanguosha.model.zones import ZoneRef, ZoneType

def clear_hand(s):
    zone=s.state.zones[ZoneRef(ZoneType.HAND,'p1')]
    cards=tuple(zone.card_ids)
    if cards: s.engine.reaction_provider.__self__.move(s.state,CardMove('clear',cards,ZoneRef(ZoneType.HAND,'p1'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM,'p1'))

def test_all_hand_ex_nihilo_one_event_once_restore_every_counter():
    s=setup('xun_you'); clear_hand(s)
    materials=tuple(put(s,'basic.slash') for _ in range(3))
    s.engine.start_action(YJ2012Action('qice','p1','qice')); s=restore(s)
    assert 'trick.nullification' not in s.engine.pending_request.choices
    assert all(not d.startswith('delayed.') for d in s.engine.pending_request.choices)
    answer(s,'trick.ex_nihilo')
    assert set(materials)<=set(s.state.cards_in(ZoneRef(ZoneType.PROCESSING)))
    while s.engine.pending_request:
        s=restore(s); answer(s,PASS_RESPONSE)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==2
    assert set(materials)<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    uses=[e for e in s.events.events if isinstance(e,CardUsedEvent) and e.virtual_definition_id=='trick.ex_nihilo']
    assert len(uses)==1
    with pytest.raises(InvalidCardUse): s.engine.start_action(YJ2012Action('again','p1','qice'))

@pytest.mark.parametrize('suits,color,blocked',[
    ((Suit.SPADE,Suit.CLUB),Color.BLACK,True),
    ((Suit.HEART,Suit.DIAMOND),Color.RED,False),
    ((Suit.SPADE,Suit.HEART),None,False)])
def test_whole_material_color_weimu_and_target_restore(suits,color,blocked):
    s=setup('xun_you'); clear_hand(s); s.state.players['p2'].granted_skills['weimu']='test'
    for suit in suits:
        c=put(s,'basic.slash');s.state.cards[c]=replace(s.state.cards[c],suit=suit)
    handler=YJ2012Handler(s.skills,s.engine.reaction_provider.__self__,s.definitions,None)
    assert handler.qice_virtual(s.state,'p1','trick.iron_chain').color is color
    s.engine.start_action(YJ2012Action('qice','p1','qice')); answer(s,'trick.iron_chain')
    assert ('p2' not in s.engine.pending_request.allowed_player_ids)==blocked
    assert s.engine.pending_request.min_count==1
    s=restore(s); answer(s,('p1',)); finish(s)
    assert s.state.players['p1'].chained
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))

def test_empty_hand_has_no_qice():
    s=setup('xun_you'); clear_hand(s)
    with pytest.raises(InvalidCardUse):s.engine.start_action(YJ2012Action('qice','p1','qice'))


def test_hongyan_granted_and_suppressed_change_virtual_color_without_mutation():
    s=setup('xun_you');clear_hand(s)
    c=put(s,'basic.slash');s.state.cards[c]=replace(s.state.cards[c],suit=Suit.SPADE)
    handler=YJ2012Handler(s.skills,s.engine.reaction_provider.__self__,s.definitions,None)
    s.state.players['p1'].granted_skills['hongyan']='lease-test'
    assert handler.qice_virtual(s.state,'p1','trick.duel').color is Color.RED
    assert s.state.cards[c].suit is Suit.SPADE
    s.state.players['p1'].disabled_skills.add('hongyan')
    assert handler.qice_virtual(s.state,'p1','trick.duel').color is Color.BLACK


def test_qice_ai_conserves_peach_and_chooses_draw_trick():
    from sanguosha.decisions.ai import AIDecisionProvider
    s=setup('xun_you');clear_hand(s);put(s,'basic.slash')
    s.engine.start_action(YJ2012Action('qice','p1','qice'))
    d=AIDecisionProvider(human_id=None).decide(s.state,s.engine.pending_request)
    assert d.value=='trick.ex_nihilo'

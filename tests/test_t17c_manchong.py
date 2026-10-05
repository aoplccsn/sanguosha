from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t17c_juece import empty
from test_t6_military_basics import put
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.events import Event
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.model.enums import EquipmentSlot

def man():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_man_chong';return s

@pytest.mark.parametrize('give',[True,False])
def test_junxing_different_type_or_flip_draw_restore(give):
    s=man();empty(s,'p1');empty(s,'p2')
    costs=(put(s,'basic.slash'),put(s,'basic.dodge'))
    eligible=put(s,'trick.duel','p2');wrong=put(s,'basic.slash','p2')
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    s.engine.start_action(YJ2013Action('skill','p1','junxing'));s=restore(s);answer(s,costs)
    s=restore(s);answer(s,'p2');s=restore(s)
    assert eligible in s.engine.pending_request.eligible_card_ids and wrong not in s.engine.pending_request.eligible_card_ids
    answer(s,(eligible,) if give else ())
    assert s.state.players['p2'].face_up==give
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==before+(-1 if give else 2)
    assert all(c in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for c in costs)
    with pytest.raises(InvalidCardUse):s.engine.start_action(YJ2013Action('again','p1','junxing'))

def test_junxing_all_three_types_force_flip_delayed_counts_as_trick():
    s=man();empty(s,'p1');empty(s,'p2')
    costs=(put(s,'basic.slash'),put(s,'delayed.indulgence'),put(s,'equipment.weapon.serpent_spear'))
    put(s,'trick.duel','p2')
    s.engine.start_action(YJ2013Action('skill','p1','junxing'));answer(s,costs);answer(s,'p2')
    assert s.engine.pending_request is None and not s.state.players['p2'].face_up
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==4

@pytest.mark.parametrize('give',[True,False])
def test_yuce_damage_reveal_source_private_type_difference(give):
    s=man();empty(s,'p1');empty(s,'p2')
    revealed=put(s,'basic.dodge');wrong=put(s,'basic.slash','p2');eligible=put(s,'trick.duel','p2')
    hp=s.state.players['p1'].hp
    s.engine.start_action(MilitaryDamageAction('hurt','p2','p1',1));s=restore(s);answer(s,True)
    s=restore(s);answer(s,revealed);s=restore(s)
    assert s.engine.pending_request.player_id=='p2'
    assert s.engine.pending_request.eligible_card_ids==(eligible,)
    answer(s,(eligible,) if give else ())
    assert s.state.players['p1'].hp==hp-int(give)
    assert revealed in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    assert any(isinstance(e,Event) and e.event_type=='card_revealed' and e.metadata.get('card_id')==revealed for e in s.events.events)

def test_yuce_no_source_still_recover_and_empty_hand_no_offer():
    s=man();hp=s.state.players['p1'].hp
    s.engine.start_action(MilitaryDamageAction('hurt',None,'p1',1));answer(s,True);answer(s,s.engine.pending_request.eligible_card_ids[0])
    assert s.state.players['p1'].hp==hp
    empty(s,'p1');s.engine.start_action(MilitaryDamageAction('hurt2','p2','p1',1))
    assert s.engine.pending_request is None

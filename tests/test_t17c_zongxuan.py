from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.card_moves import CardMove,CardMoveReason
from sanguosha.engine.zongxuan import PendingDiscard
from sanguosha.engine.events import CardMovedEvent
from sanguosha.model.enums import Suit,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType

def game():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_yu_fan'
    return s

def discard(s,cards,zone=None):
    moves=s.engine.reaction_provider.__self__
    original=CardMove('cost',cards,zone or ZoneRef(ZoneType.HAND,'p1'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,'p1')
    moves.move(s.state,original)
    action=moves.next_reaction(s.state)
    assert isinstance(action,PendingDiscard)
    s.engine.start_action(action)
    return s

@pytest.mark.parametrize('count',[0,1,3])
def test_zongxuan_ordered_subset_before_discard_and_reconnect(count):
    s=game();cards=tuple(put(s,'basic.slash') for _ in range(3))
    before=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))
    s=discard(s,cards);s=restore(s)
    assert not set(cards)&set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    chosen=cards[::-1][:count];answer(s,chosen)
    assert s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))==tuple(reversed(chosen))+before
    assert set(cards)-set(chosen)<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    facts=[e for e in s.events.events if isinstance(e,CardMovedEvent) and e.event_id=='cost']
    assert len(facts)==int(count<3)
    if facts:assert facts[0].card_ids==tuple(c for c in cards if c not in chosen)

def test_zongxuan_precedes_luoying_and_selected_card_cannot_be_taken():
    s=game();s.state.players['p2'].character_id='yj2011_cao_zhi'
    cards=tuple(put(s,'basic.slash') for _ in range(2))
    for c in cards:s.state.cards[c]=replace(s.state.cards[c],suit=Suit.CLUB)
    s=discard(s,cards);answer(s,(cards[0],));s=restore(s)
    assert '落英' in s.engine.pending_request.prompt
    answer(s,True);assert s.engine.pending_request.eligible_card_ids==(cards[1],)
    answer(s,(cards[1],))
    assert s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]==cards[0]
    assert cards[1] in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))

@pytest.mark.parametrize('reason',[CardMoveReason.USE,CardMoveReason.RESPONSE,CardMoveReason.SYSTEM])
def test_zongxuan_only_discard_reason(reason):
    s=game();c=put(s,'basic.slash');moves=s.engine.reaction_provider.__self__
    moves.move(s.state,CardMove('other',(c,),ZoneRef(ZoneType.HAND,'p1'),ZoneRef(ZoneType.DISCARD_PILE),reason,'p1'))
    assert not any(isinstance(a,PendingDiscard) for a in moves.reactions)
    assert c in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

def test_zongxuan_equipment_loss_recovery_after_top_placement():
    s=game();s.state.players['p1'].hp=2
    zone=ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.ARMOR)
    c=put(s,'equipment.armor.silver_lion','p1',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s=discard(s,(c,),zone);s=restore(s);answer(s,(c,))
    assert s.state.players['p1'].hp==3
    assert s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]==c


def test_zongxuan_private_reservation_faces_and_desktop_click_order():
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from sanguosha.ui.main_window import MainWindow
    from sanguosha.projection import project_for_human
    app=QApplication.instance() or QApplication([])
    s=game();cards=tuple(put(s,'basic.slash') for _ in range(3));s=discard(s,cards);s=restore(s)
    own=project_for_human(s.state,s.definitions,'p1',{});other=project_for_human(s.state,s.definitions,'p2',{})
    own_pile=next(p for p in own.players if p.player_id=='p1').special_piles
    foreign_pile=next(p for p in other.players if p.player_id=='p1').special_piles
    assert {c.card_id for pile in own_pile.values() for c in pile}==set(cards)
    assert all(c.definition_id=='' for pile in foreign_pile.values() for c in pile)
    window=MainWindow(military=True)
    try:
        window.session=s
        window._card_clicked(cards[2]);window._card_clicked(cards[0])
        assert window._selected_card_order==[cards[2],cards[0]]
        assert window._public_card_label(cards[2],own)!='目标背面手牌'
    finally:window.close()


def test_equipment_replacement_is_not_discard_but_keeps_loss_effects():
    from sanguosha.engine.card_use import UseCardAction
    s=game();s.state.players['p1'].hp=2
    old=put(s,'equipment.armor.silver_lion','p1',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    new=put(s,'equipment.armor.vine')
    s.engine.start_action(UseCardAction('replace','p1',new))
    assert s.engine.pending_request is None
    assert s.state.players['p1'].hp==3
    assert s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.ARMOR))==(new,)
    assert old in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

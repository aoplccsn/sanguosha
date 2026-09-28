"""Military projection and actual target/confirm interface paths."""
import pytest
from PySide6.QtWidgets import QApplication
from test_t6_military_basics import game,put
from test_t6_equipment_chains import gear,clear_hand
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import RequestType,Decision,PASS_RESPONSE
from sanguosha.model.enums import Phase,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.projection import project_for_human
from sanguosha.ui.main_window import MainWindow

@pytest.fixture
def window():
    w=MainWindow(); w.show()
    yield w
    w.close()
    QApplication.processEvents()

def preview(w,s):
    w.session=s
    s.engine.start_action(PhaseAction('gui-play','p1',Phase.PLAY))
    w._render()

def confirm(w):
    button=next(b for b in w.decision.buttons if b.text()=='确定')
    assert button.isEnabled()
    button.click()

def test_default_gui_uses_original_160_physical_manifest(window):
    window.start_new_game(); window._tick_timer.stop()
    assert window.session.state.ruleset_id=='classic-military'
    assert len(window.session.state.cards)==160
    assert len({c.definition_id for c in window.session.state.cards.values()})==43
    assert not window.grab().isNull()

def test_iron_chain_two_targets_highlight_then_confirm(window):
    s=game(); card=put(s,'trick.iron_chain'); preview(window,s)
    request=s.engine.pending_request
    window._card_clicked(card); window._player_clicked('p2'); window._player_clicked('p3')
    assert s.engine.pending_request is request
    assert window.table.panels['p2'].selected_target and window.table.panels['p3'].selected_target
    confirm(window)
    while s.engine.pending_request and s.engine.pending_request.request_type is RequestType.RESPOND_WITH_CARD:
        r=s.engine.pending_request; s.engine.submit_decision(Decision(r.request_id,r.player_id,PASS_RESPONSE))
    assert s.state.players['p2'].chained and s.state.players['p3'].chained
    window._render()
    assert window.table.panels['p2'].view.chained

def test_iron_chain_recast_without_targets_is_confirmable(window):
    s=game(); card=put(s,'trick.iron_chain'); preview(window,s)
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    window._card_clicked(card); confirm(window)
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before

def test_equipment_and_judgment_are_public_without_opponent_hand_faces(window):
    s=game(); weapon=gear(s,'weapon.kylin_bow','p2'); delayed=put(s,'delayed.lightning','p2',ZoneType.JUDGMENT)
    window.session=s; window._render()
    view=project_for_human(s.state,s.definitions,'p1',s.character_names)
    opponent=next(p for p in view.players if p.player_id=='p2')
    assert opponent.equipment[0].card_id==weapon and opponent.judgments[0].card_id==delayed
    assert all(c.card_id not in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')) for c in view.hand)
    assert '麒麟弓' in window._public_card_label(weapon,view)
    assert not window.table.panels['p2'].grab().isNull()

def test_shared_pool_choices_expose_real_public_card_names(window):
    from sanguosha.engine.military_tricks import TargetTrick
    s=game(); card=put(s,'basic.wine','p1')
    # A named shared zone, identical to the five-grain runtime zone.
    src=ZoneRef(ZoneType.HAND,'p1'); dst=ZoneRef(ZoneType.SPECIAL,special_key='pool')
    from sanguosha.engine.card_moves import CardMoveService,CardMove,CardMoveReason
    CardMoveService(s.events).move(s.state,CardMove('pool-setup',(card,),src,dst,CardMoveReason.SYSTEM))
    s.engine.start_action(TargetTrick('pick','p1','p1',card,'trick.amazing_grace','pool'))
    window.session=s; window._render()
    assert any('酒' in b.text() for b in window.decision.buttons)
    next(b for b in window.decision.buttons if '酒' in b.text()).click()
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))

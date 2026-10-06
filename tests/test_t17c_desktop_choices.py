import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from sanguosha.ui.main_window import MainWindow
from sanguosha.engine.remaining_gods import RemainingGodAction
from sanguosha.projection import project_for_human
from test_t17c_poxi import ganning
from test_t17b_tier1 import answer


def test_desktop_poxi_private_faces_and_exact_suit_confirm_validation():
    app=QApplication.instance() or QApplication([])
    window=MainWindow(military=True)
    try:
        s,cards=ganning(2)
        s.engine.start_action(RemainingGodAction('poxi','p1','poxi'));answer(s,'p2')
        window.session=s
        view=project_for_human(s.state,s.definitions,'p1',{})
        request=s.engine.pending_request
        window._selected_cards=set(cards[:3]);window._render_request(request,view)
        confirm=next(b for b in window.decision.buttons if b.text().startswith('确认弃置'))
        assert not confirm.isEnabled()
        window._selected_cards=set(cards);window._render_request(request,view)
        confirm=next(b for b in window.decision.buttons if b.text().startswith('确认弃置'))
        assert confirm.isEnabled()
        assert all(window._public_card_label(c,view)!='目标背面手牌' for c in cards[2:])
        from dataclasses import replace
        bad=replace(request,exclusive_card_groups=((cards[0],cards[2]),(cards[1],),(cards[3],)))
        window._render_request(bad,view)
        assert not next(b for b in window.decision.buttons if b.text().startswith('确认弃置')).isEnabled()
    finally:window.close()

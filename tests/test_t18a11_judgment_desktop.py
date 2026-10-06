"""Desktop consumer of public judgment facts; scoped presentation regression."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from test_t18a11_judgment_system import game
from sanguosha.engine.events import Event
from sanguosha.ui.main_window import MainWindow
from sanguosha.model.zones import ZoneRef, ZoneType


def test_desktop_reveal_retrial_final_and_delayed_outcome(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(military=True)
    try:
        s = game()
        cid = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
        window.session = s
        window._seen_events = len(s.events.events)
        public, judgments = [], []
        monkeypatch.setattr(window.table, 'play_public_event', lambda *args: public.append(args))
        monkeypatch.setattr(window.table, 'play_judgment', lambda *args: judgments.append(args))
        for kind in ('judgment_card_revealed', 'judgment_card_replaced', 'judgment_result'):
            s.events.record(Event('audit:'+kind, kind, 'p1', metadata={
                'card_id': str(cid), 'effective_suit': 'heart', 'matched': True}))
        message = '\u4e50\u4e0d\u601d\u8700\uff1a\u8df3\u8fc7\u51fa\u724c\u9636\u6bb5'
        s.events.record(Event('audit:delayed', 'delayed_result', 'p1', metadata={
            'message': message, 'definition_id': 'delayed.indulgence'}))
        window._render()
        assert public[0][0].startswith('\u5224\u5b9a\u7ffb\u724c\uff1a\u2665')
        assert public[1][0].startswith('\u6539\u5224\uff1a\u2665')
        assert judgments[0][0].startswith('\u2665') and judgments[0][2] is True
        assert public[-1] == (message, 'delayed.indulgence')
        monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
        monkeypatch.delenv('SANGUOSHA_FAST_AI', raising=False)
        delays = []
        monkeypatch.setattr(window._tick_timer, 'start', lambda delay: delays.append(delay))
        window._tick_scheduled = False
        window._schedule_tick()
        assert delays == [2500]

    finally:
        window.close()

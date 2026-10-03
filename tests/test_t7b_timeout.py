"""Human setup and engine decisions share the sixty-second policy."""

from sanguosha.engine.phases import PhaseAction
from sanguosha.model.enums import Phase
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession
from sanguosha.ui.main_window import HUMAN_DECISION_TIMEOUT_MS, MainWindow
from sanguosha.ui.pregame_dialog import PregameDialog
from sanguosha.ui.timing import PREGAME_GENERAL_TIMEOUT_MS


def test_human_pending_request_and_general_draft_use_sixty_seconds():
    assert HUMAN_DECISION_TIMEOUT_MS == PREGAME_GENERAL_TIMEOUT_MS == 60_000
    setup = Pregame.create(4)
    dialog = PregameDialog(setup)
    dialog._reveal_identity()
    dialog._show_candidates()
    assert dialog._timer.interval() == 60_000
    dialog.close()

    session = GameSession.new_game(military=True, five_generals=True)
    session.state.current_player_id = session.human_id
    session.state.turn_number = 1
    session.engine.start_action(PhaseAction('timeout-play', session.human_id, Phase.PLAY))
    window = MainWindow()
    window.session = session
    window._render()
    assert window._decision_remaining_ms == 60_000
    assert window.table.panels['p1'].decision_progress == 1.0
    window._decision_countdown()
    assert window._decision_remaining_ms == 59_900
    assert window.table.panels['p1'].decision_progress == 59_900 / 60_000
    window.close()

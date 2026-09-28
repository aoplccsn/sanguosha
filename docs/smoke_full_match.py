"""Exercise a complete offscreen match through MainWindow's Decision path."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SANGUOSHA_FAST_AI"] = "1"
from PySide6.QtWidgets import QApplication
from sanguosha.model.state import GameStatus
from sanguosha.ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])
window = MainWindow(military=False)
window.show()
window.start_new_game()
steps = 0
while window.session.state.status is not GameStatus.FINISHED and steps < 10000:
    request = window.session.engine.pending_request
    if request and request.player_id == window.session.human_id:
        decision = window.session.ai.decide(window.session.state, request)
        window._submit_value(decision.value)
    else:
        window._tick()
    app.processEvents()
    steps += 1
assert window.session.state.status is GameStatus.FINISHED, steps
print("finished", steps, "steps", window.session.state.victory.label)
window.close()

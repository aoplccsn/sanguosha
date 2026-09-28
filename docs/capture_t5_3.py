"""Save offscreen T5.3 play, selected-target and dodge-response views."""
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SANGUOSHA_FAST_AI"] = "1"
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from sanguosha.content.cards.ids import DODGE_ID, SLASH_ID
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow


def save(window: MainWindow, name: str) -> None:
    for _ in range(5):
        QApplication.processEvents()
    target = Path(__file__).with_name(name)
    assert window.grab().save(str(target))
    print(target)


app = QApplication.instance() or QApplication([])
QFontDatabase.addApplicationFont("C:/Windows/Fonts/simhei.ttf")
app.setFont(QFont("Microsoft YaHei UI", 10))
window = MainWindow()
window.show()
window.start_new_game()
for _ in range(12):
    app.processEvents()
save(window, "t5_3_table.png")
request = window.session.engine.pending_request
slash_id = next(choice[4:] for choice in request.choices if choice.startswith("use:") and
                window.session.state.cards[CardInstanceId(choice[4:])].definition_id == SLASH_ID)
window._card_clicked(slash_id)
window._player_clicked("p3")
save(window, "t5_3_target_confirm.png")

window.session = GameSession.new_game(6)
slash_id = next(cid for cid, card in window.session.state.cards.items() if card.definition_id == SLASH_ID)
window.session.engine.start_action(SlashEffectAction("t53-smoke-attack", PlayerId("p3"), PlayerId("p1"), slash_id, DODGE_ID))
window._render()
save(window, "t5_3_dodge_response.png")
window.close()

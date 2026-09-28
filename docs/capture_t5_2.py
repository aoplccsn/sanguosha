"""Capture the current T5.2 table at 1440 × 900 without opening a window."""
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SANGUOSHA_FAST_AI"] = "1"
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from sanguosha.ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])
QFontDatabase.addApplicationFont("C:/Windows/Fonts/simhei.ttf")
app.setFont(QFont("Microsoft YaHei UI", 10))
window = MainWindow()
window.show()
window.start_new_game()
for _ in range(12):
    app.processEvents()
target = Path(__file__).with_name("t5_2_smoke.png")
assert window.grab().save(str(target))
print(target)
print(window.status_label.text(), "hand", len(window.hand.cards))
window.close()

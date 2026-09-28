"""Launch a real offscreen match and save a visual smoke screenshot."""
import os
from pathlib import Path
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SANGUOSHA_FAST_AI"] = "1"
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from sanguosha.ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])
QFontDatabase.addApplicationFont("C:/Windows/Fonts/simhei.ttf")
app.setFont(QFont("Microsoft YaHei UI", 10))
window = MainWindow()
window.show()
window.start_new_game()
for _ in range(12):
    app.processEvents()
window.grab().save(str(Path(__file__).with_name("t5_1_smoke.png")))
print(window.status_label.text())
print("hand", len(window.hand.cards), "pixels", window.size().width(), window.size().height())
window.close()

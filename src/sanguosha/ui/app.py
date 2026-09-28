"""Qt application launcher."""

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    windows_font = Path("C:/Windows/Fonts/simhei.ttf")
    if windows_font.is_file():
        QFontDatabase.addApplicationFont(str(windows_font))
    for family in ("Microsoft YaHei UI", "SimHei", "SimSun"):
        if family in QFontDatabase.families():
            app.setFont(QFont(family, 10))
            break
    window = MainWindow()
    window.show()
    return app.exec()

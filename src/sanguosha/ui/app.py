"""Qt application launcher."""

import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMessageBox

from sanguosha.paths import local_app_data

from .main_window import MainWindow


def _install_crash_handler() -> None:
    def handle(exc_type, exc_value, exc_traceback):
        log_dir = local_app_data() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"crash-{datetime.now():%Y%m%d-%H%M%S}.log"
        path.write_text(
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            encoding="utf-8",
        )
        QMessageBox.critical(None, "三国杀", f"游戏发生错误，日志已保存到：\n{path}")
    sys.excepthook = handle


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    _install_crash_handler()
    windows_font = Path("C:/Windows/Fonts/simhei.ttf")
    if windows_font.is_file():
        QFontDatabase.addApplicationFont(str(windows_font))
    for family in ("Microsoft YaHei UI", "SimHei", "SimSun"):
        if family in QFontDatabase.families():
            app.setFont(QFont(family, 10))
            break
    window = MainWindow()
    window.show()
    if __import__("os").environ.get("SANGUOSHA_SMOKE_TEST"):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1200, app.quit)
    return app.exec()

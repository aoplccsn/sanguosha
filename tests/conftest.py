"""Keep one QApplication alive across the complete Qt regression suite."""
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def qt_application_lifetime():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()

@pytest.fixture(autouse=True)
def qt_widget_lifetime(qt_application_lifetime):
    """Release test-owned top-level widgets before the next test processes events."""
    yield
    from PySide6.QtCore import QCoreApplication, QEvent, QAbstractAnimation
    for widget in qt_application_lifetime.topLevelWidgets():
        for animation in widget.findChildren(QAbstractAnimation):
            animation.stop()
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qt_application_lifetime.processEvents()

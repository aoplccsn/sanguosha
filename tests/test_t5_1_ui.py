"""Focused offscreen checks for artwork, visibility and adaptive widgets."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import pytest
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication
from sanguosha.projection import CardView
from sanguosha.model.ids import CardInstanceId
from sanguosha.ui.card_widget import CardWidget
from sanguosha.ui.resources import ResourceManager, RESOURCES
from sanguosha.ui.main_window import MainWindow

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

def test_resource_fallback_and_manifest(app):
    manager = ResourceManager(Path(__file__).parent / "missing_assets")
    assert not manager.general_portrait("missing", "某将").isNull()
    assert not manager.card_art("basic.missing").isNull()
    assert not RESOURCES.card_art("basic.slash").isNull()
    assert not RESOURCES.table_background().isNull()

def test_card_state(app):
    card = CardWidget(CardView(CardInstanceId("x"), "杀", "♠", "7", "basic.slash"))
    card.set_selectable(True)
    card.set_selected(True)
    assert card.isEnabled() and card._selected
    card.set_selectable(False)
    assert not card.isEnabled()

def test_table_privacy_target_prompt_resize(app):
    window = MainWindow(military=False)
    window.show()
    window.start_new_game()
    app.processEvents()
    assert "未知" in window.table.panels["p3"].text()
    assert "手牌" in window.table.panels["p3"].text()
    assert window.decision.prompt_label.text()
    assert len(window.hand.cards) == 6
    window.resize(1280, 720)
    app.processEvents()
    assert window.table.panels["p1"].geometry().right() <= window.table.width()
    window.close()

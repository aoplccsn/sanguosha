"""Artwork and offscreen interaction checks for the T5.2 presentation layer."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from PySide6.QtWidgets import QApplication
from sanguosha.model.ids import CardInstanceId
from sanguosha.projection import CardView
from sanguosha.ui.card_widget import CardWidget
from sanguosha.ui.decision_controller import DecisionController
from sanguosha.ui.main_window import MainWindow
from sanguosha.ui.resources import RESOURCES, ResourceManager


def test_art_manifest_and_fallback():
    app = QApplication.instance() or QApplication([])
    for key in ("general.caocao", "general.liubei", "general.sunquan", "general.lvbu", "general.guanyu",
                "basic.slash", "basic.dodge", "basic.peach", "default.general"):
        assert (RESOURCES.root / RESOURCES.manifest[key]).is_file()
    assert not RESOURCES.general_portrait("unknown", "无名将").isNull()
    assert RESOURCES.general_portrait("unknown").toImage() != RESOURCES.general_portrait("other_unknown").toImage()
    assert RESOURCES.general_portrait("unknown").toImage() == RESOURCES.general_portrait("unknown").toImage()
    assert not ResourceManager(Path("missing")).card_art("basic.slash").isNull()


def test_card_panel_prompt_and_offscreen_render():
    app = QApplication.instance() or QApplication([])
    card = CardWidget(CardView(CardInstanceId("art-1"), "杀", "♠", "7", "basic.slash"))
    card.set_selectable(True)
    card.set_selected(True)
    assert not card.grab().isNull()
    card.set_selectable(False)
    assert not card.grab().isNull() and not card.isEnabled()
    prompt = DecisionController()
    prompt.render("请选择目标", [("取消", None, True)])
    assert prompt.buttons[0].isEnabled()
    prompt.render("等待响应", [("不出", None, False)])
    assert not prompt.buttons[0].isEnabled()
    window = MainWindow(military=False)
    window.show()
    window.start_new_game()
    app.processEvents()
    assert all(not panel.grab().isNull() for panel in window.table.panels.values())
    assert not window.grab().isNull()
    window.close()

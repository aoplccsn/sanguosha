"""T5.1 presentation invariants: file replacement, privacy, animation and resizing."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import replace
import json
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from sanguosha.model.ids import CardInstanceId
from sanguosha.projection import CardView, project_for_human
from sanguosha.session import GameSession
from sanguosha.ui.resources import ResourceManager, RESOURCES
from sanguosha.ui.card_widget import CardWidget
from sanguosha.ui.player_panel import PlayerPanel
from sanguosha.ui.hand_view import HandView
from sanguosha.ui.hud import PromptPanel, ActionBar
from sanguosha.ui.main_window import MainWindow

@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])

def test_replacement_removal_and_corrupt_asset(app, tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"basic.slash":"slash.png", "default.card":"fallback.png"}))
    pix = QPixmap(300, 390)
    pix.fill(QColor("red"))
    pix.save(str(tmp_path / "slash.png"))
    pix.fill(QColor("blue"))
    pix.save(str(tmp_path / "fallback.png"))
    manager = ResourceManager(tmp_path)
    assert manager.card_art("basic.slash").toImage().pixelColor(100,100) == QColor("red")
    (tmp_path / "slash.png").unlink()
    assert manager.card_art("basic.slash").toImage().pixelColor(100,100) == QColor("blue")
    (tmp_path / "slash.png").write_bytes(b"invalid picture")
    assert manager.card_art("basic.slash").toImage().pixelColor(100,100) == QColor("blue")
    pix.fill(QColor("green"))
    pix.save(str(tmp_path / "slash.png"))
    assert manager.card_art("basic.slash").toImage().pixelColor(100,100) == QColor("green")

def test_named_portrait_fallback_and_stable_id(app, tmp_path):
    manager = ResourceManager(tmp_path)
    assert manager.general_portrait("unknown", "张三").toImage() != manager.general_portrait("unknown", "李四").toImage()
    assert manager.general_portrait("unknown").toImage() != manager.general_portrait("other").toImage()
    assert manager.general_portrait("unknown").toImage() == manager.general_portrait("unknown").toImage()
    assert RESOURCES.general_portrait("general.caocao").toImage() == RESOURCES.general_portrait("caocao").toImage()

def test_all_manifest_assets_load(app):
    for key in RESOURCES.manifest:
        assert not QPixmap(str(RESOURCES.root / RESOURCES.manifest[key])).isNull(), key

def test_card_future_category_and_hover(app):
    card = CardWidget(CardView(CardInstanceId("future"), "示例锦囊", "♥", "A", "trick.example", "trick"))
    card.set_selectable(True)
    card.show()
    QTest.mouseMove(card, card.rect().center())
    QTest.qWait(150)
    assert card._hover and card._lift > 0
    assert card.category_label == "锦囊牌"
    card.set_selected(True)
    QTest.qWait(150)
    assert card._selected and card._lift == 10
    card.close()

def test_large_hand_stays_inside_on_resize(app):
    hand = HandView()
    hand.resize(760, 180)
    hand.render(tuple(CardView(CardInstanceId(f"c{i}"), "杀", "♠", "7", "basic.slash") for i in range(40)), set(), set())
    hand.show()
    app.processEvents()
    for width in (760, 1280, 600):
        hand.resize(width,180)
        app.processEvents()
        assert all(card.geometry().left() >= 0 and card.geometry().right() < width for card in hand.cards.values())
    hand.close()

def test_projection_hides_cards_identity_and_maps_art_id(app):
    session = GameSession.new_game()
    view = project_for_human(session.state, session.definitions, session.human_id, session.character_names)
    assert view.players[0].character_id == "caocao"
    for player in view.players[1:]:
        assert player.identity_label == "未知"
        assert not hasattr(player, "hand")
    assert all(c.card_id in session.state.cards_in(__import__("sanguosha.model.zones", fromlist=["ZoneRef"]).ZoneRef(
        __import__("sanguosha.model.zones", fromlist=["ZoneType"]).ZoneType.HAND, session.human_id)) for c in view.hand)

def test_player_damage_death_and_turn_animation(app):
    session = GameSession.new_game()
    v = project_for_human(session.state, session.definitions, session.human_id, session.character_names).players[1]
    panel = PlayerPanel("p2")
    panel.show()
    panel.render(v, False, False)
    panel.render(replace(v, hp=3, active=True), True, True)
    QTest.qWait(60)
    assert panel.damage_flash > 0 and panel.turn_glow > 0 and panel.targetable
    panel.render(replace(v, hp=0, alive=False, identity_label="忠臣"), False, False)
    QTest.qWait(450)
    assert panel.death_opacity == 1 and "忠臣" in panel.text() and "阵亡" in panel.text()
    panel.close()

def test_prompt_and_action_bar_are_contextual(app):
    prompt = PromptPanel()
    prompt.present("玩家3 对你使用【杀】 · 请选择【闪】响应")
    assert prompt.mode == "response"
    prompt.present("请选择【杀】的目标")
    assert prompt.mode == "target"
    bar = ActionBar()
    bar.present([("确定", "confirm", False), ("取消", "cancel", True)])
    assert not bar.buttons[0].isEnabled() and bar.buttons[1].isEnabled()
    bar.present([])
    assert bar.isHidden() and not bar.buttons

def test_table_layout_phase_and_log_toggle(app):
    w = MainWindow(military=False)
    w.show()
    w.start_new_game()
    app.processEvents()
    assert w.table.phase_indicator.phase == "play"
    for width, height in ((1280,720),(1440,900),(1700,1000)):
        w.resize(width,height)
        app.processEvents()
        rects = [p.geometry() for p in w.table.panels.values()]
        assert all(w.table.rect().contains(r) for r in rects)
        assert all(not a.intersects(b) for i,a in enumerate(rects) for b in rects[i+1:])
        assert w.table.panels["p1"].height() > w.table.panels["p2"].height()
    w.log_toggle.setChecked(False)
    assert w.log.isHidden()
    w.close()

def test_gui_timer_delay_and_fast_mode(app, monkeypatch):
    import sanguosha.ui.main_window as module
    delays = []
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("SANGUOSHA_FAST_AI", raising=False)
    w = MainWindow(military=False)
    monkeypatch.setattr(w._tick_timer, "start", lambda delay: delays.append(delay))
    w._schedule_tick()
    assert delays == [500]
    w._tick_scheduled = False
    monkeypatch.setenv("SANGUOSHA_FAST_AI", "1")
    w._schedule_tick()
    assert delays[-1] == 0
    w.close()

def test_closed_window_cancels_owned_timer(app):
    w = MainWindow(military=False)
    w.start_new_game()
    assert w._tick_timer.isActive()
    w.close()
    assert not w._tick_timer.isActive()
    events = len(w.session.events.events)
    w._schedule_tick()
    w._tick()
    app.processEvents()
    assert len(w.session.events.events) == events

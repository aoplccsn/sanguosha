"""Capture representative offscreen T6.5 screens at supported sizes."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["SANGUOSHA_FAST_AI"] = "1"

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtCore import QPoint
from sanguosha.content.cards.ids import DODGE_ID, SLASH_ID
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.military_tricks import TargetTrick
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.model.enums import Phase, EquipmentSlot, PlayerStatus
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_t6_military_basics import game, put
from test_t6_equipment_chains import gear

OUT = Path(__file__).with_name("t6_5_screenshots")


def save(window, name, size=None):
    if size:
        window.resize(*size)
    for _ in range(8):
        QApplication.processEvents()
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{name}.png"
    assert window.grab().save(str(path))
    print(path)


def main():
    app = QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/simhei.ttf")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = MainWindow()
    window.show()
    session = game()
    slash = put(session, SLASH_ID)
    session.engine.start_action(PhaseAction("t65-capture-play", "p1", Phase.PLAY))
    window.session = session
    window._render()
    for size in ((1280, 720), (1600, 900), (1920, 1080)):
        save(window, f"table_{size[0]}x{size[1]}", size)
    window.resize(1600, 900)
    large = game()
    for _ in range(18):
        put(large, "basic.slash")
    large.engine.start_action(PhaseAction("t65-capture-large-hand", "p1", Phase.PLAY))
    window.session = large
    window._render()
    save(window, "large_hand")
    window.session = session
    window._render()
    window._card_clicked(slash)
    legal = sorted(window.interaction.legal_targets)
    if legal:
        window._player_clicked(legal[0])
        save(window, "target_confirm")
    window.session = GameSession.new_game(6)
    slash = next(cid for cid, card in window.session.state.cards.items() if card.definition_id == SLASH_ID)
    window.session.engine.start_action(SlashEffectAction(
        "t65-capture-attack", PlayerId("p3"), PlayerId("p1"), slash, DODGE_ID))
    window._render()
    save(window, "dodge_response")

    session = game()
    gear(session, "weapon.kylin_bow", "p2")
    put(session, "delayed.lightning", "p2", ZoneType.JUDGMENT)
    window.session = session
    window._render()
    save(window, "equipment_and_judgment")
    panel = window.table.panels["p2"]
    QTest.mouseMove(panel, QPoint(int(panel.width()*.53)+8, 108))
    preview_path = OUT / "equipment_hover_preview.png"
    assert panel._equipment_preview.grab().save(str(preview_path))
    print(preview_path)
    QTest.mouseMove(panel, QPoint(5, 5))
    session.state.players["p3"].chained = True
    window._render()
    save(window, "chain_state")
    session.state.players["p5"].status = PlayerStatus.DEAD
    session.state.players["p5"].hp = 0
    session.state.revealed_identities.add("p5")
    window.session = session
    window._render()
    QTest.qWait(450)
    save(window, "player_death")

    session = game()
    card = put(session, "basic.wine")
    CardMoveService(session.events).move(session.state, CardMove(
        "t65-pool", (card,), ZoneRef(ZoneType.HAND, "p1"),
        ZoneRef(ZoneType.SPECIAL, special_key="pool"), CardMoveReason.SYSTEM))
    session.engine.start_action(TargetTrick(
        "t65-pick", "p1", "p1", card, "trick.amazing_grace", "pool"))
    window.session = session
    window._render()
    save(window, "shared_pool")
    window._shared_card_clicked(card)
    save(window, "shared_pool_selected")

    session = game()
    put(session, "trick.nullification")
    session.engine.start_action(RespondWithCardAction(
        "t65-nullification", "p1", "trick.nullification", "t65-trick",
        "无懈可击：响应锦囊或反制上一张无懈", "p2"))
    window.session = session
    window._render()
    save(window, "nullification_response")

    session = game()
    session.state.current_phase = Phase.JUDGMENT
    window.session = session
    window._render()
    save(window, "judgment_waiting")
    window.table.play_judgment("闪", "basic.dodge", False)
    save(window, "judgment_card_back")
    QTest.qWait(220)
    save(window, "judgment_reveal")
    QTest.qWait(330)
    save(window, "judgment_result")

    session = game()
    lightning = put(session, "delayed.lightning", "p2", ZoneType.JUDGMENT)
    window.session = session
    window._seen_events = len(session.events.events)
    CardMoveService(session.events).move(session.state, CardMove(
        "t65-lightning-transfer", (lightning,), ZoneRef(ZoneType.JUDGMENT, "p2"),
        ZoneRef(ZoneType.JUDGMENT, "p3"), CardMoveReason.SYSTEM))
    window._render()
    save(window, "judgment_transfer")
    window.close()


if __name__ == "__main__":
    main()

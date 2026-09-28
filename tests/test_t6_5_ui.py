"""T6.5 layout and privacy-facing presentation regression checks."""
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from sanguosha.projection import CardView, project_for_human
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.military_tricks import TargetTrick
from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
from sanguosha.model.zones import ZoneRef, ZoneType
from test_t6_military_basics import game, put
from test_t6_equipment_chains import gear


def test_table_seats_fit_supported_windows():
    window = MainWindow()
    window.show()
    window.start_new_game()
    window._tick_timer.stop()
    for width, height in ((1280, 720), (1600, 900), (1920, 1080)):
        window.resize(width, height)
        QApplication.processEvents()
        table = window.table
        bounds = table.rect()
        assert all(bounds.contains(panel.geometry()) for panel in table.panels.values())
        assert not table.panels["p3"].geometry().intersects(table.panels["p4"].geometry())
        assert not table.panels["p1"].geometry().intersects(table.panels["p2"].geometry())
        assert not table.panels["p1"].geometry().intersects(table.panels["p5"].geometry())
        assert not window.grab().isNull()
    window.close()


def test_large_hand_overlaps_without_shrinking_cards():
    window = MainWindow()
    window.resize(1280, 720)
    window.show()
    cards = tuple(CardView(f"test-{i}", "杀", "♠", str(i % 13 + 1)) for i in range(25))
    window.hand.render(cards, {str(card.card_id) for card in cards}, set())
    QApplication.processEvents()
    widgets = list(window.hand.cards.values())
    assert all(widget.width() == widgets[0].width() for widget in widgets)
    assert 0 < widgets[1].x() - widgets[0].x() < widgets[0].width()
    assert widgets[-1].geometry().right() <= window.hand.width()
    removed = widgets[-1]
    window.hand.render(cards[:1], {str(cards[0].card_id)}, set())
    assert not removed.isVisible()
    window.close()


def test_hidden_identity_seal_uses_projection_only():
    session = GameSession.new_game(military=True)
    view = project_for_human(session.state, session.definitions, session.human_id, session.character_names)
    window = MainWindow()
    window.show()
    window.session = session
    window._render()
    for player in view.players:
        panel = window.table.panels[str(player.player_id)]
        assert panel.view.identity_label == player.identity_label
        if str(player.player_id) != "p1":
            assert player.identity_label == "未知"
            assert "未知" in panel.text()
    hidden = session.state.cards_in(ZoneRef(ZoneType.HAND, "p2"))[0]
    label = window._public_card_label(hidden, view)
    assert str(hidden) not in label
    assert label == "目标背面手牌"
    window.close()


def test_reused_card_id_refreshes_art_after_new_game():
    window = MainWindow()
    first = CardView("same-id", "杀", "♠", "A", "basic.slash")
    second = CardView("same-id", "桃", "♥", "K", "basic.peach")
    window.hand.render((first,), {"same-id"}, set())
    window.hand.render((second,), {"same-id"}, set())
    assert window.hand.cards["same-id"].card == second
    window.close()


def test_shared_pool_requires_visible_selection_and_confirmation():
    session = game()
    card = put(session, "basic.wine")
    CardMoveService(session.events).move(session.state, CardMove(
        "ui-pool", (card,), ZoneRef(ZoneType.HAND, "p1"),
        ZoneRef(ZoneType.SPECIAL, special_key="pool"), CardMoveReason.SYSTEM))
    session.engine.start_action(TargetTrick("pick", "p1", "p1", card, "trick.amazing_grace", "pool"))
    window = MainWindow()
    window.session = session
    window.show()
    window._render()
    request = session.engine.pending_request
    confirm = next(button for button in window.decision.buttons if button.text() == "确认选择")
    assert not confirm.isEnabled()
    window._shared_card_clicked(card)
    assert session.engine.pending_request is request
    confirm = next(button for button in window.decision.buttons if button.text() == "确认选择")
    assert confirm.isEnabled()
    confirm.click()
    assert card in session.state.cards_in(ZoneRef(ZoneType.HAND, "p1"))
    window.close()


def test_judgment_visual_sequence_finishes_without_blocking_ui():
    window = MainWindow()
    window.show()
    window.table.play_judgment("闪", "basic.dodge", True)
    assert window.table._judgment_stage == 0
    QTest.qWait(210)
    assert window.table._judgment_stage == 1
    QTest.qWait(330)
    assert window.table._judgment_stage == 2
    QTest.qWait(450)
    assert window.table._judgment_stage == -1
    window.close()


def test_public_judgment_event_starts_center_animation():
    session = game()
    session.engine.start_action(JudgmentAction("ui-judgment", "p1", JudgmentPattern()))
    window = MainWindow()
    window.session = session
    window.show()
    window._render()
    assert window.table._judgment_stage == 0
    window.close()


def test_public_delayed_card_transfer_is_presented():
    session = game()
    card = put(session, "delayed.lightning", "p2", ZoneType.JUDGMENT)
    window = MainWindow()
    window.session = session
    window._seen_events = len(session.events.events)
    window.show()
    CardMoveService(session.events).move(session.state, CardMove(
        "ui-lightning-transfer", (card,), ZoneRef(ZoneType.JUDGMENT, "p2"),
        ZoneRef(ZoneType.JUDGMENT, "p3"), CardMoveReason.SYSTEM))
    window._render()
    assert "判定牌转移" in window.table._event_text
    window.close()


def test_equipment_slot_hover_shows_full_card_preview():
    session = game()
    gear(session, "weapon.kylin_bow", "p2")
    window = MainWindow()
    window.session = session
    window.show()
    window._render()
    panel = window.table.panels["p2"]
    QTest.mouseMove(panel, QPoint(int(panel.width()*.53)+8, 108))
    assert panel._equipment_preview.card.name == "麒麟弓"
    assert panel._equipment_preview.isVisible()
    window.close()

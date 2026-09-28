"""T6.5 layout and privacy-facing presentation regression checks."""
from PySide6.QtWidgets import QApplication
from sanguosha.projection import CardView, project_for_human
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.military_tricks import TargetTrick
from sanguosha.model.zones import ZoneRef, ZoneType
from test_t6_military_basics import game, put


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

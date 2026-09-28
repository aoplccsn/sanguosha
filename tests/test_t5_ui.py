"""Qt offscreen smoke tests for the real desktop widgets and Decision path."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sanguosha.content.cards.ids import DODGE_ID, SLASH_ID
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.engine.requests import RequestType
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    widget = MainWindow(military=False)
    widget.show()
    QTest.qWait(30)
    yield widget
    widget.close()
    app.processEvents()


def start(window):
    QTest.mouseClick(window.new_game_button, Qt.LeftButton)
    QTest.qWait(100)
    assert window.session is not None
    assert window.session.engine.pending_request is not None


def test_five_seat_table_human_hand_and_hidden_identity(window):
    start(window)
    assert set(window.table.panels) == {"p1", "p2", "p3", "p4", "p5"}
    assert len(window.hand.cards) == 6  # Four initial cards plus two from draw phase.
    assert "主公" in window.table.panels["p1"].text()
    assert "未知" in window.table.panels["p3"].text()
    assert "手牌" in window.table.panels["p3"].text()
    assert window.session.engine.pending_request.request_type is RequestType.CHOOSE_OPTION


def test_click_slash_then_target_and_ai_automatically_responds(window):
    start(window)
    session = window.session
    request = session.engine.pending_request
    slash_id = next(choice[4:] for choice in request.choices if choice.startswith("use:") and session.state.cards[CardInstanceId(choice[4:])].definition_id == SLASH_ID)
    QTest.mouseClick(window.hand.cards[slash_id], Qt.LeftButton)
    assert session.engine.pending_request is request
    QTest.mouseClick(window.table.panels["p3"], Qt.LeftButton)
    assert session.engine.pending_request is request
    confirm = next(button for button in window.decision.buttons if button.text() == "确定")
    QTest.mouseClick(confirm, Qt.LeftButton)
    assert session.engine.pending_request.request_type is RequestType.RESPOND_WITH_CARD
    QTest.qWait(130)
    assert session.engine.pending_request.request_type is RequestType.CHOOSE_OPTION
    assert session.engine.pending_request.player_id == PlayerId("p1")
    assert CardInstanceId(slash_id) in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert "使用【杀】" in window.log.toPlainText()


def test_human_clicks_real_dodge_in_response(window):
    window.session = GameSession.new_game(6)
    session = window.session
    dodge_id = next(cid for cid in session.state.cards_in(ZoneRef(ZoneType.HAND, PlayerId("p1"))) if session.state.cards[cid].definition_id == DODGE_ID)
    slash_id = next(cid for cid, card in session.state.cards.items() if card.definition_id == SLASH_ID)
    session.engine.start_action(SlashEffectAction("ui-attack", PlayerId("p3"), PlayerId("p1"), slash_id, DODGE_ID))
    window._render()
    assert session.engine.pending_request.request_type is RequestType.RESPOND_WITH_CARD
    assert str(dodge_id) in window.hand.cards
    QTest.mouseClick(window.hand.cards[str(dodge_id)], Qt.LeftButton)
    assert session.state.players[PlayerId("p1")].hp == 4
    assert dodge_id not in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    confirm = next(button for button in window.decision.buttons if button.text() == "确认响应")
    QTest.mouseClick(confirm, Qt.LeftButton)
    assert dodge_id in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_peach_click_and_discard_multiselect(window):
    QTest.mouseClick(window.new_game_button, Qt.LeftButton)
    session = window.session
    session.state.players[PlayerId("p1")].hp = 3
    QTest.qWait(100)
    request = session.engine.pending_request
    peach_id = next(choice[4:] for choice in request.choices if choice.startswith("use:") and session.state.cards[CardInstanceId(choice[4:])].definition_id == "basic.peach")
    QTest.mouseClick(window.hand.cards[peach_id], Qt.LeftButton)
    assert session.state.players[PlayerId("p1")].hp == 4
    # Lower HP for a precise discard request after ending play.
    session.state.players[PlayerId("p1")].hp = 2
    window._render()
    end_button = next(button for button in window.decision.buttons if button.text() == "结束出牌阶段")
    QTest.mouseClick(end_button, Qt.LeftButton)
    assert session.engine.pending_request.request_type is RequestType.CHOOSE_CARDS
    count = session.engine.pending_request.min_count
    ids = list(window.hand.cards)[:count]
    for card_id in ids:
        QTest.mouseClick(window.hand.cards[card_id], Qt.LeftButton)
    confirm = next(button for button in window.decision.buttons if button.text().startswith("确认弃置"))
    assert confirm.isEnabled()
    QTest.mouseClick(confirm, Qt.LeftButton)
    QTest.qWait(150)
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, PlayerId("p1")))) == 2
    assert session.state.turn_number >= 2  # AI turn advances without a separate user click.


def test_death_updates_portrait_and_reveals_identity(window):
    from sanguosha.engine.death import DeathAction

    window.session = GameSession.new_game(6)
    window.session.engine.start_action(DeathAction("ui-death", PlayerId("p3"), PlayerId("p1")))
    window._render()
    text = window.table.panels["p3"].text()
    assert "阵亡" in text
    assert "反贼" in text

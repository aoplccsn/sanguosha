"""Confirmation, highlight and attack-context tests for the desktop GUI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sanguosha.content.cards.ids import DODGE_ID, SLASH_ID
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.engine.requests import RequestType
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from sanguosha.ui.interaction import UiMode
from sanguosha.ui.main_window import MainWindow


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    widget = MainWindow(military=False)
    widget.show()
    yield widget
    widget.close()
    app.processEvents()


def slash_preview(window):
    window.start_new_game()
    QApplication.processEvents()
    session = window.session
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_OPTION
    slash_id = next(choice[4:] for choice in request.choices if choice.startswith("use:") and
                    session.state.cards[CardInstanceId(choice[4:])].definition_id == SLASH_ID)
    window._card_clicked(slash_id)
    return session, request, slash_id


def test_slash_waits_for_target_and_confirm(window):
    session, request, slash_id = slash_preview(window)
    assert session.engine.pending_request is request
    assert window.interaction.mode is UiMode.TARGET_SELECTING
    assert window.hand.cards[slash_id]._selected
    assert window.table.panels["p3"].targetable
    confirm = next(b for b in window.decision.buttons if b.text() == "确定")
    assert not confirm.isEnabled()
    window._player_clicked("p3")
    assert session.engine.pending_request is request
    assert window.interaction.mode is UiMode.TARGET_SELECTED_PENDING_CONFIRM
    assert window.table.panels["p3"].selected_target
    assert window.table.panels["p3"].grab().width() > 0
    confirm = next(b for b in window.decision.buttons if b.text() == "确定")
    assert confirm.isEnabled()
    QTest.mouseClick(confirm, Qt.LeftButton)
    assert session.engine.pending_request is not request
    assert CardInstanceId(slash_id) not in session.state.cards_in(ZoneRef(ZoneType.HAND, PlayerId("p1")))


def test_cancel_restores_play_state(window):
    session, request, slash_id = slash_preview(window)
    window._player_clicked("p3")
    cancel = next(b for b in window.decision.buttons if b.text() == "取消")
    QTest.mouseClick(cancel, Qt.LeftButton)
    assert session.engine.pending_request is request
    assert window.interaction.mode is UiMode.IDLE
    assert not window.table.panels["p3"].selected_target
    assert not window.table.panels["p3"].targetable
    assert "结束出牌阶段" in [b.text() for b in window.decision.buttons]


def test_dodge_shows_attack_chain_and_requires_response_confirm(window):
    window.session = GameSession.new_game(6)
    session = window.session
    dodge_id = next(cid for cid in session.state.cards_in(ZoneRef(ZoneType.HAND, PlayerId("p1")))
                    if session.state.cards[cid].definition_id == DODGE_ID)
    slash_id = next(cid for cid, card in session.state.cards.items() if card.definition_id == SLASH_ID)
    session.engine.start_action(SlashEffectAction("t53-attack", PlayerId("p3"), PlayerId("p1"), slash_id, DODGE_ID))
    window._render()
    assert window.table.panels["p3"].attack_role == "attacker"
    assert window.table.panels["p1"].attack_role == "defender"
    assert window.table.resolving_card == "basic.slash"
    assert "玩家3 对你使用了【杀】" in window.decision.prompt_label.text()
    assert window.hand.cards[str(dodge_id)]._selectable
    assert "不出" in [b.text() for b in window.decision.buttons]
    window._card_clicked(str(dodge_id))
    assert dodge_id not in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert window.hand.cards[str(dodge_id)]._selected
    confirm = next(b for b in window.decision.buttons if b.text() == "确认响应")
    assert confirm.isEnabled()
    QTest.mouseClick(confirm, Qt.LeftButton)
    assert dodge_id in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert session.state.players[PlayerId("p1")].hp == 4


def test_dodge_pass_and_offscreen_render(window):
    window.session = GameSession.new_game(6)
    session = window.session
    slash_id = next(cid for cid, card in session.state.cards.items() if card.definition_id == SLASH_ID)
    session.engine.start_action(SlashEffectAction("t53-pass", PlayerId("p3"), PlayerId("p1"), slash_id, DODGE_ID))
    window._render()
    assert not window.grab().isNull()
    button = next(b for b in window.decision.buttons if b.text() == "不出")
    QTest.mouseClick(button, Qt.LeftButton)
    assert session.state.players[PlayerId("p1")].hp == 3

"""Visible Qt entry-point smoke: real clicks, screenshots, then a complete match."""
import os
import sys
import json
import runpy
from dataclasses import replace
from pathlib import Path
os.environ["SANGUOSHA_FAST_AI"] = "1"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from sanguosha.ui.main_window import MainWindow
from sanguosha.engine.requests import RequestType, PASS_RESPONSE
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.content.cards.ids import SLASH_ID, DODGE_ID
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameStatus
from sanguosha.session import GameSession

OUTPUT = Path(__file__).parent
report = {}
original_init = MainWindow.__init__

def click_button(window, label):
    button = next(b for b in window.decision.buttons if b.text() == label)
    assert button.isEnabled(), label
    QTest.mouseClick(button, Qt.LeftButton)

def snapshot(window, name):
    QApplication.processEvents()
    assert window.grab().save(str(OUTPUT / name))

def smoke(window):
    try:
        QTest.mouseClick(window.new_game_button, Qt.LeftButton)
        QTest.qWait(40)
        snapshot(window, "t5_1_smoke.png")
        view = window.table.view
        assert all(p.view for p in window.table.panels.values())
        assert all(p.identity_label == "未知" for p in view.players[1:])
        assert all(not hasattr(p, "hand") for p in view.players[1:])
        report["privacy"] = True
        request = window.session.engine.pending_request
        slash = next(c[4:] for c in request.choices if c.startswith("use:") and window.session.state.cards[CardInstanceId(c[4:])].definition_id == SLASH_ID)
        card = window.hand.cards[slash]
        QTest.mouseMove(card, card.rect().center())
        QTest.qWait(150)
        assert card._hover and card._lift > 0
        QTest.mouseClick(card, Qt.LeftButton)
        QTest.qWait(150)
        assert card._selected
        target = next(iter(window.interaction.legal_targets))
        assert window.table.panels[target].targetable
        QTest.mouseClick(window.table.panels[target], Qt.LeftButton)
        snapshot(window, "t5_1_target.png")
        click_button(window, "取消")
        assert not window.interaction.card_id
        report["hover_selection_target_cancel"] = True
        # A rule action sets up a response; the UI answers it by real mouse clicks.
        window.session = GameSession.new_game(6)
        window._seen_events = 0
        session = window.session
        slash_id = next(cid for cid, c in session.state.cards.items() if c.definition_id == SLASH_ID)
        session.engine.start_action(SlashEffectAction("smoke-response", PlayerId("p3"), PlayerId("p1"), slash_id, DODGE_ID))
        window._render()
        assert window.decision.prompt_label.mode == "response"
        assert any(c._response_candidate for c in window.hand.cards.values())
        snapshot(window, "t5_1_response.png")
        click_button(window, "不出")
        assert window.table.panels["p1"].view.hp == 3
        QTest.qWait(70)
        report["response_damage"] = True
        # Death visual uses a projected snapshot; no direct GameState change.
        projected = replace(window.table.panels["p2"].view, hp=0, alive=False, identity_label="忠臣")
        window.table.panels["p2"].render(projected, False, False)
        QTest.qWait(450)
        assert window.table.panels["p2"].death_opacity == 1
        snapshot(window, "t5_1_death.png")
        report["death_visual"] = True
        window.resize(1280,720)
        QTest.qWait(30)
        snapshot(window, "t5_1_resize.png")
        assert all(window.table.rect().contains(p.geometry()) for p in window.table.panels.values())
        report["resize"] = True
        window.resize(1440,900)
        window.start_new_game()
        QApplication.processEvents()
        steps = 0
        while window.session.state.status is not GameStatus.FINISHED and steps < 10000:
            session = window.session
            request = session.engine.pending_request
            if request and request.player_id == session.human_id:
                value = session.ai.decide(session.state, request).value
                if request.request_type is RequestType.CHOOSE_OPTION and isinstance(value,str) and value.startswith("use:"):
                    window._card_clicked(value[4:])
                    if window.interaction.legal_targets:
                        pid = next(iter(window.interaction.legal_targets))
                        QTest.mouseClick(window.table.panels[pid], Qt.LeftButton)
                        click_button(window, "确定")
                elif request.request_type is RequestType.RESPOND_WITH_CARD and value != PASS_RESPONSE:
                    QTest.mouseClick(window.hand.cards[str(value)], Qt.LeftButton)
                    click_button(window, "确认响应")
                else:
                    window._submit_value(value)
            else:
                window._tick()
            QApplication.processEvents()
            steps += 1
        assert window.session.state.status is GameStatus.FINISHED, steps
        snapshot(window, "t5_1_finished.png")
        report.update(complete_match=True, steps=steps, result=window.session.state.victory.label,
                      platform=QApplication.platformName(), entry_point="python -m sanguosha / runpy")
        print(json.dumps(report, ensure_ascii=False), flush=True)
        (OUTPUT / "t5_1_smoke_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        import traceback
        traceback.print_exc()
        report["failed"] = True
    finally:
        window.close()
        QApplication.instance().exit(1 if report.get("failed") else 0)

def instrument(self):
    original_init(self, military=False)
    QTimer.singleShot(100, lambda: smoke(self))

MainWindow.__init__ = instrument
runpy.run_module("sanguosha", run_name="__main__")

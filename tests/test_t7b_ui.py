"""Offscreen checks for the draft and public general controls."""

from PySide6.QtWidgets import QLabel

from sanguosha.engine.phases import PhaseAction
from sanguosha.model.enums import Identity, Phase
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow


def test_standard_draft_requires_selection_then_confirmation():
    window = MainWindow()
    window.start_standard_game(seed=12)
    dialog = window._pregame_dialog
    dialog._reveal_identity()
    assert dialog.setup.generals == {}
    assert '你的身份' in dialog.title.text()
    dialog._confirm()
    assert len(dialog.cards) == 10
    assert not dialog.confirm_button.isEnabled()
    candidate = dialog.setup.candidates[2]
    dialog.cards[candidate].click()
    assert dialog.selected_id == candidate
    assert dialog.setup.generals == {}
    assert dialog.confirm_button.isEnabled()
    dialog._confirm()
    assert window.session is not None
    assert window.session.state.players[window.session.human_id].character_id == candidate
    window._tick_timer.stop()
    window.close()


def test_ten_seed_offscreen_drafts_build_unique_seated_games():
    for seed in range(1, 11):
        window = MainWindow()
        window.start_standard_game(seed=seed)
        dialog = window._pregame_dialog
        dialog._reveal_identity()
        dialog._confirm()
        dialog.cards[dialog.setup.candidates[0]].click()
        dialog._confirm()
        window._tick_timer.stop()
        window._render()
        assert len({p.character_id for p in window.session.state.players.values()}) == 5
        assert window.table.panels['p1'].view.character_name == window.session.character_names['p1']
        window.close()


def test_general_details_show_skill_status_without_hidden_identity():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players[session.human_id].identity = Identity.REBEL
    session.state.revealed_identities = {'p2'}
    window = MainWindow()
    window.session = session
    window._render()
    window._show_general_detail('p1')
    labels = '\n'.join(label.text() for label in window._detail_dialog.findChildren(QLabel))
    assert '奸雄' in labels and '护驾' in labels
    assert '当前身份下未启用' in labels
    assert '反贼' not in labels
    window._detail_dialog.close()
    window._show_general_detail('p2')
    labels = '\n'.join(label.text() for label in window._detail_dialog.findChildren(QLabel))
    assert '仁德' in labels
    window._detail_dialog.close()
    window.close()


def test_human_skill_chip_is_near_table_and_uses_engine_request():
    session = GameSession.new_game(military=True, five_generals=True)
    session.human_id = 'p2'
    session.state.current_player_id = 'p2'
    session.state.turn_number = 1
    session.engine.start_action(PhaseAction('chip-play', 'p2', Phase.PLAY))
    window = MainWindow()
    window.session = session
    window._render()
    layout = window.centralWidget().layout()
    assert layout.indexOf(window.skill_bar) == layout.indexOf(window.table) + 1
    chip = window.skill_bar.buttons['rende']
    assert chip.isEnabled()
    chip.click()
    assert '仁德' in session.engine.pending_request.prompt
    assert not window.skill_bar.buttons['rende'].isEnabled()
    window.close()

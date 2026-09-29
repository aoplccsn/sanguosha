"""Ten seeded full matches traverse the actual Qt draft and render path."""

from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.ui.main_window import MainWindow


def test_seed_1_to_10_offscreen_gui_matches_finish_without_residue():
    seen_generals = set()
    for seed in range(1, 11):
        window = MainWindow()
        window.start_standard_game(seed=seed)
        dialog = window._pregame_dialog
        dialog._reveal_identity()
        dialog._confirm()
        dialog.cards[dialog.setup.candidates[0]].click()
        dialog._confirm()
        window._tick_timer.stop()
        session = window.session
        seen_generals.update(player.character_id for player in session.state.players.values())
        for step in range(12_000):
            if session.state.status is GameStatus.FINISHED:
                break
            request = session.engine.pending_request
            if request is not None and request.player_id == session.human_id:
                session.submit_human(session.ai.decide(session.state, request))
            elif not session.step_auto():
                break
            if step % 100 == 0:
                window._render()
                window._tick_timer.stop()
        window._render()
        window._tick_timer.stop()
        assert session.state.status is GameStatus.FINISHED, seed
        assert session.engine.pending_request is None and session.engine.stack.is_empty(), seed
        assert not session.state.cards_in(ZoneRef(ZoneType.PROCESSING)), seed
        assert window.table.vfx.director.result is not None, seed
        session.state.__post_init__()
        window.close()
    assert len(seen_generals) >= 15

"""Combat cues are derived from recorded public outcomes, never guessed hits."""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from sanguosha.engine.events import (CardRespondedEvent, CardUsedEvent, DamageDealtEvent,
                                      GameEndedEvent, PlayerDiedEvent, VirtualResponseEvent,
                                      TrickTargetsDeclaredEvent)
from sanguosha.model.enums import Identity
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.ui.card_vfx import CardVfxDirector, VfxCue
from sanguosha.ui.game_table import GameTable


def test_human_decision_and_draft_timeout_share_thirty_seconds():
    from sanguosha.ui.timing import HUMAN_DECISION_TIMEOUT_MS, PREGAME_GENERAL_TIMEOUT_MS
    assert HUMAN_DECISION_TIMEOUT_MS == PREGAME_GENERAL_TIMEOUT_MS == 30_000


def test_selected_human_target_creates_preview_beam():
    from sanguosha.session import GameSession
    from sanguosha.ui.main_window import MainWindow
    window = MainWindow()
    window.session = GameSession.new_game(military=True, five_generals=True)
    card = str(window.session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0])
    window.interaction.select_card(card, {'p2'})
    window.interaction.select_target('p2')
    window._render()
    assert window.table.vfx.preview.targets == ('p2',)
    window.close()


def test_cancelled_human_target_removes_preview_beam():
    from sanguosha.session import GameSession
    from sanguosha.ui.main_window import MainWindow
    window = MainWindow()
    window.session = GameSession.new_game(military=True, five_generals=True)
    window.interaction.select_card('preview-card', {'p2'})
    window.interaction.select_target('p2')
    window._render()
    assert window.table.vfx.preview is not None
    window.interaction.reset()
    window._render()
    assert window.table.vfx.preview is None
    window.close()


def test_plain_slash_only_schedules_attack_before_damage_fact():
    director = CardVfxDirector()
    cues = director.consume(CardUsedEvent('slash', 'p1', 'c1', ('p2',)),
                            definition_id='basic.slash')
    assert [cue.kind for cue in cues] == ['beam', 'slash']
    assert all(cue.kind != 'damage' for cue in cues)


def test_fire_slash_selects_fire_variant():
    cues = CardVfxDirector().consume(CardUsedEvent('fire', 'p1', 'c1', ('p2',)),
                                      definition_id='basic.fire_slash')
    assert cues[-1].kind == 'fire_slash'


def test_thunder_slash_selects_thunder_variant():
    cues = CardVfxDirector().consume(CardUsedEvent('thunder', 'p1', 'c1', ('p2',)),
                                      definition_id='basic.thunder_slash')
    assert cues[-1].kind == 'thunder_slash'


def test_failed_dodge_does_not_create_dodge_cue():
    director = CardVfxDirector()
    director.consume(CardUsedEvent('slash', 'p1', 'c1', ('p2',)), definition_id='basic.slash')
    cues = director.consume(DamageDealtEvent('hit', 'p1', 'p2', 1, 2))
    assert [cue.kind for cue in cues] == ['damage']


def test_recovery_cue_uses_actual_recovered_amount():
    from sanguosha.engine.events import HpRecoveredEvent
    cues = CardVfxDirector().consume(HpRecoveredEvent('heal', 'p1', 'p2', 2, 3))
    assert len(cues) == 1 and cues[0].kind == 'recover' and cues[0].text == '+2'


def test_multiple_kills_advance_titles_and_cap_at_configured_level():
    from sanguosha.ui.card_vfx import KILL_TITLES
    director = CardVfxDirector()
    titles = [director.consume(PlayerDiedEvent(f'kill-{i}', f'victim-{i}', Identity.REBEL, 'p1'))[-1].text
              for i in range(len(KILL_TITLES) + 1)]
    assert all(title in text for title, text in zip(KILL_TITLES, titles))
    assert KILL_TITLES[-1] in titles[-1]
    assert director.kill_counts['p1'] == len(KILL_TITLES) + 1


def test_environmental_and_self_death_never_credit_a_killer():
    director = CardVfxDirector()
    assert [cue.kind for cue in director.consume(PlayerDiedEvent('env', 'p2', Identity.REBEL, None))] == ['death']
    assert [cue.kind for cue in director.consume(PlayerDiedEvent('self', 'p3', Identity.REBEL, 'p3'))] == ['death']
    assert director.kill_counts == {}


def test_test_mode_shortens_animation_without_changing_cue_timing(monkeypatch):
    from sanguosha.ui.timing import TARGET_BEAM_MS, vfx_duration
    monkeypatch.setenv('VFX_TEST_MODE', '1')
    assert vfx_duration(TARGET_BEAM_MS) == 1
    assert VfxCue('beam', duration_ms=TARGET_BEAM_MS).duration_ms == TARGET_BEAM_MS


def test_multi_target_beam_and_slash_variant():
    director = CardVfxDirector()
    cues = director.consume(CardUsedEvent('used', 'p1', 'c1', ('p2', 'p3')),
                            definition_id='basic.fire_slash')
    assert [cue.kind for cue in cues] == ['beam', 'fire_slash']
    assert all(cue.targets == ('p2', 'p3') for cue in cues)


def test_global_trick_declares_actual_targets_for_multiple_beams():
    from sanguosha.engine.card_use import UseCardAction
    from sanguosha.model.enums import Phase
    from sanguosha.model.usage import PlayUsageState
    from sanguosha.session import GameSession
    from test_t6_military_basics import put
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    card = put(session, 'trick.archery_attack', 'p1')
    session.engine.start_action(UseCardAction('global-trick', 'p1', card))
    event = next(event for event in session.events.events
                 if isinstance(event, TrickTargetsDeclaredEvent))
    assert event.target_ids == ('p2', 'p3', 'p4', 'p5')
    cue = CardVfxDirector().consume(event)
    assert len(cue) == 1 and cue[0].kind == 'beam'
    assert cue[0].targets == event.target_ids


def test_successful_dodge_does_not_invent_damage():
    director = CardVfxDirector()
    cues = director.consume(CardRespondedEvent('response', 'p2', 'c2', 'slash'),
                            definition_id='basic.dodge')
    assert [cue.kind for cue in cues] == ['dodge']
    assert director.consume(CardRespondedEvent('other', 'p2', 'c3', 'slash'),
                            definition_id='basic.slash') == ()


def test_armor_virtual_dodge_and_second_wushuang_dodge_have_distinct_cues():
    director = CardVfxDirector()
    first = director.consume(VirtualResponseEvent('armor', 'p2', 'slash', 'basic.dodge', 1, 2),
                             definition_id='basic.dodge')
    second = director.consume(CardRespondedEvent('second', 'p2', 'c2', 'slash', 'basic.dodge', 2, 2),
                              definition_id='basic.dodge')
    assert first[0].kind == second[0].kind == 'dodge'
    assert first[0].text == '第1张闪'
    assert second[0].text == '第2张闪'


def test_hit_is_only_from_actual_damage_event():
    director = CardVfxDirector()
    assert director.consume(CardUsedEvent('used', 'p1', 'c1', ('p2',)),
                            definition_id='basic.slash')[-1].kind == 'slash'
    assert director.consume(DamageDealtEvent('hit', 'p1', 'p2', 2, 1))[0].text == '−2'
    assert director.consume(DamageDealtEvent('zero', 'p1', 'p2', 0, 1)) == ()


def test_kill_attribution_comes_from_death_record():
    director = CardVfxDirector()
    cues = director.consume(PlayerDiedEvent('death', 'p2', Identity.REBEL, 'p3'),
                            names={'p3': '刘备'})
    assert [cue.kind for cue in cues] == ['death', 'kill']
    assert '刘备' in cues[1].text
    assert director.kill_counts == {'p3': 1}
    director.consume(PlayerDiedEvent('self', 'p3', Identity.LOYALIST, 'p3'))
    director.consume(PlayerDiedEvent('unowned', 'p4', Identity.REBEL, None))
    assert director.kill_counts == {'p3': 1}


def test_result_uses_formal_winners_and_reset():
    director = CardVfxDirector()
    assert director.consume(GameEndedEvent('end', '主公阵营获胜', ('p1', 'p3')),
                            human_id='p1')[0].text.startswith('胜利')
    director.reset()
    assert director.result is None and not director.kill_counts
    assert director.consume(GameEndedEvent('end2', '反贼获胜', ('p2',)),
                            human_id='p1')[0].text.startswith('失败')


def test_result_overlay_contains_identity_survivors_and_formal_reason():
    cue = CardVfxDirector().consume(GameEndedEvent('end', '反贼胜利', ('p1', 'p2')),
                                    human_id='p1', identity_label='反贼',
                                    survivor_names=('你', '玩家3'), reason='主公死亡')[0]
    assert cue.text.splitlines() == ['胜利', '身份：反贼', '反贼胜利', '存活：你、玩家3', '主公死亡']


def test_result_presentation_does_not_mutate_formal_winner_state():
    from sanguosha.model.victory import VictoryResult
    from sanguosha.session import GameSession
    session = GameSession.new_game(military=True, five_generals=True)
    result = VictoryResult('反贼胜利', ('p2', 'p3'), '主公死亡')
    session.state.victory = result
    cue = CardVfxDirector().consume(GameEndedEvent('end', result.label, result.winner_ids),
                                    human_id='p1')[0]
    assert cue.text.startswith('失败')
    assert session.state.victory is result


def test_installing_new_game_clears_kills_result_and_pending_animation():
    from sanguosha.session import GameSession
    from sanguosha.ui.main_window import MainWindow
    window = MainWindow()
    window._install_session(GameSession.new_game(military=True, five_generals=True))
    window._tick_timer.stop()
    layer = window.table.vfx
    layer.consume(PlayerDiedEvent('death', 'p2', Identity.REBEL, 'p1'))
    layer.consume(GameEndedEvent('end', '反贼胜利', ('p1',)), human_id='p1')
    assert layer.director.kill_counts and layer.director.result is not None
    window._install_session(GameSession.new_game(military=True, five_generals=True))
    window._tick_timer.stop()
    assert layer.director.kill_counts == {}
    assert layer.director.result is None and layer.current is None and not layer._queue
    window.close()


def test_overlay_is_mouse_transparent_and_preview_cancels():
    app = QApplication.instance() or QApplication([])
    table = GameTable()
    table.resize(1200, 700)
    layer = table.vfx
    assert layer.testAttribute(Qt.WA_TransparentForMouseEvents)
    layer.set_preview('p1', ('p2', 'p3'))
    assert layer.preview.targets == ('p2', 'p3')
    layer.set_preview(None, ())
    assert layer.preview is None
    table.close()


def test_beam_anchors_at_panel_edges_and_renders_arrow():
    app = QApplication.instance() or QApplication([])
    table = GameTable()
    table.resize(1200, 700)
    table.show()
    app.processEvents()
    layer = table.vfx
    geometry = layer._beam_geometry('p1', 'p2')
    assert geometry is not None
    start, end, _, _ = geometry
    assert start != layer._point('p1') and end != layer._point('p2')
    layer.set_preview('p1', ('p2', 'p3'))
    image = layer.grab().toImage()
    assert not image.isNull()
    table.close()

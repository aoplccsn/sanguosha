"""Combat cues are derived from recorded public outcomes, never guessed hits."""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from sanguosha.engine.events import (CardRespondedEvent, CardUsedEvent, DamageDealtEvent,
                                      GameEndedEvent, PlayerDiedEvent, VirtualResponseEvent,
                                      TrickTargetsDeclaredEvent)
from sanguosha.model.enums import Identity
from sanguosha.ui.card_vfx import CardVfxDirector
from sanguosha.ui.game_table import GameTable


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
    first = director.consume(VirtualResponseEvent('armor', 'p2', 'slash', 'basic.dodge'),
                             definition_id='basic.dodge')
    second = director.consume(CardRespondedEvent('second', 'p2', 'c2', 'slash', 'basic.dodge', 2),
                              definition_id='basic.dodge')
    assert first[0].kind == second[0].kind == 'dodge'
    assert first[0].text == '闪避'
    assert second[0].text == '第二张闪'


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

"""Capture eight staged public-event VFX states from the production Qt widgets."""

import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('VFX_TEST_MODE', '1')

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from sanguosha.engine.events import CardRespondedEvent, CardUsedEvent, PlayerDiedEvent
from sanguosha.model.enums import Identity
from sanguosha.model.state import GameStatus
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession
from sanguosha.ui.main_window import MainWindow


OUTPUT = Path(__file__).resolve().parent / 't7_vfx_screenshots'


def main():
    app = QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
    app.setFont(QFont('Microsoft YaHei UI', 10))
    setup = Pregame.create(12)
    setup.acknowledge_identity()
    setup.timeout()
    session = GameSession.new_game(military=True, setup=setup)
    window = MainWindow()
    window._install_session(session)
    window._tick_timer.stop()
    window.resize(1440, 900)
    window.show()
    app.processEvents()
    OUTPUT.mkdir(exist_ok=True)
    layer = window.table.vfx

    def save(name, cues=(), result=False):
        layer.animation.stop()
        layer.current = None if result else cues[-1] if cues else None
        layer.progress = .48
        layer.update()
        app.processEvents()
        assert window.grab().save(str(OUTPUT / name))

    layer.reset()
    layer.set_preview('p1', ('p2',))
    save('target_beam.png')
    layer.set_preview(None, ())

    for filename, definition in (('slash_vfx.png', 'basic.slash'),
                                 ('fire_slash_vfx.png', 'basic.fire_slash'),
                                 ('thunder_slash_vfx.png', 'basic.thunder_slash')):
        layer.reset()
        cues = layer.director.consume(CardUsedEvent(filename, 'p1', 'visual-card', ('p2',)),
                                      definition_id=definition)
        save(filename, cues)

    layer.reset()
    save('dodge_vfx.png', layer.director.consume(
        CardRespondedEvent('dodge', 'p2', 'visual-card', 'slash', 'basic.dodge'),
        definition_id='basic.dodge'))

    layer.reset()
    save('kill_announcement.png', layer.director.consume(
        PlayerDiedEvent('kill', 'p2', Identity.REBEL, 'p1'), names={'p1': '你'}))

    window.close()

    def capture_finished_match(seed, filename):
        match_setup = Pregame.create(seed)
        match_setup.acknowledge_identity()
        match_setup.timeout()
        match = GameSession.new_game(military=True, setup=match_setup)
        for _ in range(12_000):
            if match.state.status is GameStatus.FINISHED:
                break
            request = match.engine.pending_request
            if request is not None and request.player_id == match.human_id:
                match.submit_human(match.ai.decide(match.state, request))
            elif not match.step_auto():
                break
        assert match.state.status is GameStatus.FINISHED
        finished = MainWindow()
        finished._install_session(match)
        finished._tick_timer.stop()
        finished.resize(1440, 900)
        finished.show()
        effect = finished.table.vfx
        effect.animation.stop()
        effect.current = None
        effect._queue.clear()
        effect.update()
        app.processEvents()
        assert effect.director.result is not None
        assert finished.grab().save(str(OUTPUT / filename))
        finished.close()

    capture_finished_match(3, 'victory_overlay.png')
    capture_finished_match(1, 'defeat_overlay.png')
    print(f'Captured 8 VFX screenshots in {OUTPUT}')


if __name__ == '__main__':
    main()

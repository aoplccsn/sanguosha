"""Public-event driven combat presentation; no game rules live here."""

from dataclasses import dataclass

from PySide6.QtCore import Qt, QPointF, QRectF, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sanguosha.engine.events import (CardRespondedEvent, CardUsedEvent, DamageDealtEvent,
                                      GameEndedEvent, HpRecoveredEvent, PlayerDiedEvent,
                                      VirtualResponseEvent)
from .theme import Theme
from .timing import (DAMAGE_FEEDBACK_MS, DEATH_VFX_MS, DODGE_VFX_MS,
                     GAME_RESULT_FADE_MS, KILL_ANNOUNCEMENT_MS, SLASH_VFX_MS,
                     TARGET_BEAM_MS, vfx_duration)


KILL_TITLES = ('一破 · 卧龙出山', '二连破 · 乘胜追击', '三连破 · 威震三军',
               '四连破 · 横扫千军', '五连破 · 天下无双')


@dataclass(frozen=True)
class VfxCue:
    kind: str
    source: str | None = None
    targets: tuple[str, ...] = ()
    text: str = ''
    duration_ms: int = 0


class CardVfxDirector:
    """Translate public facts into cues without inferring combat outcomes."""

    def __init__(self):
        self.kill_counts: dict[str, int] = {}
        self.result: VfxCue | None = None

    def reset(self):
        self.kill_counts.clear()
        self.result = None

    def consume(self, event, *, definition_id: str = '', human_id: str = '', names=None):
        names = names or {}
        if isinstance(event, CardUsedEvent):
            source, targets = str(event.player_id), tuple(map(str, event.target_ids))
            if not targets:
                return ()
            kind = ('fire_slash' if definition_id == 'basic.fire_slash' else
                    'thunder_slash' if definition_id == 'basic.thunder_slash' else
                    'slash' if definition_id == 'basic.slash' else 'target')
            return (VfxCue('beam', source, targets, duration_ms=TARGET_BEAM_MS),
                    VfxCue(kind, source, targets, duration_ms=SLASH_VFX_MS)) if kind != 'target' else (
                        VfxCue('beam', source, targets, duration_ms=TARGET_BEAM_MS),)
        if isinstance(event, (CardRespondedEvent, VirtualResponseEvent)) and definition_id == 'basic.dodge':
            return (VfxCue('dodge', str(event.player_id), (str(event.player_id),),
                           '第二张闪' if event.response_number == 2 else '闪避',
                           duration_ms=DODGE_VFX_MS),)
        if isinstance(event, DamageDealtEvent) and event.amount > 0:
            return (VfxCue('damage', str(event.source_id) if event.source_id else None,
                           (str(event.target_id),), f'−{event.amount}', DAMAGE_FEEDBACK_MS),)
        if isinstance(event, HpRecoveredEvent) and event.amount > 0:
            return (VfxCue('recover', str(event.source_id) if event.source_id else None,
                           (str(event.target_id),), f'+{event.amount}', DAMAGE_FEEDBACK_MS),)
        if isinstance(event, PlayerDiedEvent):
            victim = str(event.player_id)
            cues = [VfxCue('death', None, (victim,), '阵亡', DEATH_VFX_MS)]
            killer = str(event.killer_id) if event.killer_id else None
            if killer and killer != victim:
                count = self.kill_counts.get(killer, 0) + 1
                self.kill_counts[killer] = count
                title = KILL_TITLES[min(count, len(KILL_TITLES)) - 1]
                cues.append(VfxCue('kill', killer, (victim,),
                                   f'{names.get(killer, killer)}  {title}', KILL_ANNOUNCEMENT_MS))
            return tuple(cues)
        if isinstance(event, GameEndedEvent):
            outcome = '胜利' if human_id in tuple(map(str, event.winner_ids)) else '失败'
            self.result = VfxCue('result', None, tuple(map(str, event.winner_ids)),
                                 f'{outcome} · {event.label}', GAME_RESULT_FADE_MS)
            return (self.result,)
        return ()


class CardVfxLayer(QWidget):
    """Mouse-transparent overlay above the table and player panels."""

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.director = CardVfxDirector()
        self.preview: VfxCue | None = None
        self.current: VfxCue | None = None
        self.history: list[VfxCue] = []
        self._queue: list[VfxCue] = []
        self.progress = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.valueChanged.connect(self._frame)
        self.animation.finished.connect(self._next)

    def reset(self):
        self.animation.stop()
        self.director.reset()
        self.preview = self.current = None
        self.history.clear()
        self._queue.clear()
        self.progress = 0.0
        self.update()

    def set_preview(self, source: str | None, targets, semantic: str = 'attack'):
        cue = VfxCue(f'preview_{semantic}', source, tuple(sorted(map(str, targets)))) if source and targets else None
        if cue != self.preview:
            self.preview = cue
            self.update()

    def consume(self, event, **context):
        cues = self.director.consume(event, **context)
        self.history.extend(cues)
        self._queue.extend(cue for cue in cues if cue.kind != 'result')
        if self.current is None:
            self._next()
        self.update()
        return cues

    def _frame(self, value):
        self.progress = float(value)
        self.update()

    def _next(self):
        self.current = self._queue.pop(0) if self._queue else None
        if self.current:
            self.progress = 0.0
            self.animation.setDuration(vfx_duration(self.current.duration_ms))
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()
        self.update()

    def _point(self, player_id: str | None):
        panel = self.table.panels.get(player_id)
        return QPointF(panel.geometry().center()) if panel else None

    def _beam(self, p, cue, alpha):
        source = self._point(cue.source)
        if source is None:
            return
        colors = {'preview_attack': Theme.slash, 'preview_control': '#8e68ad',
                  'preview_protect': Theme.dodge, 'beam': Theme.accent}
        color = QColor(colors.get(cue.kind, Theme.accent))
        color.setAlpha(alpha)
        p.setPen(QPen(color, 3 if cue.kind == 'beam' else 2, Qt.SolidLine if cue.kind == 'beam' else Qt.DashLine))
        for target_id in cue.targets:
            target = self._point(target_id)
            if target:
                p.drawLine(source, target)
                p.setBrush(color)
                p.drawEllipse(target, 5, 5)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.preview:
            self._beam(p, self.preview, 145)
        cue = self.current
        if cue:
            if cue.kind == 'beam':
                self._beam(p, cue, int(210 * (1 - self.progress * .6)))
            elif cue.kind in ('slash', 'fire_slash', 'thunder_slash'):
                colors = {'slash': Theme.slash, 'fire_slash': '#e86a32', 'thunder_slash': '#6ca8df'}
                color = QColor(colors[cue.kind]); color.setAlpha(int(220 * (1-self.progress*.55)))
                p.setPen(QPen(color, 5))
                for target_id in cue.targets:
                    target = self._point(target_id)
                    if target:
                        radius = 12 + 36*self.progress
                        p.drawArc(QRectF(target.x()-radius, target.y()-radius,
                                         radius*2, radius*2), 20*16, 135*16)
                        if cue.kind == 'thunder_slash':
                            p.drawLine(target + QPointF(-radius, -radius), target + QPointF(0, 0))
                            p.drawLine(target, target + QPointF(radius*.5, radius))
            elif cue.kind in ('dodge', 'damage', 'recover', 'death'):
                target = self._point(cue.targets[0])
                if target:
                    color = {'dodge': Theme.dodge, 'damage': Theme.slash,
                             'recover': Theme.dodge, 'death': '#685467'}[cue.kind]
                    p.setPen(QPen(QColor(color), 4))
                    radius = 18 + self.progress*42
                    p.drawEllipse(target, radius, radius)
                    p.setFont(QFont('Microsoft YaHei UI', 17, QFont.Bold))
                    label = cue.text or ('闪避' if cue.kind == 'dodge' else '')
                    p.drawText(QRectF(target.x()-80, target.y()-radius-40, 160, 34), Qt.AlignCenter, label)
            elif cue.kind == 'kill':
                rect = QRectF(self.width()*.2, self.height()*.39, self.width()*.6, 66)
                p.setPen(QPen(QColor(Theme.accent), 2))
                p.setBrush(QColor(30, 20, 20, 210))
                p.drawRoundedRect(rect, 13, 13)
                p.setFont(QFont('Microsoft YaHei UI', 21, QFont.Bold))
                p.drawText(rect, Qt.AlignCenter, cue.text)
        if self.director.result:
            rect = QRectF(self.width()*.18, self.height()*.26, self.width()*.64, self.height()*.40)
            p.setPen(QPen(QColor(Theme.accent), 3))
            p.setBrush(QColor(29, 22, 22, 225))
            p.drawRoundedRect(rect, 18, 18)
            p.setFont(QFont('Microsoft YaHei UI', 30, QFont.Bold))
            p.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, self.director.result.text)

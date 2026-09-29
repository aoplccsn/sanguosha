"""Public-event driven combat presentation; no game rules live here."""

from dataclasses import dataclass
from math import hypot

from PySide6.QtCore import Qt, QPointF, QRectF, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from sanguosha.engine.events import (CardRespondedEvent, CardUsedEvent, DamageDealtEvent,
                                      GameEndedEvent, HpRecoveredEvent, PlayerDiedEvent,
                                      VirtualResponseEvent, TrickTargetsDeclaredEvent)
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

    def consume(self, event, *, definition_id: str = '', human_id: str = '', names=None,
                identity_label: str = '', survivor_names=(), reason: str = ''):
        names = names or {}
        if isinstance(event, TrickTargetsDeclaredEvent):
            return (VfxCue('beam', str(event.player_id), tuple(map(str, event.target_ids)),
                           duration_ms=TARGET_BEAM_MS),)
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
            label = (f'第{event.response_number}张闪' if event.response_total > 1 else '闪避')
            return (VfxCue('dodge', str(event.player_id), (str(event.player_id),),
                           label,
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
            details = [f'身份：{identity_label}' if identity_label else '', event.label,
                       '存活：' + '、'.join(survivor_names) if survivor_names else '',
                       reason]
            self.result = VfxCue('result', None, tuple(map(str, event.winner_ids)),
                                 '\n'.join([outcome, *(detail for detail in details if detail)]),
                                 GAME_RESULT_FADE_MS)
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

    def _beam_geometry(self, source_id, target_id, index=0, count=1):
        source_panel = self.table.panels.get(source_id)
        target_panel = self.table.panels.get(target_id)
        if source_panel is None or target_panel is None:
            return None
        source = QPointF(source_panel.geometry().center())
        target = QPointF(target_panel.geometry().center())
        dx, dy = target.x() - source.x(), target.y() - source.y()
        length = hypot(dx, dy)
        if length < 1:
            return None
        ux, uy = dx / length, dy / length
        offset = (index - (count - 1) / 2) * 7
        lateral = QPointF(-uy * offset, ux * offset)
        source_radius = min(source_panel.width(), source_panel.height()) * .38
        target_radius = min(target_panel.width(), target_panel.height()) * .38
        start = source + QPointF(ux * source_radius, uy * source_radius) + lateral
        end = target - QPointF(ux * target_radius, uy * target_radius) + lateral
        return start, end, ux, uy

    def _beam(self, p, cue, alpha):
        source = self._point(cue.source)
        if source is None:
            return
        colors = {'preview_attack': Theme.slash, 'preview_control': '#8e68ad',
                  'preview_protect': Theme.dodge, 'beam': Theme.accent}
        color = QColor(colors.get(cue.kind, Theme.accent))
        color.setAlpha(alpha)
        p.setPen(QPen(color, 3 if cue.kind == 'beam' else 2, Qt.SolidLine if cue.kind == 'beam' else Qt.DashLine))
        for index, target_id in enumerate(cue.targets):
            geometry = self._beam_geometry(cue.source, target_id, index, len(cue.targets))
            if geometry:
                start, end, ux, uy = geometry
                p.drawLine(start, end)
                p.setBrush(color)
                p.drawPolygon(QPolygonF((end, end - QPointF(ux * 13, uy * 13)
                                          + QPointF(-uy * 5, ux * 5),
                                        end - QPointF(ux * 13, uy * 13)
                                          - QPointF(-uy * 5, ux * 5))))
                if cue.kind == 'beam':
                    flow = start + (end - start) * self.progress
                    p.drawEllipse(flow, 4, 4)

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
                for target_id in cue.targets:
                    target = self._point(target_id)
                    if target:
                        radius = 34 + 35*self.progress
                        p.setPen(QPen(color, 8, Qt.SolidLine, Qt.RoundCap))
                        p.drawLine(target + QPointF(-radius*.7, radius*.55),
                                   target + QPointF(radius*.7, -radius*.55))
                        highlight = QColor('#f6e5bf' if cue.kind != 'thunder_slash' else '#d8e9ff')
                        highlight.setAlpha(int(190 * (1-self.progress*.6)))
                        p.setPen(QPen(highlight, 2, Qt.SolidLine, Qt.RoundCap))
                        p.drawLine(target + QPointF(-radius*.7, radius*.55-5),
                                   target + QPointF(radius*.7, -radius*.55-5))
                        p.setPen(QPen(color, 4))
                        p.drawArc(QRectF(target.x()-radius, target.y()-radius,
                                         radius*2, radius*2), 20*16, 135*16)
                        if cue.kind == 'fire_slash':
                            p.drawArc(QRectF(target.x()-radius*.65, target.y()-radius*.65,
                                             radius*1.3, radius*1.3), 195*16, 105*16)
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
                p.setPen(QPen(QColor('#a54936'), 2))
                p.setBrush(QColor(128, 42, 32, 210))
                seal = QRectF(rect.right()-52, rect.top()+10, 42, 42)
                p.drawRect(seal)
                p.setFont(QFont('Microsoft YaHei UI', 15, QFont.Bold))
                p.drawText(seal, Qt.AlignCenter, '破')
                p.setPen(QPen(QColor(Theme.accent), 2))
                p.setFont(QFont('Microsoft YaHei UI', 21, QFont.Bold))
                p.drawText(QRectF(rect.left()+20, rect.top(), rect.width()-80, rect.height()),
                           Qt.AlignCenter, cue.text)
        if self.director.result:
            rect = QRectF(self.width()*.18, self.height()*.26, self.width()*.64, self.height()*.40)
            p.setPen(QPen(QColor(Theme.accent), 3))
            p.setBrush(QColor(29, 22, 22, 225))
            p.drawRoundedRect(rect, 18, 18)
            lines = self.director.result.text.splitlines()
            p.setFont(QFont('Microsoft YaHei UI', 34, QFont.Bold))
            p.drawText(QRectF(rect.left(), rect.top() + 20, rect.width(), 70), Qt.AlignCenter, lines[0])
            p.setFont(QFont('Microsoft YaHei UI', 16))
            p.drawText(QRectF(rect.left() + 24, rect.top() + 105, rect.width() - 48,
                              rect.height() - 120), Qt.AlignCenter | Qt.TextWordWrap,
                       '\n'.join(lines[1:]))

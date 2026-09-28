"""Illustrated seat plaque; all data comes from the public PlayerView."""
from PySide6.QtCore import Qt, QRectF, Signal, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton
from sanguosha.projection import PlayerView
from .resources import RESOURCES
from .theme import Theme


class PlayerPanel(QPushButton):
    player_selected = Signal(str)

    def __init__(self, player_id: str) -> None:
        super().__init__()
        self.player_id = player_id
        self.view: PlayerView | None = None
        self.targetable = self.selected_target = False
        self.attack_role: str | None = None
        self.damage_flash = self.death_opacity = self.turn_glow = 0.0
        self._damage_animation = self._animation("damage_flash", 380)
        self._death_animation = self._animation("death_opacity", 420)
        self._turn_animation = self._animation("turn_glow", 280)
        self.setObjectName(f"player-{player_id}")
        self.setMinimumSize(205, 145)
        self.clicked.connect(lambda: self.player_selected.emit(self.player_id))

    def _animation(self, attribute, duration):
        animation = QVariantAnimation(self)
        animation.setDuration(duration)
        animation.valueChanged.connect(lambda value: (setattr(self, attribute, float(value)), self.update()))
        return animation

    def _start_animation(self, animation, start, end):
        animation.stop()
        animation.setStartValue(float(start))
        animation.setEndValue(float(end))
        animation.start()

    def render(self, view: PlayerView, targetable: bool, choosing_target: bool,
               selected_target: bool = False, attacker: bool = False, defender: bool = False) -> None:
        old = self.view
        if old and view.hp < old.hp:
            self._start_animation(self._damage_animation, 1, 0)
        if old and old.alive and not view.alive:
            self._start_animation(self._death_animation, 0, 1)
        elif old is None or not old.alive and view.alive:
            self._death_animation.stop()
            self.death_opacity = 0 if view.alive else 1
        if old is None or old.active != view.active:
            self._start_animation(self._turn_animation, self.turn_glow, 1 if view.active else 0)
        self.view = view
        self.targetable = targetable
        self.selected_target = selected_target
        self.attack_role = "attacker" if attacker else "defender" if defender else None
        status = "阵亡" if not view.alive else "当前回合" if view.active else "存活"
        self.setText(f"{view.name} · {view.character_name} {view.identity_label} {status} 手牌 {view.hand_count}")
        self.setToolTip("装备：" + ("、".join(c.name for c in view.equipment) or "无") +
                        "\n判定：" + ("、".join(c.name for c in view.judgments) or "无"))
        self.setEnabled(not choosing_target or targetable)
        self.setCursor(Qt.PointingHandCursor if targetable else Qt.ArrowCursor)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        outer = QRectF(3, 3, w-6, h-6)
        edge = QColor(Theme.selected if self.selected_target else
                      "#e0bc69" if self.targetable else
                      "#b35a43" if self.attack_role == "attacker" else
                      "#668a98" if self.attack_role == "defender" else
                      Theme.accent if self.view and self.view.active else "#8b7053")
        if self.selected_target or self.targetable or self.attack_role or self.turn_glow:
            halo = QColor(edge)
            halo.setAlpha(110 if self.selected_target else 45 + int(35*self.turn_glow))
            p.setPen(QPen(halo, 6))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(outer, 8, 8)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor("#ede0c4"))
        grad.setColorAt(1, QColor("#b9a384"))
        p.setBrush(grad)
        p.setPen(QPen(edge, 4 if self.selected_target else 2))
        p.drawRoundedRect(outer, 7, 7)
        p.setPen(QPen(QColor("#5c402b"), 1))
        p.drawRoundedRect(outer.adjusted(5, 5, -5, -5), 4, 4)
        if not self.view:
            return
        v = self.view
        portrait_width = int(w*.53)
        art = QRectF(9, 9, portrait_width-8, h-18)
        clip = QPainterPath()
        clip.addRoundedRect(art, 3, 3)
        p.setClipPath(clip)
        p.drawPixmap(art.toRect(), RESOURCES.general_portrait(v.character_id, v.character_name))
        if not v.alive:
            p.fillRect(art, QColor(24, 21, 19, int(185*self.death_opacity)))
        p.setClipping(False)
        p.setPen(QPen(QColor("#795d3c"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(art, 3, 3)
        x = portrait_width + 6
        rw = w-x-11
        p.setPen(QColor("#2e2821"))
        p.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        p.drawText(QRectF(x, 12, rw-25, 23), Qt.AlignLeft, v.character_name)
        p.drawPixmap(w-34, 9, 25, 25, RESOURCES.identity_icon(v.identity_label))
        p.setPen(QColor("#f6e8c8"))
        p.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        seal = {"主公":"主", "忠臣":"忠", "反贼":"反", "内奸":"内", "未知":"?"}.get(v.identity_label, "?")
        p.drawText(QRectF(w-34, 9, 25, 25), Qt.AlignCenter, seal)
        faction_color = {"魏":"#435a73", "蜀":"#765438", "吴":"#55725f", "群":"#685b67"}.get(v.faction, "#685b67")
        p.setBrush(QColor(faction_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(x, 37, 26, 20), 3, 3)
        p.setPen(QColor("#f8edda"))
        p.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        p.drawText(QRectF(x, 37, 26, 20), Qt.AlignCenter, v.faction)
        p.setPen(QColor("#4b3c2c"))
        p.drawText(QRectF(x+30, 37, rw-30, 20), Qt.AlignLeft, v.name)
        bead_step = min(19, max(12, (rw-8)//max(1, v.max_hp)))
        for i in range(v.max_hp):
            cx = x+7+i*bead_step
            bead = QLinearGradient(cx-6, 61, cx+6, 74)
            bead.setColorAt(0, QColor("#e4a97a" if i < v.hp else "#aaa18f"))
            bead.setColorAt(1, QColor("#9c3d37" if i < v.hp else "#665b50"))
            p.setBrush(bead)
            p.setPen(QPen(QColor("#efcf91" if i < v.hp else "#81715d"), 1))
            p.drawEllipse(QRectF(cx-6, 61, 13, 13))
        p.setPen(QColor("#493b2d"))
        p.setFont(QFont("Microsoft YaHei UI", 8))
        p.drawText(QRectF(x, 78, rw, 17), Qt.AlignLeft, f"手牌 {v.hand_count}   体力 {v.hp}/{v.max_hp}")
        equipment = {"武":None, "甲":None, "+马":None, "-马":None}
        for card in v.equipment:
            slot = {"weapon":"武", "armor":"甲", "defensive_horse":"+马", "offensive_horse":"-马"}.get(card.equipment_slot)
            if slot is None:
                continue
            equipment[slot] = card
        cell = rw/4
        for i, (slot, card) in enumerate(equipment.items()):
            box = QRectF(x+i*cell, 98, cell-2, 21)
            p.setBrush(QColor("#e2d0ab" if card else "#b3a084"))
            p.setPen(QPen(QColor("#8a6c48"), 1))
            p.drawRoundedRect(box, 2, 2)
            p.setPen(QColor("#3b3027" if card else "#756653"))
            p.setFont(QFont("Microsoft YaHei UI", 7, QFont.Bold if card else QFont.Normal))
            p.drawText(box, Qt.AlignCenter, card.name[:3] if card else slot)
        p.setPen(QColor("#624b34"))
        p.setFont(QFont("Microsoft YaHei UI", 8))
        judgments = "  ".join("【"+c.name+"】" for c in v.judgments) or "判定 · 无"
        p.drawText(QRectF(x, 121, rw, 18), Qt.AlignLeft, judgments)
        p.setFont(QFont("Microsoft YaHei UI", 8, QFont.Bold))
        p.setPen(QColor("#8b3f31" if v.chained else "#756653"))
        p.drawText(QRectF(x, h-25, rw, 17), Qt.AlignRight, "⛓ 连环" if v.chained else "当前回合" if v.active else "")
        if v.active:
            p.setPen(QPen(QColor("#b88d43"), 3))
            p.drawLine(10, h-8, w-10, h-8)
        if self.attack_role:
            p.setBrush(QColor("#913f31" if self.attack_role == "attacker" else "#456d7a"))
            p.setPen(QColor("#f6e6c4"))
            badge = QRectF(13, 14, 39, 19)
            p.drawRoundedRect(badge, 3, 3)
            p.drawText(badge, Qt.AlignCenter, "出杀" if self.attack_role == "attacker" else "受击")
        if self.damage_flash:
            p.fillRect(outer, QColor(180, 43, 33, int(125*self.damage_flash)))
        if not v.alive:
            p.setPen(QColor("#a23831"))
            p.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
            p.drawText(art, Qt.AlignCenter, "阵亡")

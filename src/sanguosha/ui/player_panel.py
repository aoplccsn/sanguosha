"""Illustrated, clickable general plaque."""
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
        self.damage_flash = 0.0
        self.death_opacity = 0.0
        self.turn_glow = 0.0
        self._damage_animation = self._animation("damage_flash", 380)
        self._death_animation = self._animation("death_opacity", 420)
        self._turn_animation = self._animation("turn_glow", 220)
        self.targetable = False
        self.selected_target = False
        self.attack_role: str | None = None
        self.setObjectName(f"player-{player_id}")
        self.setMinimumSize(205, 136)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: self.player_selected.emit(self.player_id))

    def _animation(self, attribute, duration):
        animation = QVariantAnimation(self)
        animation.setDuration(duration)
        def update(value):
            setattr(self, attribute, float(value))
            self.update()
        animation.valueChanged.connect(update)
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
        elif old is None or (old and not old.alive and view.alive):
            self._death_animation.stop()
            self.death_opacity = 0 if view.alive else 1
        if old is None or old.active != view.active:
            self._start_animation(self._turn_animation, self.turn_glow, 1 if view.active else 0)
        self.view = view
        self.setToolTip('装备：'+('、'.join(c.name for c in view.equipment) or '无')+'\n判定：'+('、'.join(c.name for c in view.judgments) or '无'))
        self.targetable = targetable
        self.selected_target = selected_target
        self.attack_role = "attacker" if attacker else "defender" if defender else None
        status = "阵亡" if not view.alive else "当前回合" if view.active else "存活"
        self.setText(f"{view.name} · {view.character_name}  {view.identity_label}  {status}  手牌 {view.hand_count}")
        self.setEnabled(not choosing_target or targetable)
        self.setCursor(Qt.PointingHandCursor if targetable else Qt.ArrowCursor)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(3, 3, -3, -3)
        edge = QColor(Theme.shade_fff3b7 if self.selected_target else Theme.shade_ffdf8a if self.targetable and self.underMouse()
                      else Theme.shade_eab465 if self.attack_role == "attacker"
                      else Theme.shade_76d4d4 if self.attack_role == "defender" else Theme.shade_e3bf76 if self.targetable
                      else Theme.shade_ddbd77 if self.view and self.view.active else Theme.shade_947b53)
        bg = QLinearGradient(0, 0, self.width(), self.height())
        bg.setColorAt(0, QColor(Theme.shade_274944))
        bg.setColorAt(1, QColor(Theme.shade_101f22))
        if self.selected_target or self.targetable or self.attack_role or self.turn_glow > 0:
            for inset, alpha in ((0, 55), (2, 90)):
                glow = QColor(edge)
                glow.setAlpha(alpha)
                p.setPen(QPen(glow, 5))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(r.adjusted(inset, inset, -inset, -inset), 11, 11)
        p.setPen(QPen(edge, 5 if self.selected_target else 3 if self.targetable or self.attack_role else 2))
        p.setBrush(bg)
        p.drawRoundedRect(r, 10, 10)
        p.setPen(QPen(QColor(210, 176, 112, 125), 1))
        p.drawRoundedRect(r.adjusted(5, 5, -5, -5), 7, 7)
        if self.selected_target:
            p.setPen(QPen(QColor(Theme.shade_fff0a5), 2))
            p.drawRoundedRect(r.adjusted(9, 9, -9, -9), 6, 6)
        if not self.view:
            return
        v = self.view
        portrait = RESOURCES.general_portrait(v.character_id, v.character_name)
        portrait_w = min(108, int(self.width() * .42))
        image_rect = QRectF(8, 8, portrait_w, self.height()-16)
        path = QPainterPath()
        path.addRoundedRect(image_rect, 5, 5)
        p.setClipPath(path)
        p.drawPixmap(image_rect.toRect(), portrait)
        p.setClipping(False)
        p.setPen(QPen(QColor(Theme.shade_d9bd7a), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(image_rect, 5, 5)
        if self.attack_role:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(Theme.shade_975034 if self.attack_role == "attacker" else Theme.shade_356c75))
            p.drawRoundedRect(QRectF(image_rect.x()+4, image_rect.y()+4, 38, 17), 3, 3)
            p.setPen(QColor(Theme.shade_fff0cf))
            p.setFont(QFont("Microsoft YaHei UI", 8, QFont.Bold))
            p.drawText(QRectF(image_rect.x()+4, image_rect.y()+4, 38, 17), Qt.AlignCenter,
                       "出杀" if self.attack_role == "attacker" else "受击")
        if not v.alive:
            p.fillRect(image_rect, QColor(0, 0, 0, int(165*self.death_opacity)))
        x = portrait_w + 18
        faction = v.faction
        p.setPen(QColor(Theme.shade_f3e1b8))
        p.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        p.drawText(x, 29, v.character_name)
        p.setPen(QColor(Theme.shade_d1aa69))
        p.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        p.drawText(x, 47, f"{faction}  ·  {v.name}")
        icon = RESOURCES.identity_icon(v.identity_label)
        p.drawPixmap(self.width()-39, 9, 30, 30, icon)
        for i in range(v.max_hp):
            cx = x + 8 + i*19
            bead = QLinearGradient(cx-7, 55, cx+7, 70)
            bead.setColorAt(0, QColor(Theme.shade_ed7464 if i < v.hp else Theme.shade_5c6560))
            bead.setColorAt(1, QColor(Theme.shade_852f30 if i < v.hp else Theme.shade_313b3b))
            p.setBrush(bead)
            p.setPen(QPen(QColor(Theme.shade_efc787 if i < v.hp else Theme.shade_72807a), 1.5))
            p.drawEllipse(cx-7, 55, 14, 14)
        p.setFont(QFont("Microsoft YaHei UI", 8))
        p.setPen(QColor(Theme.shade_c5c9b4))
        p.drawText(x, 86, f"手牌 {v.hand_count}    体力 {v.hp}/{v.max_hp}")
        for j, title in enumerate(("装备", "判定")):
            box = QRectF(x+j*(self.width()-x-13)/2, 96, (self.width()-x-20)/2, 25)
            p.setPen(QPen(QColor(Theme.shade_7d7761), 1))
            p.setBrush(QColor(12, 29, 31, 155))
            p.drawRoundedRect(box, 4, 4)
            p.setPen(QColor(Theme.shade_a9ae9c))
            cards=v.equipment if j==0 else v.judgments
            p.setFont(QFont("Microsoft YaHei UI", 7))
            p.drawText(box, Qt.AlignCenter, ' / '.join(c.name for c in cards) or title)
        p.setFont(QFont("Microsoft YaHei UI", 8))
        p.setPen(QColor(Theme.accent if v.active else Theme.muted))
        p.drawText(QRectF(x, self.height()-25, self.width()-x-10, 17), Qt.AlignCenter,
                   ('当前回合 · 连环' if v.chained else '当前回合') if v.active and v.alive else "连环" if v.chained else "技能 · —")
        if self.damage_flash > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(180, 43, 33, int(130*self.damage_flash)))
            p.drawRoundedRect(r, 10, 10)
        if not v.alive:
            p.setOpacity(self.death_opacity)
            p.setPen(QColor(Theme.shade_e7b9a9))
            p.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
            p.drawText(r, Qt.AlignCenter, "阵亡")

"""Artwork-led physical card, with selection and hover movement."""
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton
from sanguosha.projection import CardView
from .resources import RESOURCES
from .theme import Theme

class CardWidget(QPushButton):
    card_selected = Signal(str)
    def __init__(self, card: CardView) -> None:
        super().__init__()
        self.card = card
        self.card_id = str(card.card_id)
        self.card_name = card.name
        self.suit = card.suit
        self.setObjectName(f"card-{self.card_id}")
        self.setFixedSize(Theme.card_width, Theme.card_height)
        self.category_label = {"basic":"基础牌", "trick":"锦囊牌", "delayed_trick":"延时锦囊", "equipment":"装备牌"}.get(card.category, "卡牌")
        self.setToolTip(card.details or f"{card.suit} {card.rank} · {card.name} · {self.category_label}")
        self.setText(card.name)
        self.clicked.connect(lambda: self.card_selected.emit(self.card_id))
        self._selected = False
        self._selectable = False
        self._hover = False
        self._response_candidate = False
        self._lift = 0
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(130)
        self._animation.valueChanged.connect(self._set_lift)
        self.setCursor(Qt.PointingHandCursor)

    def _set_lift(self, value) -> None:
        self._lift = int(value)
        self.update()

    def _animate_lift(self) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._lift)
        self._animation.setEndValue(10 if self._selected else 7 if self._hover else 0)
        self._animation.start()

    def set_selectable(self, value: bool) -> None:
        self._selectable = value
        self.setEnabled(value)
        self.update()

    def set_selected(self, value: bool) -> None:
        if self._selected == value:
            return
        self._selected = value
        self._animate_lift()
        self.update()

    def set_response_candidate(self, value: bool) -> None:
        self._response_candidate = value
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self._animate_lift()
        self.raise_()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self._animate_lift()
        self.update()
        super().leaveEvent(event)

    def _draw_suit(self, p: QPainter, x: float, y: float) -> None:
        """Draw suit shapes directly so they survive systems without symbol fonts."""
        suit = self.suit
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(Theme.shade_a13a36 if suit in ("♥", "♦") else Theme.shade_263238))
        if suit == "♦":
            path = QPainterPath(QPointF(x+7, y))
            path.lineTo(x+14, y+8)
            path.lineTo(x+7, y+16)
            path.lineTo(x, y+8)
            path.closeSubpath()
            p.drawPath(path)
        elif suit == "♥":
            path = QPainterPath(QPointF(x+7, y+15))
            path.cubicTo(x-5, y+8, x, y-3, x+7, y+4)
            path.cubicTo(x+14, y-3, x+19, y+8, x+7, y+15)
            p.drawPath(path)
        elif suit == "♠":
            path = QPainterPath(QPointF(x+7, y))
            path.cubicTo(x-5, y+9, x, y+15, x+7, y+11)
            path.cubicTo(x+14, y+15, x+19, y+9, x+7, y)
            p.drawPath(path)
            p.drawRect(QRectF(x+5, y+10, 4, 6))
        elif suit == "♣":
            for dx, dy in ((4, 6), (10, 6), (7, 2)):
                p.drawEllipse(QRectF(x+dx-3, y+dy-3, 6, 6))
            p.drawRect(QRectF(x+5, y+8, 4, 7))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        y = 10 - self._lift
        accent = {"basic.slash": Theme.slash, "basic.dodge": Theme.dodge, "basic.peach": Theme.peach}.get(self.card.definition_id, Theme.category_accents.get(self.card.category, Theme.card_edge))
        outer = QRectF(2, y, 112, 152)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 75))
        p.drawRoundedRect(outer.translated(2, 4), 8, 8)
        if self._selected or self._response_candidate:
            for pad, opacity in ((0, 80), (2, 125)):
                p.setBrush(Qt.NoBrush)
                color = QColor(Theme.shade_ffe077)
                color.setAlpha(opacity)
                p.setPen(QPen(color, 5))
                p.drawRoundedRect(outer.adjusted(pad, pad, -pad, -pad), 8, 8)
        grad = QLinearGradient(0, y, 0, y+152)
        grad.setColorAt(0, QColor(Theme.shade_f9f0d8))
        grad.setColorAt(1, QColor(Theme.shade_d5bf91))
        p.setBrush(grad)
        p.setPen(QPen(QColor(Theme.shade_fff1a6 if self._selected else Theme.shade_f1d283 if self._response_candidate or self._hover else Theme.shade_6a492c),
                      4 if self._selected else 3))
        p.drawRoundedRect(outer, 7, 7)
        p.setPen(QPen(QColor(accent), 2))
        p.drawRoundedRect(outer.adjusted(4, 4, -4, -4), 5, 5)
        art_box = QRectF(9, y+29, 98, 84)
        path = QPainterPath()
        path.addRoundedRect(art_box, 3, 3)
        p.setClipPath(path)
        art = RESOURCES.card_art(self.card.definition_id or "default.card")
        p.drawPixmap(art_box.toRect(), art)
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(accent), 2))
        p.drawRoundedRect(art_box, 3, 3)
        p.setPen(QColor(Theme.shade_a13a36 if self.suit in ("♥", "♦") else Theme.shade_263238))
        self._draw_suit(p, 11, y+7)
        p.setPen(QColor(Theme.shade_a13a36 if self.suit in ("♥", "♦") else Theme.shade_263238))
        p.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        p.drawText(QRectF(30, y+5, 67, 21), Qt.AlignLeft, str(self.card.rank))
        p.setPen(QColor(Theme.shade_322720))
        p.setFont(QFont("Microsoft YaHei UI", 17, QFont.Bold))
        p.drawText(QRectF(12, y+113, 89, 26), Qt.AlignCenter, self.card.name)
        p.setPen(QColor(accent))
        p.drawLine(18, int(y+138), 98, int(y+138))
        p.setFont(QFont("Microsoft YaHei UI", 8))
        p.drawText(QRectF(10, y+138, 96, 14), Qt.AlignCenter, self.category_label)
        if not self._selectable:
            p.fillRect(outer.adjusted(3, 3, -3, -3), QColor(35, 40, 38, 52))

"""Small noninteractive full-art preview for a public equipped card."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget
from sanguosha.projection import CardView
from .resources import RESOURCES
from .card_widget import equipment_label


class EquipmentPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setFixedSize(280, 330)
        self.card: CardView | None = None
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.hide()

    def show_card(self, card: CardView, position) -> None:
        if self.card != card:
            self.card = card
            self.update()
        self.move(position)
        self.show()

    def paintEvent(self, event) -> None:
        if self.card is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        outer = QRectF(3, 3, 274, 324)
        p.setBrush(QColor("#e6d5b0"))
        p.setPen(QPen(QColor("#a17a45"), 4))
        p.drawRoundedRect(outer, 8, 8)
        p.drawPixmap(13, 37, 100, 140, RESOURCES.card_art(self.card.definition_id))
        p.setPen(QColor("#392c22"))
        p.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        p.drawText(QRectF(13, 8, 254, 28), Qt.AlignCenter, equipment_label(self.card))
        p.setFont(QFont("Microsoft YaHei UI", 10))
        p.drawText(QRectF(123, 40, 143, 205), Qt.AlignLeft | Qt.TextWordWrap,
                   self.card.details or f"{self.card.name}\n装备\n暂无效果说明")
        suit = {"♠":"黑桃", "♣":"梅花", "♥":"红桃", "♦":"方片"}.get(self.card.suit, self.card.suit)
        p.drawText(QRectF(13, 278, 254, 24), Qt.AlignCenter,
                   f"{suit}{self.card.rank} · 装备")

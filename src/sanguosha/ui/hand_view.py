"""Adaptive overlapping human hand; opponent cards never enter this widget."""
from PySide6.QtCore import Signal
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget
from sanguosha.projection import CardView
from .card_widget import CardWidget
from .theme import Theme

class HandView(QWidget):
    card_selected = Signal(str)
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(Theme.card_height + 5)
        self.cards: dict[str, CardWidget] = {}

    def render(self, hand: tuple[CardView, ...], selectable: set[str], selected: set[str],
               response_mode: bool = False) -> None:
        old = self.cards
        self.cards = {}
        for card in hand:
            key = str(card.card_id)
            widget = old.pop(key, None)
            if widget is not None and widget.card != card:
                widget.hide()
                widget.deleteLater()
                widget = None
            widget = widget or CardWidget(card)
            widget.setParent(self)
            widget.set_selectable(key in selectable)
            widget.set_selected(key in selected)
            widget.set_response_candidate(response_mode and key in selectable)
            if key not in old and not getattr(widget, '_connected', False):
                widget.card_selected.connect(self.card_selected)
                widget._connected = True
            widget.show()
            self.cards[key] = widget
        for widget in old.values():
            widget.hide()
            widget.deleteLater()
        self._arrange()

    def resizeEvent(self, event) -> None:
        self._arrange()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(2, 3, self.width()-4, self.height()-7)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor("#493322"))
        grad.setColorAt(1, QColor("#241a16"))
        p.setBrush(grad)
        p.setPen(QPen(QColor("#b18b54"), 2))
        p.drawRoundedRect(r, 9, 9)
        p.setPen(QColor(Theme.shade_b39b67))
        p.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        p.drawText(QRectF(14, 9, 100, 22), Qt.AlignLeft, f"手  牌 · {len(self.cards)}")

    def _arrange(self) -> None:
        count = len(self.cards)
        if not count:
            return
        step = min(Theme.card_width + 8, max(0, (self.width()-Theme.card_width-24)/max(1, count-1)))
        start = max(0, (self.width()-(count-1)*step-Theme.card_width)//2)
        for index, widget in enumerate(self.cards.values()):
            widget.move(round(start+index*step), 0)
            widget.raise_()

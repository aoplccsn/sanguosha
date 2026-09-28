"""Presentation-only phase, response and contextual action components."""
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QWidget, QPushButton, QHBoxLayout
from .theme import Theme
PHASES = {"preparation":"准备", "judgment":"判定", "draw":"摸牌", "play":"出牌", "discard":"弃牌", "finish":"结束"}

class PhaseIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = ""
        self.setFixedHeight(32)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        step = self.width()/6
        for i, (key, name) in enumerate(PHASES.items()):
            r = QRectF(i*step+3, 3, step-6, 26)
            active = key == self.phase
            p.setBrush(QColor(Theme.accent if active else Theme.panel))
            p.setPen(QPen(QColor(Theme.accent if active else Theme.muted), 1))
            p.drawRoundedRect(r, 6, 6)
            p.setPen(QColor(Theme.background if active else Theme.muted))
            p.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
            p.drawText(r, Qt.AlignCenter, name)

class PromptPanel(QLabel):
    def __init__(self):
        super().__init__("点击“开始游戏”")
        self.setObjectName("game-prompt")
        self.setWordWrap(True)
        self.setMinimumHeight(44)
        self.mode = "idle"

    def present(self, text):
        self.mode = "response" if "响应" in text or "求桃" in text else "target" if "目标" in text else "idle"
        self.setProperty("mode", self.mode)
        self.setText(text)
        self.style().unpolish(self)
        self.style().polish(self)

class ActionBar(QWidget):
    value_selected = Signal(object)
    def __init__(self):
        super().__init__()
        self.actions = QHBoxLayout(self)
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.buttons = []

    def present(self, actions):
        while self.actions.count():
            item = self.actions.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.buttons = []
        for label, value, enabled in actions:
            button = QPushButton(label)
            button.setProperty("action", True)
            button.setEnabled(enabled)
            button.clicked.connect(lambda checked=False, choice=value: self.value_selected.emit(choice))
            self.actions.addWidget(button)
            self.buttons.append(button)
        self.setVisible(bool(actions))


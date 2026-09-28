"""Compatibility facade composing a prompt HUD and contextual action bar."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget
from .hud import HumanDecisionPrompt, ActionBar

class DecisionController(QWidget):
    value_selected = Signal(object)
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.prompt_label = HumanDecisionPrompt()
        self.action_bar = ActionBar()
        self.action_bar.value_selected.connect(self.value_selected)
        layout.addWidget(self.prompt_label, 1)
        layout.addWidget(self.action_bar)
        self.actions = self.action_bar.actions

    @property
    def buttons(self):
        return self.action_bar.buttons

    def render(self, prompt, actions):
        self.prompt_label.present(prompt)
        self.action_bar.present(actions)


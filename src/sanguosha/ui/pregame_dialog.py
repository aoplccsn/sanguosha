"""Short identity reveal followed by an explicit ten-card general draft."""

import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)

from sanguosha.content.characters.standard import STANDARD_25_GENERAL_POOL, STANDARD_SKILL_CATALOGUE
from sanguosha.engine.requests import Decision
from sanguosha.pregame import Pregame, SetupStage
from sanguosha.projection import IDENTITY_LABELS
from .resources import RESOURCES
from .timing import PREGAME_GENERAL_TIMEOUT_MS


GOAL_HINTS = {
    'lord': '守住阵营，与忠臣合力平定叛乱。',
    'loyalist': '守护主公，协助其击败反贼与内奸。',
    'rebel': '寻找同伴，合力击败主公。',
    'renegade': '审时度势，争取成为最后的胜者。',
}
FACTIONS = {'wei': '魏', 'shu': '蜀', 'wu': '吴', 'qun': '群'}


class GeneralChoiceCard(QPushButton):
    def __init__(self, character, skill_names, parent=None):
        super().__init__(parent)
        self.character = character
        self.setObjectName(f'candidate-{character.id}')
        self.setCheckable(True)
        self.setMinimumSize(135, 190)
        self.setMaximumWidth(170)
        layout = QVBoxLayout(self)
        portrait = QLabel()
        portrait.setPixmap(RESOURCES.general_portrait(str(character.id), character.name).scaled(125, 133, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        portrait.setAlignment(Qt.AlignCenter)
        portrait.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(portrait)
        title = QLabel(f'{character.name}  {FACTIONS[character.kingdom.value]}  {character.max_hp} 体力')
        title.setAlignment(Qt.AlignCenter)
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(title)
        names = QLabel(' · '.join(skill_names))
        names.setAlignment(Qt.AlignCenter)
        names.setWordWrap(True)
        names.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(names)
        self.setStyleSheet('QPushButton {background:#dfcfad;border:2px solid #8c7654;border-radius:6px;}'
                           'QPushButton:hover {border:2px solid #d2a74e;background:#f0dfba;}'
                           'QPushButton:checked {border:4px solid #e2b64d;background:#f4e4bd;}')


class PregameDialog(QDialog):
    def __init__(self, setup: Pregame, parent=None):
        super().__init__(parent)
        self.setup = setup
        self.selected_id = None
        self.setObjectName('pregame-dialog')
        self.setWindowTitle('标准身份局 · 开局')
        self.setMinimumSize(840, 630)
        self.layout = QVBoxLayout(self)
        self.title = QLabel('五张身份牌正在洗入座位…')
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)
        self.content = QWidget()
        self.layout.addWidget(self.content, 1)
        self.bottom = QHBoxLayout()
        self.layout.addLayout(self.bottom)
        self.cards = {}
        self.confirm_button = QPushButton('继续')
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self._confirm)
        self.bottom.addStretch()
        self.bottom.addWidget(self.confirm_button)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._timeout)
        self._show_identity_backs()
        QTimer.singleShot(0 if os.environ.get('SANGUOSHA_FAST_SETUP') else 360, self._reveal_identity)

    def _replace_content(self):
        self.layout.removeWidget(self.content)
        self.content.deleteLater()
        self.content = QWidget()
        self.layout.insertWidget(1, self.content, 1)

    def _show_identity_backs(self):
        row = QHBoxLayout(self.content)
        for _ in range(5):
            back = QLabel('身份')
            back.setAlignment(Qt.AlignCenter)
            back.setFixedSize(125, 175)
            back.setStyleSheet('background:#614b3a;color:#e9d2a2;border:3px solid #b68e4e;border-radius:8px;font-size:25px;')
            row.addWidget(back)

    def _reveal_identity(self):
        if self.setup.stage is not SetupStage.IDENTITY_REVEAL:
            return
        identity = self.setup.human_identity
        self.title.setText(f'你的身份：{IDENTITY_LABELS[identity]}')
        self._replace_content()
        column = QVBoxLayout(self.content)
        identity_card = QLabel(IDENTITY_LABELS[identity])
        identity_card.setAlignment(Qt.AlignCenter)
        identity_card.setFixedSize(180, 240)
        identity_card.setStyleSheet('background:#e7d8b5;color:#683b2d;border:4px solid #d6ad5c;border-radius:8px;font-size:42px;')
        column.addWidget(identity_card, alignment=Qt.AlignCenter)
        hint = QLabel(GOAL_HINTS[identity.value])
        hint.setAlignment(Qt.AlignCenter)
        column.addWidget(hint)
        self.confirm_button.setText('查看十位候选武将')
        self.confirm_button.setEnabled(True)

    def _show_candidates(self):
        self.setup.acknowledge_identity()
        self.title.setText('十选一 · 点击武将查看技能，再确认选择')
        self._replace_content()
        characters = {character.id: character for character in STANDARD_25_GENERAL_POOL}
        skills = {skill.id: skill for skill in STANDARD_SKILL_CATALOGUE}
        outer = QVBoxLayout(self.content)
        grid = QGridLayout()
        outer.addLayout(grid)
        for index, cid in enumerate(self.setup.candidates):
            character = characters[cid]
            card = GeneralChoiceCard(character, [skills[sid].name for sid in character.skill_ids])
            card.clicked.connect(lambda checked=False, selected=cid: self._select(selected))
            self.cards[cid] = card
            grid.addWidget(card, index // 5, index % 5)
        self.details = QLabel('请选择武将以查看详情。')
        self.details.setWordWrap(True)
        outer.addWidget(self.details)
        self.confirm_button.setText('确认选择')
        self.confirm_button.setEnabled(False)
        self._timer.start(PREGAME_GENERAL_TIMEOUT_MS)

    def _select(self, cid):
        if self.setup.stage is not SetupStage.CHOOSE_GENERAL:
            return
        self.selected_id = cid
        for candidate_id, card in self.cards.items():
            card.setChecked(candidate_id == cid)
        character = next(character for character in STANDARD_25_GENERAL_POOL if character.id == cid)
        skills = {skill.id: skill for skill in STANDARD_SKILL_CATALOGUE}
        descriptions = '\n'.join(f'【{skills[sid].name}】{skills[sid].description}' for sid in character.skill_ids)
        self.details.setText(f'{character.name} · {FACTIONS[character.kingdom.value]} · {character.max_hp} 体力\n{descriptions}')
        self.confirm_button.setEnabled(True)

    def _confirm(self):
        if self.setup.stage is SetupStage.IDENTITY_REVEAL:
            self._show_candidates()
        elif self.setup.stage is SetupStage.CHOOSE_GENERAL and self.selected_id is not None:
            request = self.setup.pending_request
            self.setup.submit(Decision(request.request_id, self.setup.human_id, self.selected_id))
            self._timer.stop()
            self.accept()

    def _timeout(self):
        if self.setup.stage is SetupStage.CHOOSE_GENERAL:
            self.setup.timeout()
            self.accept()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)

"""Public character details and the human player's nearby skill controls."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from sanguosha.model.enums import Identity, SkillType
from sanguosha.content.characters.classic import SKILLS as IMPLEMENTED_SKILLS
from sanguosha.projection import PlayerView
from .resources import RESOURCES


TYPE_LABELS = {
    SkillType.ACTIVE: '主动', SkillType.TRIGGERED: '触发',
    SkillType.LOCKED: '锁定', SkillType.VIEW_AS: '转化',
    SkillType.LIMITED: '限定', SkillType.RULE_MODIFIER: '规则',
}
IMPLEMENTED_SKILL_IDS = {skill.id for skill in IMPLEMENTED_SKILLS}
IMPLEMENTED_SKILL_IDS.update((
    'fankui', 'guicai', 'ganglie', 'tuxi', 'luoyi', 'tiandu', 'yiji', 'luoshen', 'qingguo',
    'paoxiao', 'kongcheng', 'mashu', 'qicai', 'jizhi', 'qixi', 'keji', 'kurou',
    'yingzi', 'fanjian', 'qianxun', 'lianying', 'jieyin', 'xiaoji', 'qingnang', 'biyue',
))


def skill_status(skill, player, state, choices=()):
    if skill.id not in IMPLEMENTED_SKILL_IDS:
        return '规则开发中'
    if skill.metadata.get('lord') and player.identity is not Identity.LORD:
        return '当前身份下未启用'
    if f'skill:{skill.id}' in choices or f'virtual:{skill.id}' in choices:
        return '可用'
    if skill.skill_type is SkillType.VIEW_AS and any(str(choice).startswith(f'virtual:{skill.id}:') for choice in choices):
        return '可用'
    if skill.skill_type is SkillType.LOCKED:
        return '锁定生效'
    if skill.skill_type is SkillType.TRIGGERED:
        return '等待触发'
    if skill.skill_type is SkillType.ACTIVE:
        if f'skill:{skill.id}' in choices:
            return '可用'
        if state.play_usage and state.play_usage.player_id == player.player_id and state.play_usage.count(f'skill.{skill.id}'):
            return '已使用'
        return '当前不可用'
    if skill.skill_type is SkillType.VIEW_AS:
        return '等待合法时机'
    return '当前不可用'


class GeneralDetailPanel(QDialog):
    def __init__(self, view: PlayerView, character, skills, player, state, choices=(), parent=None):
        super().__init__(parent)
        self.setObjectName('general-detail')
        self.setWindowTitle(f'{character.name} · 武将详情')
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        portrait = QLabel()
        portrait.setPixmap(RESOURCES.general_portrait(str(character.id), character.name).scaledToHeight(260, Qt.SmoothTransformation))
        portrait.setAlignment(Qt.AlignCenter)
        layout.addWidget(portrait)
        faction = {'wei': '魏', 'shu': '蜀', 'wu': '吴', 'qun': '群'}[character.kingdom.value]
        layout.addWidget(QLabel(f'{character.name}  ·  {faction}  ·  体力 {view.hp}/{view.max_hp}'))
        for sid in character.skill_ids:
            skill = skills[sid]
            title = f'{skill.name} · {"主公" if skill.metadata.get("lord") else TYPE_LABELS[skill.skill_type]}'
            label = QLabel(f'{title}\n{skill.description}\n状态：{skill_status(skill, player, state, choices)}')
            label.setWordWrap(True)
            layout.addWidget(label)
        close = QPushButton('关闭')
        close.clicked.connect(self.close)
        layout.addWidget(close)


class SkillBar(QWidget):
    selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('human-skill-bar')
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(4, 0, 4, 0)
        self.row.addStretch()
        self.buttons = {}

    def render(self, character, skills, player, state, choices=()):
        while self.row.count():
            item = self.row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons = {}
        self.row.addStretch()
        if character is not None:
            for sid in character.skill_ids:
                skill = skills[sid]
                status = skill_status(skill, player, state, choices)
                button = QPushButton(skill.name)
                button.setObjectName(f'skill-{sid}')
                button.setToolTip(f'{skill.description}\n{status}')
                button.setProperty('action', True)
                button.setEnabled(status == '可用')
                button.clicked.connect(lambda checked=False, skill_id=str(sid): self.selected.emit(skill_id))
                self.row.addWidget(button)
                self.buttons[str(sid)] = button
        self.row.addStretch()

import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication,QLabel
from sanguosha.content.characters.remaining import REMAINING_DEV_GENERALS
from sanguosha.engine.skills import SkillRegistry
from sanguosha.ui.general_detail import GeneralDetailPanel,SkillBar
from sanguosha.ui.pregame_dialog import GeneralChoiceCard
from sanguosha.projection import project_for_human
from test_t17c_first_batch import setup

@pytest.mark.parametrize('general',REMAINING_DEV_GENERALS,ids=lambda c:c.id)
def test_new_general_desktop_portrait_selection_detail_and_skill_status(general):
    app=QApplication.instance() or QApplication([]);s=setup('cao_zhang')
    p=s.state.players['p1'];p.character_id=general.id;p.hp=p.max_hp=general.max_hp
    registry=SkillRegistry();view=project_for_human(s.state,s.definitions,'p1',{})
    pv=next(p for p in view.players if p.player_id=='p1')
    card=GeneralChoiceCard(general,[registry.skills[s].name for s in general.skill_ids]);detail=None
    try:
        portraits=[label.pixmap() for label in card.findChildren(QLabel) if label.pixmap() and not label.pixmap().isNull()]
        assert portraits
        detail=GeneralDetailPanel(pv,general,registry.skills,p,s.state)
        texts=' '.join(label.text() for label in detail.findChildren(QLabel))
        assert '规则开发中' not in texts
        for sid in general.skill_ids:assert registry.skills[sid].name in texts
    finally:
        card.close()
        if detail:detail.close()

def test_borrowed_skill_bar_available_and_disabled_native_status():
    app=QApplication.instance() or QApplication([]);s=setup('cao_zhang');p=s.state.players['p1']
    p.granted_skills['qixi']='duorui:test';p.disabled_skills.add('jiangchi');bar=SkillBar()
    try:
        bar.render(s.skills.characters[p.character_id],s.skills.skills,p,s.state,('virtual:qixi:card',))
        assert 'qixi' in bar.buttons and bar.buttons['qixi'].isEnabled()
        assert '已失去' in bar.buttons['jiangchi'].toolTip()
    finally:bar.close()


@pytest.mark.parametrize('general',REMAINING_DEV_GENERALS,ids=lambda c:c.id)
def test_production_desktop_ten_general_selection_confirms_new_general(general):
    from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
    from sanguosha.pregame import Pregame,SetupStage
    from sanguosha.ui.pregame_dialog import PregameDialog
    from sanguosha.session import GameSession
    app=QApplication.instance() or QApplication([])
    setup_state=Pregame.create(18103)
    setup_state.candidates=(general.id,)+tuple(c.id for c in PLAYABLE_GENERAL_POOL if c.id!=general.id)[:9]
    dialog=PregameDialog(setup_state)
    try:
        dialog._show_candidates();assert len(dialog.cards)==10
        dialog.cards[general.id].click()
        assert general.name in dialog.details.text() and dialog.confirm_button.isEnabled()
        dialog.confirm_button.click()
        assert setup_state.stage is SetupStage.COMPLETE and setup_state.generals['p1']==general.id
        session=GameSession.new_game(seed=18103,military=True,setup=setup_state)
        assert session.state.players['p1'].character_id==general.id
        session.step_auto()
        assert session.state.turn_number>=1
    finally:dialog.close()

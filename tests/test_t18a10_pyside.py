import pytest
from PySide6.QtWidgets import QApplication,QLabel
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.engine.skills import SkillRegistry
from sanguosha.ui.general_detail import GeneralDetailPanel
from sanguosha.session import GameSession
from sanguosha.projection import project_for_human

@pytest.mark.parametrize('general',PLAYABLE_GENERAL_POOL,ids=lambda g:g.id)
def test_103_pyside_details_use_authoritative_description(general):
 app=QApplication.instance() or QApplication([])
 s=GameSession.new_game(military=True,five_generals=True);p=s.state.players['p1'];p.character_id=general.id;p.hp=p.max_hp=general.max_hp
 registry=SkillRegistry();pv=project_for_human(s.state,s.definitions,'p1',{'p1':general.name}).players[0]
 panel=GeneralDetailPanel(pv,general,registry.skills,p,s.state)
 try:
  text=' '.join(label.text() for label in panel.findChildren(QLabel))
  for sid in general.skill_ids:
   assert registry.skills[sid].name in text
   assert registry.skills[sid].description in text
  assert not any(word in text for word in ('规则摘要','待补','TODO','placeholder'))
 finally:panel.close()

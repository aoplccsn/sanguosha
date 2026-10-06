"""Scoped desktop horse/abolished-slot presentation; not final smoke."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from sanguosha.ui.card_widget import CardWidget,equipment_label
from sanguosha.ui.player_panel import PlayerPanel
from sanguosha.projection import project_for_human
from test_t18a11_equipment_distance import game,put


@pytest.mark.parametrize('key,sign,slot',[('chitu','-1','offensive_horse'),('jueying','+1','defensive_horse')])
def test_signed_horse_hand_card_and_equipment_token(key,sign,slot):
 app=QApplication.instance() or QApplication([])
 s=game();cid=put(s,'equipment.horse.'+key)
 view=project_for_human(s.state,s.definitions,'p1',{})
 card=next(c for c in view.hand if c.card_id==cid)
 widget=CardWidget(card);panel=PlayerPanel('p1')
 try:
  assert widget.text().endswith(' '+sign)
  assert equipment_label(card,compact=True).endswith(' '+sign)
  assert sign+'\u9a6c' in panel._equipped_slots()
 finally:widget.close();panel.close()

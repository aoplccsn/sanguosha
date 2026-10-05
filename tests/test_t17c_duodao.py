from dataclasses import replace
import pytest
from test_t17c_first_batch import setup, restore
from test_t17b_tier1 import answer, finish
from test_t6_military_basics import put
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.model.enums import EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType

@pytest.mark.parametrize('target,weapon,propagated,kind,expected',[
    ('p2',None,False,'slash',1),('p3',None,False,'slash',2),
    ('p3','equipment.weapon.serpent_spear',False,'slash',1),
    ('p3',None,True,'slash',1),('p3',None,False,'duel',1)])
def test_anjian_reversed_range_weapon_chain_and_non_slash(target,weapon,propagated,kind,expected):
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_pan_zhang_ma_zhong'
    if weapon: put(s,weapon,target,ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    c=put(s,'basic.slash');hp=s.state.players[target].hp
    s.engine.start_action(MilitaryDamageAction('damage','p1',target,1,card_id=c,propagated=propagated,card_kind=kind))
    finish(s);assert s.state.players[target].hp==hp-expected

def test_anjian_silver_lion_caps_final_damage():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_pan_zhang_ma_zhong'
    put(s,'equipment.armor.silver_lion','p3',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    c=put(s,'basic.slash');hp=s.state.players['p3'].hp
    s.engine.start_action(MilitaryDamageAction('damage','p1','p3',1,card_id=c,card_kind='slash'))
    finish(s);assert s.state.players['p3'].hp==hp-1

@pytest.mark.parametrize('wanted',[False,True])
def test_duodao_after_slash_cost_and_weapon_obtain_restore(wanted):
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_pan_zhang_ma_zhong'
    weapon=put(s,'equipment.weapon.serpent_spear','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    c=put(s,'basic.slash','p2');s.engine.start_action(MilitaryDamageAction('hurt','p2','p1',1,card_id=c,card_kind='slash'))
    assert s.engine.pending_request is not None;s=restore(s);answer(s,wanted)
    if wanted:
        s=restore(s);cost=s.engine.pending_request.eligible_card_ids[0];answer(s,cost)
        assert cost in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert (weapon in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==wanted
    assert (weapon in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.WEAPON)))!=wanted
    assert s.engine.pending_request is None

@pytest.mark.parametrize('kind,weapon',[('duel',True),('slash',False)])
def test_duodao_non_slash_or_no_weapon_has_no_offer(kind,weapon):
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_pan_zhang_ma_zhong'
    if weapon:put(s,'equipment.weapon.serpent_spear','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    c=put(s,'basic.slash','p2');s.engine.start_action(MilitaryDamageAction('hurt','p2','p1',1,card_id=c,card_kind=kind))
    assert s.engine.pending_request is None

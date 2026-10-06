import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.remaining_gods import RemainingGodAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.events import AfterDamageEvent
from sanguosha.model.enums import Phase,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType


def luxun():
    s=setup('cao_zhang');s.state.players['p1'].character_id='shadow_god_luxun'
    for q in s.state.seat_order:empty(s,q)
    return s


@pytest.mark.parametrize('amount',[1,2,3])
def test_junlve_counts_each_damage_point_dealt_and_received(amount):
    s=luxun();s.state.players['p1'].hp=s.state.players['p1'].max_hp=8
    s.engine.start_action(MilitaryDamageAction('deal','p1','p2',amount))
    assert s.state.players['p1'].marks['junlve']==amount
    s.engine.start_action(MilitaryDamageAction('receive','p2','p1',amount))
    assert s.state.players['p1'].marks['junlve']==amount*2
    s=restore(s);assert s.state.players['p1'].marks['junlve']==amount*2


def test_junlve_self_damage_has_both_damage_roles():
    s=luxun();s.engine.start_action(MilitaryDamageAction('self','p1','p1',1))
    assert s.state.players['p1'].marks['junlve']==2


@pytest.mark.parametrize('burst',[True,False])
def test_cuike_odd_seven_damage_creates_eighth_mark_then_optional_burst(burst):
    s=luxun();s.state.players['p1'].marks['junlve']=7
    s.engine.start_action(PhaseAction('play','p1',Phase.PLAY));s=restore(s);answer(s,True)
    s=restore(s);answer(s,'p2');s=restore(s)
    assert '所有其他角色' in s.engine.pending_request.prompt
    assert s.state.players['p1'].marks['junlve']==8
    answer(s,burst)
    assert s.state.players['p1'].marks['junlve']==(4 if burst else 8)
    assert s.state.players['p2'].hp==(2 if burst else 3)
    assert s.engine.pending_request.request_type.value=='choose_option'


def test_cuike_even_can_chain_empty_target():
    s=luxun();s.engine.start_action(RemainingGodAction('cuike','p1','cuike'));answer(s,True);answer(s,'p2')
    assert s.state.players['p2'].chained and s.engine.pending_request is None


def test_cuike_even_discards_judgment_region_card_restore():
    s=luxun();card=put(s,'delayed.indulgence','p2',ZoneType.JUDGMENT)
    s.engine.start_action(RemainingGodAction('cuike','p1','cuike'));answer(s,True);answer(s,'p2')
    s=restore(s);assert card in s.engine.pending_request.eligible_card_ids;answer(s,card)
    assert s.state.players['p2'].chained and card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_zhanhuo_all_equipment_departures_before_fire_then_fresh_junlve():
    s=luxun();s.state.players['p1'].marks['junlve']=2;s.state.players['p1'].hp=1
    s.state.players['p1'].chained=s.state.players['p2'].chained=True
    silver=put(s,'equipment.armor.silver_lion','p1',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    vine=put(s,'equipment.armor.vine','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.engine.start_action(RemainingGodAction('fire','p1','zhanhuo'));s=restore(s)
    assert s.engine.pending_request.max_count==2;answer(s,('p2','p1'));s=restore(s)
    assert {silver,vine}<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert s.state.players['p1'].hp==2 and s.state.players['p1'].marks['junlve']==0
    answer(s,'p2')
    assert s.state.players['p2'].hp==3 and s.state.players['p1'].hp==1
    assert s.state.players['p1'].marks['junlve']==3
    assert not s.state.players['p2'].chained and not s.state.players['p1'].chained
    with pytest.raises(InvalidCardUse):s.engine.start_action(RemainingGodAction('again','p1','zhanhuo'))


def test_zhanhuo_without_mark_or_chain_not_available():
    s=luxun()
    with pytest.raises(InvalidCardUse):s.engine.start_action(RemainingGodAction('none','p1','zhanhuo'))
    s=luxun();s.state.players['p1'].marks['junlve']=1
    with pytest.raises(InvalidCardUse):s.engine.start_action(RemainingGodAction('no-chain','p1','zhanhuo'))

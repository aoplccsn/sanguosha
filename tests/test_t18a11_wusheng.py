from dataclasses import replace
import pytest
from test_t17c_first_batch import setup
from test_t6_military_basics import put,resolve
from sanguosha.engine.skills import WushengUse
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.requests import Decision
from sanguosha.model.enums import Suit,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.snapshot import snapshot_session,restore_session


def owner(acquired):
    s=setup('cao_zhang');p=s.state.players['p1']
    p.character_id='mountain_zuoci' if acquired else 'guanyu'
    if acquired:p.transformation_pool=['guanyu'];p.active_transformation='guanyu';p.transformation_skill='wusheng'
    return s

@pytest.mark.parametrize('acquired',[False,True])
@pytest.mark.parametrize('response',[False,True])
def test_red_equipment_is_a_real_wusheng_cost_for_use_and_response(acquired,response):
    s=owner(acquired);cost=put(s,'equipment.weapon.kylin_bow','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    s.state.cards[cost]=replace(s.state.cards[cost],suit=Suit.HEART)
    s=restore_session(snapshot_session(s))
    if response:
        s.engine.start_action(RespondWithCardAction('response','p1','basic.slash','external'))
        r=s.engine.pending_request;assert 'virtual:wusheng:'+cost in r.eligible_card_ids
        s.engine.submit_decision(Decision(r.request_id,r.player_id,'virtual:wusheng:'+cost))
    else:
        s.engine.start_action(WushengUse('use','p1',cost));r=s.engine.pending_request
        s.engine.submit_decision(Decision(r.request_id,r.player_id,'p2'));resolve(s)
    assert cost in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON))
    s.state.__post_init__()

@pytest.mark.parametrize('slot,definition',[(EquipmentSlot.WEAPON,'equipment.weapon.kylin_bow'),(EquipmentSlot.OFFENSIVE_HORSE,'equipment.horse.chitu')])
def test_wusheng_cost_cannot_retain_consumed_weapon_or_horse_distance(slot,definition):
    s=owner(True);cost=put(s,definition,'p1',ZoneType.EQUIPMENT,slot)
    s.state.cards[cost]=replace(s.state.cards[cost],suit=Suit.HEART)
    s.engine.start_action(WushengUse('cost-distance','p1',cost))
    assert 'p2' in s.engine.pending_request.allowed_player_ids
    assert 'p3' not in s.engine.pending_request.allowed_player_ids

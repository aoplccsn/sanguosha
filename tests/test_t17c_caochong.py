from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.engine.events import AfterDamageEvent
from sanguosha.model.enums import EquipmentSlot,DamageNature
from sanguosha.model.zones import ZoneRef,ZoneType

def cao():
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_cao_chong';return s

@pytest.mark.parametrize('ranks',[(1,2,3,7),(13,13,13,13),(6,7,8,9)])
def test_chengxiang_reveal_budget_nonempty_and_restore(ranks):
    s=cao();top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:4]
    for c,rank in zip(top,ranks):s.state.cards[c]=replace(s.state.cards[c],rank=rank)
    s.engine.start_action(YJ2013Action('skill','p1','chengxiang'));s=restore(s);answer(s,True)
    chosen=[]
    while s.engine.pending_request:
        s=restore(s);r=s.engine.pending_request
        if r.eligible_card_ids:
            assert all(s.state.cards[c].rank+sum(s.state.cards[x].rank for x in chosen)<=13 for c in r.eligible_card_ids)
            card=r.eligible_card_ids[0];chosen.append(card);answer(s,card)
        else:answer(s,'continue')
    assert chosen and sum(s.state.cards[c].rank for c in chosen)<=13
    assert all(c in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')) for c in chosen)
    assert all(c in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for c in top if c not in chosen)
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))

def test_chengxiang_one_offer_for_multi_point_damage_decline():
    s=cao();s.engine.start_action(MilitaryDamageAction('hurt','p2','p1',2))
    assert s.engine.pending_request;s=restore(s);answer(s,False)
    assert s.engine.pending_request is None

def test_chengxiang_can_finish_after_first_pick():
    s=cao();top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:4]
    for c in top:s.state.cards[c]=replace(s.state.cards[c],rank=1)
    s.engine.start_action(YJ2013Action('skill','p1','chengxiang'));answer(s,True);answer(s,top[0]);s=restore(s);answer(s,'finish')
    assert all(c in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for c in top[1:])

@pytest.mark.parametrize('wanted',[False,True])
@pytest.mark.parametrize('zone',[ZoneType.HAND,ZoneType.EQUIPMENT])
def test_renxin_other_one_hp_equipment_cost_turnover_prevents_all_damage(wanted,zone):
    s=cao();s.state.players['p2'].hp=1
    c=put(s,'equipment.weapon.serpent_spear','p1',zone,EquipmentSlot.WEAPON if zone is ZoneType.EQUIPMENT else None)
    s.engine.start_action(MilitaryDamageAction('hurt','p3','p2',3))
    assert s.engine.pending_request.player_id=='p1';s=restore(s);answer(s,wanted)
    if wanted:
        assert c in s.engine.pending_request.eligible_card_ids;s=restore(s);answer(s,c)
        assert s.state.players['p2'].hp==1 and not s.state.players['p1'].face_up
        assert c in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
        assert not any(isinstance(e,AfterDamageEvent) and e.target_id=='p2' for e in s.events.events)
    else:finish(s)

@pytest.mark.parametrize('hp,self_target',[(2,False),(1,True)])
def test_renxin_only_other_exact_one_hp(hp,self_target):
    s=cao();target='p1' if self_target else 'p2';s.state.players[target].hp=hp
    put(s,'equipment.weapon.serpent_spear')
    s.engine.start_action(MilitaryDamageAction('hurt','p3',target,1))
    assert s.engine.pending_request is None or s.engine.pending_request.player_id!= 'p1' or 'renxin' not in s.engine.pending_request.request_id
    finish(s)

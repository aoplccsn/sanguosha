from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put,resolve
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.pindian import PindianAction
from sanguosha.engine.turns import TurnAction
from sanguosha.engine.death import DeathAction
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.card_moves import CardMove,CardMoveService,CardMoveReason,InvalidCardMove
from sanguosha.engine.skill_leases import begin_lease,expire_target,leases
from sanguosha.engine.skill_grants import add_grant,grant_sources
from sanguosha.engine.zhangliao import borrowable
from sanguosha.engine.fire import FireHandLimit
from sanguosha.engine.wind import WindHandLimit
from sanguosha.model.enums import Phase,Suit,EquipmentSlot,Identity
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.projection import project_for_human


def game():
    s=setup('cao_zhang');s.state.players['p1'].character_id='thunder_god_zhangliao';s.state.players['p2'].character_id='guanyu'
    for q in s.state.seat_order:empty(s,q)
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return s


def borrow(s,slot='weapon'):
    s.engine.start_action(MilitaryDamageAction('hurt','p1','p2',1));s=restore(s)
    assert '夺锐' in s.engine.pending_request.prompt;answer(s,True);s=restore(s)
    if len(s.state.players['p1'].abolished_equipment_slots)<4:answer(s,slot);s=restore(s)
    assert s.engine.pending_request.choices==('wusheng',);answer(s,'wusheng')
    return s


def test_duorui_actual_slot_borrow_suppression_and_exact_target_turn_end_restore():
    s=borrow(game());assert EquipmentSlot.WEAPON in s.state.players['p1'].abolished_equipment_slots
    assert s.skills.has(s.state,'p1','wusheng') and not s.skills.has(s.state,'p2','wusheng')
    s.engine.start_action(TurnAction('own-end','p1',phases=(Phase.FINISH,)))
    assert s.skills.has(s.state,'p1','wusheng') and not s.skills.has(s.state,'p2','wusheng')
    s.engine.start_action(TurnAction('target-end','p2',phases=(Phase.FINISH,)))
    assert not s.skills.has(s.state,'p1','wusheng') and s.skills.has(s.state,'p2','wusheng') and not leases(s.state)


def test_duorui_cannot_repeat_while_lease_active_and_all_slots_abolished_skips_cost():
    s=game();s.state.players['p1'].abolished_equipment_slots=set(EquipmentSlot);s=borrow(s)
    s.engine.start_action(MilitaryDamageAction('again','p1','p2',1))
    assert s.engine.pending_request is None and len(leases(s.state))==1


def test_duorui_abolished_equipment_uses_loss_pipeline_and_cannot_equip_again():
    s=game();s.state.players['p1'].hp=2
    old=put(s,'equipment.armor.silver_lion','p1',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s=borrow(s,'armor');assert s.state.players['p1'].hp==3
    assert old in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    new=put(s,'equipment.armor.vine')
    with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('equip','p1',new))
    assert new in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')) and s.engine.stack.is_empty()
    with pytest.raises(InvalidCardMove):CardMoveService(s.events).move(s.state,CardMove('raw',(new,),ZoneRef(ZoneType.HAND,'p1'),ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.ARMOR),CardMoveReason.SYSTEM))


def test_duorui_target_death_expires_lease_without_erasing_permanent_suppression():
    s=borrow(game());s.state.players['p2'].disabled_skills.add('wusheng')
    s.engine.start_action(DeathAction('death','p2',None));resolve(s)
    assert not leases(s.state) and not s.skills.has(s.state,'p1','wusheng')
    assert 'wusheng' in s.state.players['p2'].disabled_skills


def test_duorui_borrower_death_removes_grant_but_target_suppression_lasts_to_target_end():
    s=borrow(game());s.state.players['p1'].identity=Identity.REBEL;s.state.players['p3'].identity=Identity.LORD
    s.engine.start_action(DeathAction('source-death','p1',None));resolve(s)
    assert 'wusheng' not in s.state.players['p1'].granted_skills
    assert not s.skills.has(s.state,'p2','wusheng')
    s.engine.start_action(TurnAction('target-end','p2',phases=(Phase.FINISH,)))
    assert s.skills.has(s.state,'p2','wusheng') and not leases(s.state)


def test_duorui_grant_sources_coexist_with_earlier_and_fuhun_grants():
    s=game();s.state.players['p1'].granted_skills['wusheng']='earlier'
    begin_lease(s.state,'p1','p2','wusheng');add_grant(s.state,'p1','wusheng','fuhun:4')
    s=restore(s);expire_target(s.state,'p2')
    assert set(grant_sources(s.state,'p1','wusheng'))=={'earlier','fuhun:4'}
    from sanguosha.engine.fuhun import clear_grants
    clear_grants(s.state,'p1');assert s.state.players['p1'].granted_skills['wusheng']=='earlier'


def test_duorui_eligible_native_skills_excludes_lord_awakening_limited_special_and_grants():
    s=game();p=s.state.players['p2'];p.character_id='yj2012_zhong_hui';p.granted_skills['paoxiao']='test'
    assert borrowable(s.state,'p2',s.skills)==('quanji',)
    p.character_id='yj2012_liao_hua';assert borrowable(s.state,'p2',s.skills)==('dangxian',)
    p.character_id='liubei';assert borrowable(s.state,'p2',s.skills)==('rende',)
    p.character_id='fire_god_zhugeliang';assert 'qixing' not in borrowable(s.state,'p2',s.skills) and 'kuangfeng' not in borrowable(s.state,'p2',s.skills)


@pytest.mark.parametrize('wounded,in_range',[(True,True),(False,True),(True,False)])
def test_zhiti_received_damage_restores_only_for_wounded_source_in_actual_range(wounded,in_range):
    s=game();s.state.players['p1'].abolished_equipment_slots={EquipmentSlot.ARMOR}
    source='p2' if in_range else 'p3'
    if wounded:s.state.players[source].hp-=1
    s.engine.start_action(MilitaryDamageAction('damage',source,'p1',1))
    if wounded and in_range:
        s=restore(s);assert '止啼' in s.engine.pending_request.prompt;answer(s,'armor')
        assert not s.state.players['p1'].abolished_equipment_slots
    else:assert s.engine.pending_request is None and EquipmentSlot.ARMOR in s.state.players['p1'].abolished_equipment_slots


@pytest.mark.parametrize('win',[True,False])
def test_zhiti_pindian_victory_restores_one_slot_and_tie_does_not(win):
    s=game();s.state.players['p1'].abolished_equipment_slots={EquipmentSlot.WEAPON,EquipmentSlot.ARMOR};s.state.players['p2'].hp=2
    a=put(s,'basic.slash');b=put(s,'basic.dodge','p2')
    s.state.cards[a]=replace(s.state.cards[a],rank=12 if win else 7);s.state.cards[b]=replace(s.state.cards[b],rank=3 if win else 7)
    s.engine.start_action(PindianAction('compare','p1','p2'));answer(s,a);answer(s,b)
    if win:
        s=restore(s);answer(s,'weapon');assert s.state.players['p1'].abolished_equipment_slots=={EquipmentSlot.ARMOR}
    else:assert s.engine.pending_request is None


@pytest.mark.parametrize('god_target',[True,False])
def test_zhiti_duel_victory_both_sides_uses_result_after_response_not_any_damage(god_target):
    s=game();s.state.players['p1'].abolished_equipment_slots={EquipmentSlot.ARMOR};s.state.players['p2'].hp=3
    if god_target:
        c=put(s,'trick.duel','p2');slash=put(s,'basic.slash');s.state.current_player_id='p2'
        from sanguosha.model.usage import PlayUsageState
        s.state.play_usage=PlayUsageState('p2',4)
        s.engine.start_action(UseCardAction('duel','p2',c,('p1',)))
        while s.engine.pending_request.required_definition_id=='trick.nullification':answer(s,PASS_RESPONSE)
        answer(s,slash);answer(s,PASS_RESPONSE)
    else:
        c=put(s,'trick.duel');s.engine.start_action(UseCardAction('duel','p1',c,('p2',)))
        while s.engine.pending_request.required_definition_id=='trick.nullification':answer(s,PASS_RESPONSE)
        answer(s,PASS_RESPONSE)
        assert '夺锐' in s.engine.pending_request.prompt;answer(s,False)
    s=restore(s);assert '止啼' in s.engine.pending_request.prompt;answer(s,'armor')
    assert not s.state.players['p1'].abolished_equipment_slots


def test_zhiti_hand_penalty_uses_weapon_range_and_projection_exposes_abolished_slots():
    s=game();s.state.players['p1'].abolished_equipment_slots={EquipmentSlot.ARMOR}
    put(s,'equipment.weapon.serpent_spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    for q in ('p2','p3'):s.state.players[q].hp-=1
    limit=FireHandLimit(WindHandLimit(),s.skills,s.definitions)
    assert limit(s.state,'p2')==s.state.players['p2'].hp-1
    assert limit(s.state,'p3')==s.state.players['p3'].hp-1
    s.state.players['p1'].disabled_skills.add('zhiti');assert limit(s.state,'p3')==s.state.players['p3'].hp
    view=project_for_human(s.state,s.definitions,'p2',{})
    assert next(p for p in view.players if p.player_id=='p1').abolished_equipment_slots==('armor',)


def test_abolished_slots_survive_json_projection_roundtrip_and_legacy_default():
    import json
    from sanguosha.multiplayer.protocol import serialize_projection,deserialize_projection
    s=game();s.state.players['p1'].abolished_equipment_slots={EquipmentSlot.WEAPON}
    view=project_for_human(s.state,s.definitions,'p2',{})
    payload=json.loads(json.dumps(serialize_projection(view),ensure_ascii=False))
    assert deserialize_projection(payload)==view
    for p in payload['players']:p.pop('abolished_equipment_slots')
    assert all(p.abolished_equipment_slots==() for p in deserialize_projection(payload).players)

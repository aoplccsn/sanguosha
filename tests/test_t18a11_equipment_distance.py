"""Shared equipment, geometry and slot lifecycle conformance regressions."""
from dataclasses import replace
import pytest
from test_t18a11_judgment_system import game
from test_t17c_first_batch import restore
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.military_basics import MilitaryStrike,MilitaryDamageAction
from sanguosha.engine.military_equipment import WeaponChoice
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.card_moves import CardMove,CardMoveReason
from sanguosha.engine.requests import RequestType
from sanguosha.model.enums import EquipmentSlot,DamageNature,Suit
from sanguosha.model.zones import ZoneRef,ZoneType


def gear(s,key,pid='p1',slot=EquipmentSlot.WEAPON):
 return put(s,'equipment.'+key,pid,ZoneType.EQUIPMENT,slot)


def test_axe_does_not_offer_when_only_cost_is_itself_plus_one_card():
 s=game();axe=gear(s,'weapon.rock_cleaving_axe');put(s,'basic.peach')
 # Remove other owner hand cards to make the two-cost boundary exact.
 hand=ZoneRef(ZoneType.HAND,'p1')
 keep=s.state.cards_in(hand)[-1]
 moves=s.engine.reaction_provider.__self__
 rest=tuple(c for c in s.state.cards_in(hand) if c!=keep)
 if rest:moves.move(s.state,CardMove('audit-empty',rest,hand,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
 slash=put(s,'basic.slash','p3');dodge=put(s,'basic.dodge','p2')
 s.engine.start_action(MilitaryStrike('audit-axe','p1','p2',slash,'basic.dodge'));answer(s,dodge)
 assert s.engine.pending_request is None
 assert axe in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON))


def test_axe_cost_request_excludes_equipped_axe():
 s=game();axe=gear(s,'weapon.rock_cleaving_axe');slash=put(s,'basic.slash');dodge=put(s,'basic.dodge','p2')
 s.engine.start_action(MilitaryStrike('audit-axe-material','p1','p2',slash,'basic.dodge'));answer(s,dodge);answer(s,True)
 assert axe not in s.engine.pending_request.eligible_card_ids


def test_kylin_choice_precedes_hp_and_damage_reactions():
 s=game();gear(s,'weapon.kylin_bow');gear(s,'horse.chitu','p2',EquipmentSlot.OFFENSIVE_HORSE)
 slash=put(s,'basic.slash');hp=s.state.players['p2'].hp
 s.engine.start_action(MilitaryStrike('audit-kylin','p1','p2',slash,'basic.dodge'));answer(s,s.engine.pending_request.timeout_value())
 assert s.engine.pending_request.request_id.endswith(':kylin')
 assert s.state.players['p2'].hp==hp
 s=restore(s);answer(s,True);horse=s.engine.pending_request.eligible_card_ids[0];answer(s,(horse,));finish(s)
 assert s.state.players['p2'].hp==hp-1


def test_kylin_lethal_hit_still_offers_before_death():
 s=game();gear(s,'weapon.kylin_bow');gear(s,'horse.chitu','p2',EquipmentSlot.OFFENSIVE_HORSE)
 slash=put(s,'basic.slash');s.state.players['p2'].hp=1
 s.engine.start_action(MilitaryStrike('audit-kylin-lethal','p1','p2',slash,'basic.dodge'));answer(s,s.engine.pending_request.timeout_value())
 assert s.engine.pending_request.request_id.endswith(':kylin') and s.state.players['p2'].hp==1


def test_ice_sword_selects_second_card_after_first_move_reactions():
 s=game();s.state.players['p2'].granted_skills['xiaoji']='audit'
 # Target has only armor; losing it draws two new cards before the second discard.
 moves=s.engine.reaction_provider.__self__;hand=ZoneRef(ZoneType.HAND,'p2');cards=s.state.cards_in(hand)
 if cards:moves.move(s.state,CardMove('audit-empty-target',cards,hand,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
 armor=gear(s,'armor.vine','p2',EquipmentSlot.ARMOR)
 s.engine.start_action(WeaponChoice('audit-ice','p1','p2','ice_sword'))
 assert s.engine.pending_request.request_type is RequestType.CHOOSE_CARD
 answer(s,armor)
 assert s.engine.pending_request.request_type is RequestType.YES_NO
 answer(s,True);s=restore(s)
 assert s.engine.pending_request.request_type is RequestType.CHOOSE_CARD
 assert len(s.engine.pending_request.eligible_card_ids)==2
 answer(s,s.engine.pending_request.eligible_card_ids[0]);assert s.engine.pending_request is None


def test_equipment_replacement_waits_for_departure_reaction_before_install():
 s=game();s.state.players['p1'].granted_skills['xiaoji']='audit'
 old=gear(s,'armor.vine',slot=EquipmentSlot.ARMOR);new=put(s,'equipment.armor.eight_trigrams')
 s.engine.start_action(UseCardAction('audit-replace','p1',new))
 assert s.engine.pending_request.request_type is RequestType.YES_NO
 assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.ARMOR))
 assert new in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
 assert old in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
 s=restore(s);answer(s,False)
 assert s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.ARMOR))==(new,)
 s.state.__post_init__()



def test_qicai_ignores_supply_shortage_distance_but_not_duplicate():
 s=game();s.state.players['p1'].granted_skills['qicai']='audit'
 from sanguosha.engine.military_tricks import MilitaryTrickRule
 from sanguosha.engine.distance import DistanceSystem
 rule=MilitaryTrickRule('delayed.supply_shortage',DistanceSystem(s.definitions),s.skills)
 assert 'p3' in rule.target_candidates(s.state,'p1')
 put(s,'delayed.supply_shortage','p3',ZoneType.JUDGMENT)
 assert 'p3' not in rule.target_candidates(s.state,'p1')


def test_qiangxi_weapon_cost_preserves_independent_attack_range_modifier():
 from sanguosha.engine.fire import QiangxiHandler
 s=game();weapon=gear(s,'weapon.serpent_spear');s.state.players['p1'].marks['yj_gongqi']=s.state.turn_number
 h=QiangxiHandler(s.skills,s.engine.reaction_provider.__self__,s.definitions)
 assert 'p3' in h.targets(s.state,'p1',weapon)



def test_qinggang_target_binding_survives_weapon_stolen_by_first_target():
 s=game();s.state.players['p1'].marks['slash_extra_targets']=1;s.state.players['p2'].granted_skills['fankui']='audit'
 sword=gear(s,'weapon.qinggang_sword');gear(s,'armor.vine','p3',EquipmentSlot.ARMOR)
 slash=put(s,'basic.slash');hp=s.state.players['p3'].hp
 s.engine.start_action(UseCardAction('audit-qinggang-binding','p1',slash,('p2','p3')))
 while s.engine.pending_request:
  r=s.engine.pending_request
  if r.request_id.endswith(':fankui'):answer(s,True)
  elif r.request_id.endswith(':fankui-card'):answer(s,sword)
  else:answer(s,r.timeout_value())
 assert sword in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
 assert s.state.players['p3'].hp==hp-1



@pytest.mark.parametrize('horse,slot', [('chitu',EquipmentSlot.OFFENSIVE_HORSE),('jueying',EquipmentSlot.DEFENSIVE_HORSE)])
def test_hand_horse_projection_exposes_slot_for_signed_face(horse,slot):
 from sanguosha.projection import project_for_human
 s=game();cid=put(s,'equipment.horse.'+horse)
 card=next(c for c in project_for_human(s.state,s.definitions,'p1',{}).hand if c.card_id==cid)
 assert card.equipment_slot==slot.value



@pytest.mark.parametrize('mode',['military-five','military-eight'])
def test_all_living_seat_distances_and_death_compression(mode):
 from sanguosha.session import GameSession
 from sanguosha.engine.distance import DistanceSystem
 from sanguosha.model.enums import PlayerStatus
 s=GameSession.new_game(military=True,five_generals=True,mode_id=mode)
 for p in s.state.players.values():p.character_id='caocao'
 distance=DistanceSystem(s.definitions)
 for dead in (False,True):
  if dead:s.state.players['p2'].status=PlayerStatus.DEAD
  alive=tuple(q for q in s.state.seat_order if s.state.players[q].is_alive)
  for i,a in enumerate(alive):
   for j,b in enumerate(alive):
    if a!=b:assert distance.base_distance(s.state,a,b)==min(abs(i-j),len(alive)-abs(i-j))


@pytest.mark.parametrize('key,name,radius',__import__('sanguosha.content.cards.classic_military',fromlist=['WEAPONS']).WEAPONS)
def test_every_registered_weapon_range_and_departure(key,name,radius):
 from sanguosha.engine.distance import DistanceSystem
 s=game();cid=gear(s,'weapon.'+key);distance=DistanceSystem(s.definitions)
 assert distance.attack_range(s.state,'p1')==radius
 s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-remove',(cid,),ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON),ZoneRef(ZoneType.HAND,'p2'),CardMoveReason.SYSTEM))
 assert distance.attack_range(s.state,'p1')==1
 s=restore(s);assert distance.attack_range(s.state,'p1')==1;s.state.__post_init__()


def test_distance_horses_skill_modifiers_fixed_distance_and_suppression():
 from sanguosha.engine.distance import DistanceSystem
 from sanguosha.engine.skill_grants import add_grant,remove_grant
 s=game();d=DistanceSystem(s.definitions)
 assert d.distance_between(s.state,'p1','p3')==2
 gear(s,'horse.chitu',slot=EquipmentSlot.OFFENSIVE_HORSE);gear(s,'horse.jueying','p3',EquipmentSlot.DEFENSIVE_HORSE)
 assert d.distance_between(s.state,'p1','p3')==2 and d.attack_range(s.state,'p1')==1
 add_grant(s.state,'p1','mashu','audit-a');add_grant(s.state,'p1','mashu','audit-b')
 assert d.distance_between(s.state,'p1','p3')==1
 remove_grant(s.state,'p1','mashu','audit-a');assert d.distance_between(s.state,'p1','p3')==1
 add_grant(s.state,'p3','feiying','audit')
 assert d.distance_between(s.state,'p1','p3')==2
 s.state.players['p1'].disabled_skills.add('mashu');assert d.distance_between(s.state,'p1','p3')==3
 s.state.metadata['zhuikong_distance']={'audit':{'source':'p1','target':'p3','turn':s.state.turn_number}}
 assert d.distance_between(s.state,'p1','p3')==1
 s=restore(s);assert d.distance_between(s.state,'p1','p3')==1


@pytest.mark.parametrize('slot,key',[(EquipmentSlot.WEAPON,'weapon.kylin_bow'),(EquipmentSlot.ARMOR,'armor.silver_lion'),(EquipmentSlot.OFFENSIVE_HORSE,'horse.chitu'),(EquipmentSlot.DEFENSIVE_HORSE,'horse.jueying')])
def test_duorui_each_slot_actual_abolish_restore_and_public_geometry(slot,key):
 from test_t17c_zhangliao import game as zhangliao
 from sanguosha.engine.remaining_gods import RemainingGodAction
 from sanguosha.engine.card_rules import InvalidCardUse
 from sanguosha.engine.distance import DistanceSystem
 from sanguosha.projection import project_for_human
 s=zhangliao();cid=gear(s,key,slot=slot);d=DistanceSystem(s.definitions)
 s.engine.start_action(RemainingGodAction('audit-slot','p1','duorui','p2'));answer(s,True);answer(s,slot.value)
 assert slot in s.state.players['p1'].abolished_equipment_slots
 assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p1',slot))
 assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
 s=restore(s);answer(s,'wusheng')
 assert d.attack_range(s.state,'p1')==1 and d.distance_between(s.state,'p1','p3')==2
 assert d.distance_between(s.state,'p3','p1')==2
 views=[project_for_human(s.state,s.definitions,q,{}) for q in s.state.seat_order]
 own=[next(p for p in v.players if p.player_id=='p1') for v in views]
 assert all(p.abolished_equipment_slots==(slot.value,) and not p.equipment for p in own)
 new=put(s,'equipment.'+key)
 with pytest.raises(InvalidCardUse):s.engine.start_action(UseCardAction('audit-slot-equip','p1',new))
 assert new in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
 s.engine.start_action(RemainingGodAction('audit-enable','p1','zhiti_restore','p2'));s=restore(s);answer(s,slot.value)
 assert not s.state.players['p1'].abolished_equipment_slots
 s.engine.start_action(UseCardAction('audit-slot-enabled','p1',new));finish(s)
 assert new in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p1',slot));s.state.__post_init__()


def test_crossbow_live_permission_loss_preserves_native_paoxiao():
 from sanguosha.engine.military_basics import SkillSlashLimit
 s=game();cid=gear(s,'weapon.crossbow');s.state.play_usage.record('basic.slash')
 limit=SkillSlashLimit(s.skills)
 assert limit.limit(s.state,'p1') is None
 s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-crossbow-out',(cid,),ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON),ZoneRef(ZoneType.HAND,'p2'),CardMoveReason.SYSTEM))
 assert limit.limit(s.state,'p1')==1
 s.state.players['p1'].character_id='zhangfei';s=restore(s)
 assert limit.limit(s.state,'p1') is None



@pytest.mark.parametrize('character',[c.id for c in __import__('sanguosha.content.characters.standard',fromlist=['ALL_GENERAL_POOL']).ALL_GENERAL_POOL if 'mashu' in c.skill_ids])
def test_each_native_mashu_direction_and_lease_expiration(character):
 from sanguosha.engine.distance import DistanceSystem
 from sanguosha.engine.skill_leases import begin_lease,expire_target
 s=game();s.state.players['p1'].character_id=character;d=DistanceSystem(s.definitions)
 assert s.skills.has(s.state,'p1','mashu')
 assert d.distance_between(s.state,'p1','p3')==1 and d.distance_between(s.state,'p3','p1')==2
 begin_lease(s.state,'p2','p1','mashu')
 assert d.distance_between(s.state,'p1','p3')==2 and d.distance_between(s.state,'p2','p4')==1
 s=restore(s);expire_target(s.state,'p1');assert d.distance_between(s.state,'p1','p3')==1
 s.state.players['p1'].disabled_skills.add('mashu');assert d.distance_between(s.state,'p1','p3')==2


def test_native_feiying_only_incoming_and_disabled_context():
 from sanguosha.engine.distance import DistanceSystem
 s=game();s.state.players['p3'].character_id='forest_god_caocao';d=DistanceSystem(s.definitions)
 assert s.skills.has(s.state,'p3','feiying')
 assert d.distance_between(s.state,'p1','p3')==3 and d.distance_between(s.state,'p3','p1')==2
 s=restore(s);s.state.players['p3'].disabled_skills.add('feiying')
 assert d.distance_between(s.state,'p1','p3')==2


@pytest.mark.parametrize('definition',['trick.snatch','delayed.supply_shortage'])
def test_qicai_distance_permission_does_not_apply_to_slash_and_expires_when_disabled(definition):
 from sanguosha.engine.military_tricks import MilitaryTrickRule
 from sanguosha.engine.distance import DistanceSystem
 s=game();put(s,'basic.slash','p3');d=DistanceSystem(s.definitions)
 rule=MilitaryTrickRule(definition,d,s.skills)
 assert 'p3' not in rule.target_candidates(s.state,'p1')
 s.state.players['p1'].granted_skills['qicai']='audit';assert 'p3' in rule.target_candidates(s.state,'p1')
 assert not d.can_reach_with_slash(s.state,'p1','p3')
 s=restore(s);s.state.players['p1'].disabled_skills.add('qicai')
 assert 'p3' not in rule.target_candidates(s.state,'p1')



@pytest.mark.parametrize('corruption',['capacity','abolished'])
def test_invalid_equipment_snapshot_is_rejected(corruption):
 s=game();gear(s,'weapon.crossbow');ref=ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON)
 if corruption=='capacity':gear(s,'weapon.kylin_bow','p2');other=ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.WEAPON);cid=s.state.zones[other].card_ids.pop();s.state.zones[ref].card_ids.append(cid)
 else:s.state.players['p1'].abolished_equipment_slots.add(EquipmentSlot.WEAPON)
 with pytest.raises(ValueError):s.state.__post_init__()


def test_ai_play_request_uses_legal_range_and_abolished_slot():
 from sanguosha.engine.phases import PhaseAction
 from sanguosha.model.enums import Phase
 s=game();slash=put(s,'basic.slash');forbidden=put(s,'equipment.weapon.kylin_bow')
 s.state.players['p1'].abolished_equipment_slots.add(EquipmentSlot.WEAPON)
 s.engine.start_action(PhaseAction('audit-ai-play','p1',Phase.PLAY))
 r=s.engine.pending_request
 assert 'use:'+forbidden not in r.choices
 targets=r.play_card_targets['use:'+slash][0]
 assert set(targets)=={'p2','p5'}
 decision=s.ai.decide(s.state,r)
 option=decision.value['option'] if isinstance(decision.value,dict) else decision.value
 assert option in r.choices and option!='use:'+forbidden
 s=restore(s);assert s.engine.pending_request.play_card_targets['use:'+slash][0]==targets


def test_ai_equipment_value_uses_horse_distance_and_replacement():
 s=game();s.state.revealed_identities.add('p3')
 from sanguosha.model.enums import Identity
 s.state.players['p1'].identity=Identity.LORD;s.state.players['p3'].identity=Identity.REBEL
 before=s.ai._equipment_quality(s.state,'p1','equipment.weapon.crossbow')[1]
 gear(s,'horse.chitu',slot=EquipmentSlot.OFFENSIVE_HORSE)
 after=s.ai._equipment_quality(s.state,'p1','equipment.weapon.crossbow')[1]
 assert after>before
 gear(s,'weapon.kylin_bow')
 assert s.ai._action_priority(s.state,'p1','equipment.weapon.double_sword',['p3'])<0
 assert s.ai._equipment_quality(s.state,'p1','equipment.armor.eight_trigrams')[1]>0



@pytest.mark.parametrize('virtual',[False,True])
def test_green_dragon_followup_is_use_with_materials_on_table_until_jianxiong(virtual):
 from sanguosha.engine.events import CardUsedEvent
 s=game();gear(s,'weapon.green_dragon_blade');s.state.players['p2'].granted_skills['jianxiong']='audit'
 first=put(s,'basic.slash');dodge=put(s,'basic.dodge','p2')
 follow=put(s,'basic.peach' if virtual else 'basic.fire_slash');s.state.cards[follow]=replace(s.state.cards[follow],suit=Suit.HEART)
 if virtual:s.state.players['p1'].granted_skills['wusheng']='audit'
 s.engine.start_action(UseCardAction('audit-green-use','p1',first,('p2',)));answer(s,dodge)
 answer(s,'virtual:wusheng:'+follow if virtual else follow)
 answer(s,s.engine.pending_request.timeout_value())
 assert s.engine.pending_request is not None and s.engine.pending_request.request_id.endswith(':jianxiong')
 assert follow in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
 uses=[e for e in s.events.events if isinstance(e,CardUsedEvent) and e.card_id==follow]
 assert len(uses)==1 and not uses[0].slash_counted
 s=restore(s);answer(s,True)
 assert follow in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
 assert s.state.play_usage.count('basic.slash')==1
 s.state.__post_init__()



def test_green_dragon_alliance_supplied_material_preserves_provider_and_use_owner():
 from sanguosha.engine.events import CardUsedEvent
 s=game();gear(s,'weapon.green_dragon_blade');s.state.players['p1'].granted_skills['jijiang']='audit'
 s.state.players['p3'].character_id='guanyu';s.state.players['p2'].granted_skills['jianxiong']='audit'
 first=put(s,'basic.slash');dodge=put(s,'basic.dodge','p2');follow=put(s,'basic.fire_slash','p3')
 s.engine.start_action(UseCardAction('audit-green-alliance','p1',first,('p2',)));answer(s,dodge)
 answer(s,'virtual:jijiang');assert s.engine.pending_request.player_id=='p3'
 answer(s,follow);answer(s,s.engine.pending_request.timeout_value())
 assert s.engine.pending_request.request_id.endswith(':jianxiong')
 event=next(e for e in s.events.events if isinstance(e,CardUsedEvent) and e.card_id==follow)
 assert event.player_id=='p1' and follow in s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
 s=restore(s);answer(s,True);assert follow in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))



def test_green_dragon_cannot_follow_up_against_newly_empty_kongcheng():
 s=game();gear(s,'weapon.green_dragon_blade');s.state.players['p2'].granted_skills['kongcheng']='audit'
 hand=ZoneRef(ZoneType.HAND,'p2');old=s.state.cards_in(hand)
 if old:s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-clear-kongcheng',old,hand,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
 dodge=put(s,'basic.dodge','p2');slash=put(s,'basic.slash');put(s,'basic.slash')
 s.engine.start_action(UseCardAction('audit-green-kongcheng','p1',slash,('p2',)));answer(s,dodge)
 assert s.engine.pending_request is None

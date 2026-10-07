"""T20.2 requested strategic decisions, with only own cards/public facts."""
from dataclasses import replace
import pytest
from test_t18a10_ai import game,request,ai
from test_t6_military_basics import put
from sanguosha.engine.requests import RequestType,PASS_RESPONSE
from sanguosha.model.enums import Identity,EquipmentSlot,Suit
from sanguosha.model.zones import ZoneType,ZoneRef
from sanguosha.decisions import strategy
from sanguosha.engine.events import Event,CardRespondedEvent,HpRecoveredEvent

def scenario(role=Identity.REBEL):
 s=game();s.state.revealed_identities.clear();s.state.revealed_identities.add('p2')
 s.state.players['p1'].identity=role;s.state.players['p2'].identity=Identity.LORD
 for p in s.state.players.values(): p.character_id='machao';p.hp=4;p.max_hp=4
 return s

def response(s,definition,target):
 c=put(s,definition)
 r=request(RequestType.RESPOND_WITH_CARD,required_definition_id=definition,eligible_card_ids=(c,),subject_player_id=target,allow_pass=True)
 return c,r

def test_loyalist_saves_dying_lord():
 s=scenario(Identity.LOYALIST);s.state.players['p2'].hp=0;c,r=response(s,'basic.peach','p2')
 assert ai().decide(s.state,r).value==c

def test_public_team_saves_teammate():
 from sanguosha.pregame import Pregame
 from sanguosha.session import GameSession
 s=GameSession.new_game(seed=20,military=True,five_generals=True,mode_id='team-2v2')
 s.state.players['p3'].hp=0;c,r=response(s,'basic.peach','p3')
 assert ai().decide(s.state,r).value==c

def test_killable_key_enemy_over_safe_lord():
 s=scenario();s.state.metadata['public_attitude']={'p3':{'p2':4}}
 s.state.players['p3'].character_id='mobile_god_xunyu';s.state.players['p3'].hp=1
 r=request(RequestType.CHOOSE_PLAYER,allowed_player_ids=('p2','p3'))
 assert ai().decide(s.state,r).value=='p3'

def test_aoe_rejects_own_side_casualties():
 s=scenario(Identity.LOYALIST);s.state.players['p2'].hp=1
 s.state.metadata['public_attitude']={q:{'p2':5} for q in ('p3','p4','p5')}
 assert ai()._action_priority(s.state,'p1','trick.archery_attack',[])<0

def test_remove_enemy_eight_trigrams_without_reading_hidden_hand():
 s=scenario(Identity.LOYALIST);s.state.metadata['public_attitude']={'p3':{'p2':-5}}
 armor=put(s,'equipment.armor.eight_trigrams','p3',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
 hidden=put(s,'basic.peach','p3')
 r=replace(request(RequestType.CHOOSE_CARD,eligible_card_ids=(hidden,armor),subject_player_id='p3'),prompt='过河拆桥：选择目标区域的一张牌')
 assert ai().decide(s.state,r).value==armor

def test_enemy_hurts_enemy_not_countered():
 s=scenario(Identity.LOYALIST);s.state.metadata['public_attitude']={'p3':{'p2':-5},'p4':{'p2':-5}}
 c,r=response(s,'trick.nullification','p3')
 assert ai().decide(s.state,r,response_context={'current_target_id':'p3','source_id':'p4','definition_id':'trick.duel','cancelled':False}).value is PASS_RESPONSE

def test_low_value_damage_discount_for_masochism():
 s=scenario(Identity.LOYALIST);s.state.metadata['public_attitude']={'p3':{'p2':-5},'p4':{'p2':-5}}
 s.state.players['p3'].character_id='guojia'
 assert ai()._target_score(s.state,'p1','p3')<ai()._target_score(s.state,'p1','p4')

def test_rebel_can_conceal_low_value_lord_attack():
 s=scenario();c=put(s,'basic.slash')
 r=request(RequestType.CHOOSE_OPTION,choices=('use:'+c,'end_play_phase'),play_card_targets={'use:'+c:(('p2',),1,1)})
 assert ai().decide(s.state,r).value=='end_play_phase'

def test_rebel_never_conceals_direct_lord_kill():
 s=scenario();s.state.players['p2'].hp=1;c=put(s,'basic.slash')
 r=request(RequestType.CHOOSE_OPTION,choices=('use:'+c,'end_play_phase'),play_card_targets={'use:'+c:(('p2',),1,1)})
 assert ai().decide(s.state,r).value=='use:'+c

def test_renegade_changes_side_with_public_strength():
 s=scenario(Identity.RENEGADE);s.state.metadata['public_attitude']={'p3':{'p2':5},'p4':{'p2':-5},'p5':{'p2':-5}}
 s.state.players['p4'].hp=s.state.players['p5'].hp=1
 before=ai()._priority(s.state,'p1','p3')
 s.state.players['p4'].hp=s.state.players['p5'].hp=8
 s.state.players['p2'].hp=s.state.players['p3'].hp=1
 assert ai()._priority(s.state,'p1','p3')<before
 assert ai()._priority(s.state,'p1','p4')>ai()._priority(s.state,'p1','p3')

def test_simayi_near_awakening_preserves_scarce_safe_response():
 s=scenario();p=s.state.players['p1'];p.character_id='mountain_god_simayi';p.marks['ren']=3;p.hp=4
 c,r=response(s,'basic.dodge','p1')
 # All existing own cards become cheap Slash so this is the only Dodge.
 for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')):
  if cid!=c:s.state.cards[cid]=replace(s.state.cards[cid],definition_id='basic.slash')
 assert ai().decide(s.state,r).value is PASS_RESPONSE
 p.hp=1
 assert ai().decide(s.state,r).value==c

def test_simayi_actual_decline_grows_fourth_ren_but_defense_does_not():
 from sanguosha.engine.response import RespondWithCardAction
 from sanguosha.engine.requests import Decision
 s=scenario();p=s.state.players['p1'];p.character_id='mountain_god_simayi';p.marks['ren']=3;p.hp=4
 c=put(s,'basic.dodge');s.engine.start_action(RespondWithCardAction('t202','p1','basic.dodge','slash',card_source_id='p2'))
 assert p.marks['ren']==3
 for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')):
  if cid!=c:s.state.cards[cid]=replace(s.state.cards[cid],definition_id='basic.slash')
 d=ai().decide(s.state,s.engine.pending_request);assert d.value is PASS_RESPONSE
 s.engine.submit_decision(d);assert p.marks['ren']==4
 p.marks['ren']=3;p.hp=1
 s.engine.start_action(RespondWithCardAction('t202-defend','p1','basic.dodge','slash',card_source_id='p2'))
 d=ai().decide(s.state,s.engine.pending_request);assert d.value==c
 s.engine.submit_decision(d);assert p.marks['ren']==3

def test_jilue_and_lianpo_choose_for_board():
 s=scenario();c=put(s,'basic.slash');s.state.players['p2'].hp=1
 r=replace(request(RequestType.CHOOSE_OPTION,choices=('learn:jizhi','learn:wansha','learn:zhiheng')),prompt='极略：选择')
 assert ai().decide(s.state,r).value=='learn:wansha'
 for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')):s.state.cards[cid]=replace(s.state.cards[cid],definition_id='trick.ex_nihilo')
 r=replace(r,prompt='连破：选择',choices=('extra_turn','learn:jizhi'))
 assert ai().decide(s.state,r).value=='learn:jizhi'

def test_core_teammate_gets_resources_and_own_skill_keeps_material():
 s=scenario(Identity.LOYALIST);s.state.metadata['public_attitude']={'p3':{'p2':5},'p4':{'p2':5}}
 s.state.players['p3'].character_id='mobile_god_taishici';s.state.players['p3'].granted_skills['shenzhu']={'test'}
 r=replace(request(RequestType.CHOOSE_PLAYER,allowed_player_ids=('p3','p4')),prompt='仁德：请选择角色')
 assert ai().decide(s.state,r).value=='p3'
 s.state.players['p1'].character_id='guanyu';red=put(s,'basic.slash');black=put(s,'basic.slash')
 s.state.cards[red]=replace(s.state.cards[red],suit=Suit.HEART);s.state.cards[black]=replace(s.state.cards[black],suit=Suit.SPADE)
 r=request(RequestType.CHOOSE_CARDS,eligible_card_ids=(red,black),min_count=1,max_count=1)
 assert ai().decide(s.state,r).value==(black,)

def test_hidden_faces_and_identities_cannot_change_scores():
 s=scenario(Identity.LOYALIST);s.state.metadata['public_attitude']={'p3':{'p2':-5}}
 put(s,'equipment.weapon.crossbow','p3',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
 before=ai()._target_score(s.state,'p1','p3');equipment=ai()._equipment_quality(s.state,'p3','equipment.weapon.crossbow',observer='p1')
 s.state.players['p3'].identity=Identity.LOYALIST
 for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')):s.state.cards[cid]=replace(s.state.cards[cid],definition_id='basic.slash')
 assert ai()._target_score(s.state,'p1','p3')==before
 assert ai()._equipment_quality(s.state,'p3','equipment.weapon.crossbow',observer='p1')==equipment

def test_public_counters_and_rescue_update_belief():
 s=scenario();c=put(s,'trick.nullification','p3')
 events=[Event('duel:current:1','effect_target','p4',('p2',),{'definition_id':'trick.duel'}),CardRespondedEvent('counter','p3',c,'duel:window:1','trick.nullification')]
 ai().observe_public_events(s.state,events)
 assert strategy.belief(s.state,'p3')>0
 events.append(CardRespondedEvent('counter2','p4',c,'duel:window:1','trick.nullification'))
 ai().observe_public_events(s.state,events);assert strategy.belief(s.state,'p4')<0

def test_identity_match_supplies_actual_public_counter_context():
 from sanguosha.engine.military_tricks import TrickAction
 s=scenario(Identity.LOYALIST);c=put(s,'trick.duel');put(s,'trick.nullification')
 s.engine.start_action(TrickAction('t202-trick','p1',c,'trick.duel',('p2',)))
 context=s.ai_response_context()
 assert context and context['current_target_id']=='p2' and context['definition_id']=='trick.duel'

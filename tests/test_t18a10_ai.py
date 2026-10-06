from dataclasses import replace
import pytest
from sanguosha.decisions.ai import AIDecisionProvider
from sanguosha.engine.requests import PendingRequest,RequestType,PASS_RESPONSE
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.skills import SkillRegistry
from sanguosha.model.enums import Identity,EquipmentSlot,Phase,Suit
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.snapshot import snapshot_session,restore_session
from test_t6_military_basics import put
from sanguosha.session import GameSession
from sanguosha.model.usage import PlayUsageState
def game():
 s=GameSession.new_game(military=True,five_generals=True);s.state.current_player_id='p1';s.state.current_phase=Phase.PLAY;s.state.turn_number=1;s.state.play_usage=PlayUsageState('p1',1);return s

def request(kind,**kwargs):return PendingRequest('r','p1',kind,'选择','a','f',**kwargs)
def ai():return AIDecisionProvider('none')

def test_attack_public_enemy_over_ally_without_hidden_identity_read():
 s=game();s.state.metadata['public_attitude']={'p2':{'p1':8},'p3':{'p1':-8}}
 r=request(RequestType.CHOOSE_PLAYER,allowed_player_ids=('p2','p3'))
 assert ai().decide(s.state,r).value=='p3'
 s.state.players['p2'].identity,s.state.players['p3'].identity=s.state.players['p3'].identity,s.state.players['p2'].identity
 assert ai().decide(s.state,r).value=='p3'

def test_dying_resource_and_discard_keeps_peach_dodge_counter():
 s=game();s.state.players['p1'].hp=1
 cards=tuple(put(s,d) for d in ('basic.slash','basic.peach','basic.dodge','trick.nullification','basic.wine'))
 r=request(RequestType.CHOOSE_CARDS,eligible_card_ids=cards,min_count=1,max_count=1)
 assert ai().decide(s.state,r).value==(cards[0],)
 assert ai()._card_value(s.state,'p1','basic.wine')>ai()._card_value(s.state,'p1','basic.slash')

def test_counter_critical_dying_friend_and_pass_enemy_protection():
 s=game();s.state.players['p2'].hp=1;s.state.metadata['public_attitude']={'p2':{'p1':8}}
 c=put(s,'trick.nullification');r=request(RequestType.RESPOND_WITH_CARD,required_definition_id='trick.nullification',eligible_card_ids=(c,),allow_pass=True)
 assert ai().decide(s.state,r,response_context={'current_target_id':'p2','definition_id':'trick.duel','cancelled':False}).value==c
 assert ai().decide(s.state,r,response_context={'current_target_id':'p2','definition_id':'trick.duel','cancelled':True}).value is PASS_RESPONSE

@pytest.mark.parametrize('verb',['过河拆桥','顺手牵羊'])
def test_removal_prefers_public_key_armor_and_ignores_hidden_faces(verb):
 s=game();hidden=put(s,'basic.peach','p2');armor=put(s,'equipment.armor.eight_trigrams','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
 r=replace(request(RequestType.CHOOSE_CARD,eligible_card_ids=(hidden,armor),subject_player_id='p2'),prompt=verb+'：选择目标区域的一张牌')
 assert ai().decide(s.state,r).value==armor
 s.state.cards[hidden]=replace(s.state.cards[hidden],definition_id='equipment.weapon.crossbow')
 assert ai().decide(s.state,r).value==armor

def test_fire_attack_reserves_last_peach_and_needs_suit_resources():
 s=game();s.state.players['p1'].hp=1;peach=put(s,'basic.peach')
 r=replace(request(RequestType.RESPOND_WITH_CARD,eligible_card_ids=(peach,),allow_pass=True),prompt='火攻：弃同花色')
 assert ai().decide(s.state,r).value is PASS_RESPONSE
 for cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')):s.state.cards[cid]=replace(s.state.cards[cid],definition_id='basic.peach')
 assert ai()._action_priority(s.state,'p1','trick.fire_attack',['p2'])<0

def test_chain_unchains_friend_and_chains_enemy():
 s=game();s.state.metadata['public_attitude']={'p2':{'p1':8},'p3':{'p1':-8}};s.state.players['p2'].chained=True
 r=replace(request(RequestType.CHOOSE_PLAYERS,allowed_player_ids=('p2','p3'),min_count=0,max_count=2),prompt='【铁索连环】请选择目标')
 assert ai().decide(s.state,r).value==('p2','p3')

def test_aoe_rejects_friendly_damage_and_uses_enemy_benefit():
 s=game();s.state.metadata['public_attitude']={q:{'p1':8} for q in s.state.seat_order if q!='p1'}
 assert ai()._action_priority(s.state,'p1','trick.archery_attack',[])<0
 s.state.metadata['public_attitude']={q:{'p1':-8} for q in s.state.seat_order if q!='p1'}
 assert ai()._action_priority(s.state,'p1','trick.archery_attack',['p2'])>0

@pytest.mark.parametrize('avatar,skill', [('ganning','qixi'),('guanyu','wusheng'),('zhaoyun','longdan'),('fire_wolong','huoji'),('fire_wolong','kanpo'),('fire_pang_tong','lianhuan'),('yj2012_guan_xing_zhang_bao','fuhun'),('shadow_god_liubei','longnu')])
def test_real_acquired_skill_registry_snapshot_and_loss(avatar,skill):
 s=game();p=s.state.players['p1'];p.character_id='mountain_zuoci';p.active_transformation=avatar;p.transformation_pool=[avatar];p.transformation_skill=skill
 assert s.skills.has(s.state,'p1',skill)
 restored=restore_session(snapshot_session(s));assert restored.skills.has(restored.state,'p1',skill)
 p.disabled_skills.add(skill);assert not s.skills.has(s.state,'p1',skill)
 p.disabled_skills.clear();p.active_transformation=None;assert not s.skills.has(s.state,'p1',skill)

def test_actual_qixi_options_restore_normal_play_after_avatar_change():
 s=game();p=s.state.players['p1'];p.character_id='mountain_zuoci';p.active_transformation='ganning';p.transformation_pool=['ganning'];p.transformation_skill='qixi'
 black=put(s,'basic.slash');s.state.cards[black]=replace(s.state.cards[black],suit=Suit.SPADE)
 s.engine.start_action(PhaseAction('play','p1',Phase.PLAY));r=s.engine.pending_request
 assert 'virtual:qixi:'+black in r.choices
 provider=s.engine.registry.handler_for(PhaseAction('unused','p1',Phase.PLAY)).bodies.body_for(Phase.PLAY).provider
 p.transformation_skill=None
 choices=provider.options(s.state,'p1')
 assert not any(c.startswith('virtual:qixi:') for c in choices)
 assert 'use:'+black in choices

"""Deterministic shared movement contracts and dependent reactions."""
from copy import deepcopy
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t6_military_basics import put
from sanguosha.engine.card_moves import CardMove,CardMoveReason,CardMoveService,InvalidCardMove
from sanguosha.engine.events import CardMovedEvent
from sanguosha.model.enums import EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType


def game():
 s=setup('xun_you')
 for p in s.state.players.values():p.character_id='caocao'
 s.state.metadata['reaction_event_cursor']=len(s.events.events)
 return s

@pytest.mark.parametrize('inactive',[False,True])
def test_tuntian_excludes_own_hand_equipment_relocation(inactive):
 s=game();s.state.players['p2'].granted_skills['tuntian']='audit'
 s.state.current_player_id='p2' if inactive else 'p1'
 if inactive:s.state.current_phase=None
 cid=put(s,'equipment.weapon.spear','p2');moves=s.engine.reaction_provider.__self__
 moves.move(s.state,CardMove('audit-own-equip',(cid,),ZoneRef(ZoneType.HAND,'p2'),ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.WEAPON),CardMoveReason.SYSTEM,'p2'))
 assert not moves.reactions
 s.state.__post_init__()


def test_tuntian_notactive_current_still_triggers_on_actual_loss():
 s=game();s.state.players['p2'].granted_skills['tuntian']='audit'
 s.state.current_player_id='p2';s.state.current_phase=None
 cid=put(s,'basic.slash','p2');moves=s.engine.reaction_provider.__self__
 moves.move(s.state,CardMove('audit-inactive-loss',(cid,),ZoneRef(ZoneType.HAND,'p2'),ZoneRef(ZoneType.HAND,'p3'),CardMoveReason.SYSTEM,'p3'))
 assert len(moves.reactions)==1


def test_obtain_validates_entire_multizone_batch_before_any_mutation():
 s=game();first=put(s,'basic.slash','p2');second=put(s,'equipment.weapon.spear','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
 s.state.zones[ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.WEAPON)].card_ids.append(second)
 before=deepcopy(s.state.zones);events=len(s.events.events)
 with pytest.raises(InvalidCardMove):s.engine.reaction_provider.__self__.obtain_cards(s.state,(first,second),'p1','p1','audit-atomic-obtain')
 assert s.state.zones==before and len(s.events.events)==events


def test_quan_count_updates_on_shared_move_and_death_cleanup():
 from sanguosha.engine.yj2012 import power_zone
 from sanguosha.engine.death import DeathAction
 s=game();cid=put(s,'basic.slash','p2');moves=s.engine.reaction_provider.__self__
 moves.move(s.state,CardMove('audit-quan-in',(cid,),ZoneRef(ZoneType.HAND,'p2'),power_zone('p2'),CardMoveReason.SYSTEM,'p2'))
 assert s.state.players['p2'].marks.get('quan')==1
 s=restore(s);s.engine.start_action(DeathAction('audit-quan-death','p2',None));finish(s)
 assert not s.state.cards_in(power_zone('p2')) and not s.state.players['p2'].marks.get('quan')
 s.state.__post_init__()


def test_xingshang_cross_zone_acquisition_is_one_enyuan_fact():
 from sanguosha.engine.forest import XingshangAction
 from sanguosha.model.enums import PlayerStatus
 s=game();s.state.players['p1'].granted_skills.update(xingshang='audit',enyuan='audit')
 s.state.players['p2'].status=PlayerStatus.DEAD
 hand=ZoneRef(ZoneType.HAND,'p2');old=s.state.cards_in(hand)
 if old:CardMoveService(s.events).move(s.state,CardMove('audit-clear',old,hand,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
 a=put(s,'basic.slash','p2');b=put(s,'equipment.weapon.spear','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
 s.state.metadata['reaction_event_cursor']=len(s.events.events)
 s.engine.start_action(XingshangAction('audit-inherit','p2'));s=restore(s);answer(s,True)
 facts=[e for e in s.events.events if getattr(e,'event_type','')=='cards_obtained' and e.source_id=='p1']
 assert len(facts)==1 and facts[0].metadata=={'from_player_id':'p2','count':2}
 assert {a,b}<=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))



def test_zongxuan_reserved_equipment_does_not_publish_duplicate_departure_trigger():
 from sanguosha.engine.zongxuan import PendingDiscard
 s=game();s.state.players['p1'].granted_skills.update(zongxuan='audit',xuanfeng='audit')
 cid=put(s,'equipment.weapon.spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
 moves=s.engine.reaction_provider.__self__
 moves.move(s.state,CardMove('audit-reserved-equipment',(cid,),ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,'p1'))
 pending=moves.next_reaction(s.state);assert isinstance(pending,PendingDiscard)
 assert not any(type(a).__name__=='XuanfengAction' for a in moves.reactions)
 s.engine.start_action(pending);s=restore(s);answer(s,())
 frames=s.engine.stack.snapshot()
 assert sum(type(f.action).__name__=='XuanfengAction' for f in frames)==1
 queued=s.engine.reaction_provider.__self__.reactions
 assert not any(type(a).__name__=='XuanfengAction' for a in queued)



def test_xingshang_acquires_hand_equipment_only_leaves_judgment_and_private_piles():
 from sanguosha.engine.death import DeathAction
 s=game();s.state.players['p1'].granted_skills['xingshang']='audit'
 judgment=put(s,'delayed.indulgence','p2',ZoneType.JUDGMENT)
 special=put(s,'basic.slash','p2');moves=s.engine.reaction_provider.__self__
 moves.move(s.state,CardMove('audit-private-in',(special,),ZoneRef(ZoneType.HAND,'p2'),ZoneRef(ZoneType.SPECIAL,'p2',special_key='quan'),CardMoveReason.SYSTEM))
 s.engine.start_action(DeathAction('audit-inherit-limits','p2',None));s=restore(s);answer(s,True);finish(s)
 assert judgment not in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
 assert {judgment,special}<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
 s.state.__post_init__()


@pytest.mark.parametrize('pile',['quan','counter','tian','wine','buqu','star','committed:audit'])
def test_all_pile_storage_conservation_restore_visibility_and_death(pile):
 from sanguosha.engine.death import DeathAction
 from sanguosha.projection import project_for_human
 from sanguosha.multiplayer.room import MultiplayerRoom
 s=game();cid=put(s,'basic.slash','p2');moves=s.engine.reaction_provider.__self__
 ref=ZoneRef(ZoneType.SPECIAL,'p2',special_key=pile)
 moves.move(s.state,CardMove('audit-pile-in-'+pile,(cid,),ZoneRef(ZoneType.HAND,'p2'),ref,CardMoveReason.SYSTEM))
 s.state.__post_init__();s=restore(s);s.state.__post_init__()
 own=next(p for p in project_for_human(s.state,s.definitions,'p2',{}).players if p.player_id=='p2')
 other=next(p for p in project_for_human(s.state,s.definitions,'p1',{}).players if p.player_id=='p2')
 assert own.special_piles[pile][0].card_id==cid
 private=pile=='star' or pile.startswith('committed:')
 assert (other.special_piles[pile][0].definition_id=='')==private
 room=MultiplayerRoom();room.session=s
 e=next(e for e in s.events.events if isinstance(e,CardMovedEvent) and e.event_id=='audit-pile-in-'+pile)
 assert room._public_event(e) is None
 s.engine.start_action(DeathAction('audit-pile-clean-'+pile,'p2',None));finish(s)
 assert not s.state.cards_in(ref) and cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
 s.state.__post_init__();s=restore(s);s.state.__post_init__()

@pytest.mark.parametrize('destination',[ZoneRef(ZoneType.DISCARD_PILE),ZoneRef(ZoneType.HAND,'p1')])
def test_hidden_hand_removal_choice_then_public_discard_or_private_obtain(destination):
 from sanguosha.multiplayer.room import MultiplayerRoom
 from sanguosha.multiplayer.choice_labels import choice_labels
 from sanguosha.engine.requests import PendingRequest,RequestType
 from sanguosha.projection import project_for_human
 s=game();cid=put(s,'basic.peach','p2');room=MultiplayerRoom();room.session=s
 request=PendingRequest('audit-choice','p1',RequestType.CHOOSE_CARD,'select', 'a','f',eligible_card_ids=(cid,),subject_player_id='p2')
 labels=choice_labels(room,request)
 assert not any('Peach' in str(v) or 'peach' in str(v) for v in labels.values())
 moves=s.engine.reaction_provider.__self__;reason=CardMoveReason.DISCARD if destination.zone_type is ZoneType.DISCARD_PILE else CardMoveReason.SYSTEM
 moves.move(s.state,CardMove('audit-removal',(cid,),ZoneRef(ZoneType.HAND,'p2'),destination,reason,'p1'))
 public=room._public_event(s.events.events[-1])
 if destination.zone_type is ZoneType.DISCARD_PILE:
  assert public['cards'][0]['definition_id']=='basic.peach' and public['cards'][0]['card_id']!=cid
 else:
  assert public is None
  stranger=project_for_human(s.state,s.definitions,'p3',{})
  assert not next(p for p in stranger.players if p.player_id=='p1').revealed_hand
 s.state.__post_init__()


def test_internal_discard_is_not_duplicated_in_public_event_stream():
 from test_t17c_zongxuan import game as zgame,discard
 from sanguosha.multiplayer.room import MultiplayerRoom
 s=zgame();cid=put(s,'basic.peach');s=discard(s,(cid,));s=restore(s);answer(s,())
 room=MultiplayerRoom();room.session=s
 public=[room._public_event(e) for e in s.events.events if isinstance(e,CardMovedEvent) and cid in e.card_ids and e.to_zone.zone_type is ZoneType.DISCARD_PILE]
 assert sum(e is not None for e in public)==1

@pytest.mark.parametrize('selection',[(),('one',)])
def test_zongxuan_equipment_departure_is_once_for_top_or_discard(selection):
 from sanguosha.engine.zongxuan import PendingDiscard
 s=game();s.state.players['p1'].granted_skills.update(zongxuan='audit',xuanfeng='audit')
 cid=put(s,'equipment.weapon.spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
 moves=s.engine.reaction_provider.__self__
 moves.move(s.state,CardMove('audit-once',(cid,),ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.DISCARD,'p1'))
 action=moves.next_reaction(s.state);assert isinstance(action,PendingDiscard)
 s.engine.start_action(action);s=restore(s);answer(s,(cid,) if selection else ())
 assert sum(type(f.action).__name__=='XuanfengAction' for f in s.engine.stack.snapshot())==1
 assert not any(type(a).__name__=='XuanfengAction' for a in s.engine.reaction_provider.__self__.reactions)
 finish(s);s.state.__post_init__()

@pytest.mark.parametrize('initial_zone',[ZoneType.HAND,ZoneType.JUDGMENT,ZoneType.SPECIAL])
def test_xingshang_only_offers_for_nonempty_hand_equipment(initial_zone):
 from sanguosha.engine.forest import XingshangAction
 from sanguosha.model.enums import PlayerStatus
 s=game();s.state.players['p1'].granted_skills['xingshang']='audit';s.state.players['p2'].status=PlayerStatus.DEAD
 hand=ZoneRef(ZoneType.HAND,'p2');cards=s.state.cards_in(hand)
 if cards:CardMoveService(s.events).move(s.state,CardMove('audit-victim-empty',cards,hand,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
 cid=put(s,'basic.slash','p2')
 if initial_zone is not ZoneType.HAND:
  ref=ZoneRef(initial_zone,'p2',special_key='quan') if initial_zone is ZoneType.SPECIAL else ZoneRef(initial_zone,'p2')
  CardMoveService(s.events).move(s.state,CardMove('audit-victim-card',(cid,),hand,ref,CardMoveReason.SYSTEM))
 s.engine.start_action(XingshangAction('audit-offer-regions','p2'))
 assert (s.engine.pending_request is not None)==(initial_zone is ZoneType.HAND)


def test_ai_decision_after_restore_on_moving_pile_request_is_legal():
 from sanguosha.engine.yj2012 import YJ2012Action
 s=game();s.state.players['p1'].granted_skills['quanji']='audit'
 s.engine.start_action(YJ2012Action('audit-ai-pile','p1','quanji'));answer(s,True);s=restore(s)
 r=s.engine.pending_request;d=s.ai.decide(s.state,r);r.validate(d.value)
 s.engine.submit_decision(d);s.state.__post_init__();s=restore(s);s.state.__post_init__()


@pytest.mark.parametrize('enabled',[False,True])
def test_quan_hand_limit_reads_authoritative_pile_and_effective_skill(enabled):
 from sanguosha.engine.yj2012 import power_zone
 from sanguosha.engine.phases import PhaseAction
 from sanguosha.model.enums import Phase
 s=game();s.state.players['p1'].granted_skills['quanji']='audit'
 moves=s.engine.reaction_provider.__self__
 for i in range(2):
  cid=put(s,'basic.slash');moves.move(s.state,CardMove('audit-quan-limit-'+str(i),(cid,),ZoneRef(ZoneType.HAND,'p1'),power_zone('p1'),CardMoveReason.SYSTEM))
 if not enabled:s.state.players['p1'].disabled_skills.add('quanji')
 for i in range(3):put(s,'basic.slash')
 s.state.players['p1'].marks['quan']=99
 count=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
 s.engine.start_action(PhaseAction('audit-quan-limit','p1',Phase.DISCARD))
 assert s.engine.pending_request.min_count==count-4-(2 if enabled else 0)
 s=restore(s);decision=s.ai.decide(s.state,s.engine.pending_request)
 s.engine.submit_decision(decision);s.state.__post_init__()
 assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==4+(2 if enabled else 0)

@pytest.mark.parametrize('disabled',[False,True])
def test_xingshang_multiple_owners_decline_and_skill_disabled(disabled):
 from sanguosha.engine.forest import XingshangAction
 from sanguosha.model.enums import PlayerStatus
 s=game();s.state.players['p2'].status=PlayerStatus.DEAD
 for pid in ('p1','p3'):s.state.players[pid].granted_skills['xingshang']='audit'
 if disabled:s.state.players['p1'].disabled_skills.add('xingshang')
 cards=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
 s.engine.start_action(XingshangAction('audit-multi-inherit','p2'))
 if not disabled:
  assert s.engine.pending_request.player_id=='p1';s=restore(s);answer(s,False)
 assert s.engine.pending_request.player_id=='p3';s=restore(s);answer(s,True);finish(s)
 assert cards<=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p3')))
 s.state.__post_init__()



def test_ownerless_special_pool_named_quan_does_not_create_personal_mark():
 s=game();cid=put(s,'basic.slash');ref=ZoneRef(ZoneType.SPECIAL,special_key='quan')
 s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-ownerless-quan',(cid,),ZoneRef(ZoneType.HAND,'p1'),ref,CardMoveReason.SYSTEM))
 assert cid in s.state.cards_in(ref) and all(not p.marks.get('quan') for p in s.state.players.values())
 s.state.__post_init__()

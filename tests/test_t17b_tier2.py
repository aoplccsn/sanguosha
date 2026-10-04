from dataclasses import replace
import pytest
from sanguosha.engine.yj2011 import ShangshiAction, JujianAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.hp import LoseHpAction
from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.events import AfterDamageEvent, DamageDealtEvent, KillRewardEvent, PhaseEndedEvent
from sanguosha.engine.phases import PhaseAction
from sanguosha.model.enums import DamageNature, EquipmentSlot, Phase, Identity
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.engine.requests import Decision, RequestType, PASS_RESPONSE
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.projection import project_for_human
from test_t17b_tier1 import game, answer, finish
from test_t6_military_basics import put


@pytest.mark.parametrize('nature',list(DamageNature))
def test_jueqing_replaces_damage_without_chains_or_damage_triggers(nature):
    s=game(); s.state.players['p1'].character_id='yj2011_zhang_chunhua'
    s.state.players['p2'].character_id='caocao'
    s.state.players['p2'].chained=s.state.players['p3'].chained=True
    put(s,'equipment.armor.silver_lion','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.state.players['p2'].marks['fog:p4']=1
    s.engine.start_action(MilitaryDamageAction('jueqing','p1','p2',2,nature))
    assert s.engine.pending_request is None
    assert s.state.players['p2'].hp==2
    assert s.state.players['p3'].hp==4
    assert s.state.players['p2'].chained and s.state.players['p3'].chained
    assert not any(isinstance(e,(AfterDamageEvent,DamageDealtEvent)) for e in s.events.events)
    assert s.engine.last_result==0


def test_jueqing_dying_reconnect_and_no_damage_killer_reward():
    s=game(); s.state.players['p1'].character_id='yj2011_zhang_chunhua'
    s.state.players['p2'].hp=1; s.state.players['p2'].identity=Identity.REBEL
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(MilitaryDamageAction('fatal','p1','p2',1))
    assert s.engine.pending_request is not None
    s=restore_session(snapshot_session(s)); finish(s)
    assert not s.state.players['p2'].is_alive
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before
    assert not any(isinstance(e,KillRewardEvent) for e in s.events.events)


@pytest.mark.parametrize('lost',[0,1,2,3,4])
@pytest.mark.parametrize('hand',[0,1,3,5])
def test_shangshi_all_lost_hp_and_hand_counts_no_cap(lost,hand):
    s=game(); p=s.state.players['p1']; p.character_id='yj2011_zhang_chunhua'; p.max_hp=6; p.hp=6-lost
    for cid in tuple(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))):
        # Set up directly through the base movement service so no setup reactions are queued.
        from sanguosha.engine.card_moves import CardMoveService
        CardMoveService(s.events).move(s.state,CardMove('remove:'+cid,(cid,),ZoneRef(ZoneType.HAND,'p1'),
            ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    for _ in range(hand): put(s,'basic.slash','p1')
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    s.engine.start_action(ShangshiAction('shangshi','p1'))
    if hand<lost:
        r=s.engine.pending_request; assert r.request_type is RequestType.YES_NO
        s=restore_session(snapshot_session(s)); answer(s,True)
    assert s.engine.pending_request is None
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==max(hand,lost)
    assert s.engine.stack.is_empty()


def test_shangshi_health_loss_event_offer_and_decline_not_repeated():
    s=game(); p=s.state.players['p1']; p.character_id='yj2011_zhang_chunhua'; p.max_hp=6; p.hp=6
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    s.engine.start_action(LoseHpAction('loss','p1',5))
    assert 'shangshi' in s.engine.pending_request.request_id
    answer(s,False); assert s.engine.pending_request is None
    assert p.hp==1


@pytest.mark.parametrize('source_skill,target_skill',[('wuyan',None),(None,'wuyan'),(None,None)])
@pytest.mark.parametrize('definition',['trick.duel','trick.lightning','basic.slash'])
def test_wuyan_only_trick_damage_source_or_target(source_skill,target_skill,definition):
    s=game()
    if source_skill: s.state.players['p1'].character_id='yj2011_xu_shu'
    if target_skill: s.state.players['p2'].character_id='yj2011_xu_shu'
    cid=put(s,definition)
    s.engine.start_action(MilitaryDamageAction('damage','p1','p2',1,card_id=cid))
    finish(s)
    prevented=definition.startswith('trick.') and bool(source_skill or target_skill)
    assert s.state.players['p2'].hp==4-int(not prevented)


@pytest.mark.parametrize('reason',list(CardMoveReason))
@pytest.mark.parametrize('destination',[ZoneType.DISCARD_PILE,ZoneType.HAND])
def test_xuanfeng_any_equipment_leave_reason_private_choice_and_reconnect(reason,destination):
    s=game(); s.state.players['p1'].character_id='yj2011_ling_tong'
    eq=put(s,'equipment.weapon.crossbow','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    hidden=put(s,'basic.peach','p2')
    moves=s.engine.reaction_provider.__self__
    moves.move(s.state,CardMove('loss',(eq,),ZoneRef(ZoneType.EQUIPMENT,'p1',EquipmentSlot.WEAPON),
        ZoneRef(destination,'p2') if destination is ZoneType.HAND else ZoneRef(destination),reason,'p2'))
    from sanguosha.engine.turnover import TurnoverAction
    s.engine.start_action(TurnoverAction('pump','p5'))
    assert 'xuanfeng' in s.engine.pending_request.request_id
    answer(s,True); answer(s,'p2')
    r=s.engine.pending_request; assert r.subject_player_id=='p2'
    # The owning chooser's authorized request must survive exactly; other players get no request.
    view=project_for_human(s.state,s.definitions,'p3',s.character_names)
    assert hidden not in repr(view)
    s=restore_session(snapshot_session(s)); assert s.engine.pending_request==r
    answer(s,hidden); answer(s,False)
    assert hidden in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert s.engine.stack.is_empty()


@pytest.mark.parametrize('choice',['draw','recover','reset'])
def test_jujian_cost_target_and_recipient_choice_restore(choice):
    s=game(); s.state.players['p1'].character_id='yj2011_xu_shu'
    cid=put(s,'trick.duel'); p=s.state.players['p2']; p.hp=2; p.face_up=False; p.chained=True
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    s.engine.start_action(JujianAction('jujian','p1'))
    for value in (True,cid,'p2'): answer(s,value)
    assert s.engine.pending_request.player_id=='p2'
    s=restore_session(snapshot_session(s)); answer(s,choice)
    p=s.state.players['p2']
    assert cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert p.hp==(3 if choice=='recover' else 2)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==before+(2 if choice=='draw' else 0)
    assert p.face_up is (choice=='reset')
    assert p.chained is (choice!='reset')

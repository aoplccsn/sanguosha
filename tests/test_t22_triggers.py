"""Risk-focused rules and resumability checks for the second boundary group."""
from test_t22_combat import game, answer, drain
from test_t6_military_basics import put
from sanguosha.engine.boundary_triggers import BoundaryTriggerAction, clear_turn, qimou_amount
from sanguosha.engine.military_basics import MilitaryDamageAction, SkillSlashLimit
from sanguosha.engine.card_moves import CardMove, CardMoveReason
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.turns import TurnAction
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.events import DamageDealtEvent, BeforeDamageEvent
from sanguosha.model.enums import Phase, EquipmentSlot
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.snapshot import snapshot_session, restore_session

def test_kuanggu_each_point_has_independent_choice_and_reconnect_preserves_cursor():
    s=game('boundary_wei_yan')
    s.state.players['p1'].hp=2
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(MilitaryDamageAction('two-points','p1','p2',2))
    assert '【狂骨】' in s.engine.pending_request.prompt
    s=restore_session(snapshot_session(s)); answer(s,'recover')
    s=restore_session(snapshot_session(s)); answer(s,'draw')
    assert s.engine.pending_request is None
    assert s.state.players['p1'].hp==3
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before+1
    assert len([e for e in s.events.events if isinstance(e,DamageDealtEvent)])==1

def test_qimou_loses_hp_without_damage_and_modifiers_expire_but_limited_mark_survives():
    s=game('boundary_wei_yan')
    prior=sum(isinstance(e,BeforeDamageEvent) for e in s.events.events)
    initial_hp=s.state.players['p1'].hp
    s.engine.start_action(BoundaryTriggerAction('qimou','p1','jie_qimou'))
    s=restore_session(snapshot_session(s)); answer(s,'2')
    assert s.state.players['p1'].hp==initial_hp-2 and qimou_amount(s.state,'p1')==2
    assert DistanceSystem(s.definitions).distance_between(s.state,'p1','p3')==1
    assert SkillSlashLimit(s.skills).limit(s.state,'p1')==3
    assert sum(isinstance(e,BeforeDamageEvent) for e in s.events.events)==prior
    s.engine.start_action(TurnAction('end-turn','p1',phases=(Phase.FINISH,)))
    drain(s)
    assert qimou_amount(s.state,'p1')==0 and s.state.players['p1'].marks['jie_qimou_used']==1
    assert DistanceSystem(s.definitions).distance_between(s.state,'p1','p3')==2

def test_kuanggu_distance_is_checked_before_target_dies_and_not_for_far_target():
    s=game('boundary_wei_yan')
    s.engine.start_action(MilitaryDamageAction('far','p1','p3',1))
    assert s.engine.pending_request is None
    assert s.state.players['p3'].hp==3

def test_danshou_implicit_aoe_targets_count_and_damage_branch_is_authoritative():
    s=game()
    s.state.players['p1'].character_id='sunquan'
    s.state.players['p2'].character_id='boundary_zhu_ran'
    slash=put(s,'basic.slash','p1')
    aoe=put(s,'trick.archery_attack','p1')
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    s.engine.start_action(UseCardAction('target-one','p1',slash,('p2',))); drain(s)
    s.engine.start_action(UseCardAction('target-aoe','p1',aoe)); drain(s)
    assert s.state.metadata['boundary_target_counts']['p2']==2
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH))
    assert s.engine.pending_request.subject_player_id=='p1'
    answer(s,True)
    assert s.engine.pending_request.min_count==s.engine.pending_request.max_count==2
    cards=s.engine.pending_request.eligible_card_ids[:2]
    s=restore_session(snapshot_session(s)); before=s.state.players['p1'].hp
    answer(s,cards); drain(s)
    assert s.state.players['p1'].hp==before-1
    assert set(cards)<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))

def test_danshou_no_targets_draws_once_and_reconnect_does_not_repeat():
    s=game()
    s.state.players['p1'].character_id='sunquan'
    s.state.players['p2'].character_id='boundary_zhu_ran'
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH)); drain(s)
    s=restore_session(snapshot_session(s))
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==before+1
    assert s.engine.pending_request is None

def test_enyuan_multizone_acquisition_one_offer_and_damage_points_choose_give_or_lose_hp():
    s=game('boundary_fa_zheng')
    a=put(s,'basic.dodge','p2')
    b=put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    moves=s.engine.reaction_provider.__self__
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    moves.obtain_cards(s.state,(a,b),'p1','p1','two-cards')
    s.engine.start_action(BoundaryTriggerAction('flush','p1','jie_enyuan_gain','p2'))
    # Flush itself opens one gain offer and the queued acquisition one more.
    answer(s,False); answer(s,True); drain(s)
    s.state.players['p1'].hp=4
    s.engine.start_action(MilitaryDamageAction('revenge','p2','p1',2))
    answer(s,True); answer(s,'give')
    cid=s.engine.pending_request.eligible_card_ids[0]
    s=restore_session(snapshot_session(s)); answer(s,cid)
    answer(s,True); answer(s,'lose_hp'); drain(s)
    assert cid in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    assert s.state.players['p2'].hp==3

def test_xuanhuo_replaces_normal_draw_and_declined_slash_transfers_two_hidden_cards():
    s=game('boundary_fa_zheng')
    before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(PhaseAction('draw','p1',Phase.DRAW))
    answer(s,True); answer(s,'p2'); answer(s,'p3'); answer(s,'decline')
    assert s.engine.pending_request.subject_player_id=='p2'
    a=s.engine.pending_request.eligible_card_ids[0]; answer(s,a)
    b=s.engine.pending_request.eligible_card_ids[0]
    s=restore_session(snapshot_session(s)); answer(s,b); drain(s)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before+2
    assert {a,b}<=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))

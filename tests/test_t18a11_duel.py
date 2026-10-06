import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.card_use import UseCardAction

def test_wushuang_duel_quota_stays_fixed_after_skill_disabled():
    s=setup('xun_you')
    s.state.players['p1'].granted_skills['wushuang']='audit'
    first=put(s,'basic.slash','p2')
    second=put(s,'basic.slash','p2')
    card=put(s,'trick.duel')
    s.engine.start_action(UseCardAction('audit-fixed-duel','p1',card,('p2',)))
    while s.engine.pending_request.required_definition_id!='basic.slash':
        s=restore(s);answer(s,s.engine.pending_request.timeout_value())
    s.state.players['p1'].disabled_skills.add('wushuang')
    s=restore(s);answer(s,first)
    assert s.engine.pending_request.player_id=='p2'
    response=s.engine.stack.snapshot()[-1].action
    assert response.response_number==2
    assert response.response_total==2
    answer(s,second)
    while s.engine.pending_request:
        s=restore(s);answer(s,s.engine.pending_request.timeout_value())
    assert s.state.players['p1'].hp==3

@pytest.mark.parametrize('owners,expected', [
    ((), [('p2',1,1),('p1',1,1)]),
    (('p1',), [('p2',1,2),('p2',2,2),('p1',1,1)]),
    (('p2',), [('p2',1,1),('p1',1,2),('p1',2,2)]),
    (('p1','p2'), [('p2',1,2),('p2',2,2),('p1',1,2),('p1',2,2)]),
])
def test_duel_requires_correct_number_of_slashes_for_either_wushuang_owner(owners,expected):
    s=setup('xun_you')
    for pid in owners:
        s.state.players[pid].granted_skills['wushuang']='audit'
    materials=[put(s,'basic.slash','p2') for _ in range(2)]
    if 'p2' in owners:
        materials.append(put(s,'basic.slash'))
    card=put(s,'trick.duel')
    s.engine.start_action(UseCardAction('audit-either-duel','p1',card,('p2',)))
    seen=[]
    while s.engine.pending_request:
        s=restore(s);r=s.engine.pending_request
        if r.required_definition_id=='basic.slash':
            a=s.engine.stack.snapshot()[-1].action
            seen.append((r.player_id,a.response_number,a.response_total))
            answer(s,next((c for c in materials if c in r.eligible_card_ids),r.timeout_value()))
        else:answer(s,r.timeout_value())
    assert seen==expected

def test_wushuang_slash_keeps_two_dodges_after_mid_response_skill_disable():
    s=setup('xun_you');s.state.players['p1'].granted_skills['wushuang']='audit'
    first=put(s,'basic.dodge','p2');second=put(s,'basic.dodge','p2')
    card=put(s,'basic.slash')
    s.engine.start_action(UseCardAction('audit-fixed-slash','p1',card,('p2',)))
    assert s.engine.pending_request.required_definition_id=='basic.dodge'
    s.state.players['p1'].disabled_skills.add('wushuang')
    s=restore(s);answer(s,first)
    assert s.engine.pending_request is not None
    a=s.engine.stack.snapshot()[-1].action
    assert a.response_number==2 and a.response_total==2
    answer(s,second)
    assert s.engine.pending_request is None
    assert s.state.players['p2'].hp==4

def test_multitarget_wushuang_slash_freezes_all_initial_targets_before_first_response():
    from sanguosha.model.enums import EquipmentSlot
    from sanguosha.model.zones import ZoneRef,ZoneType
    from sanguosha.engine.card_moves import CardMove,CardMoveReason
    s=setup('xun_you');s.state.players['p1'].granted_skills['wushuang']='audit'
    old=s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-empty',old,ZoneRef(ZoneType.HAND,'p1'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    put(s,'equipment.weapon.halberd','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    card=put(s,'basic.slash')
    dodges={pid:[put(s,'basic.dodge',pid) for _ in range(2)] for pid in ('p2','p3')}
    s.engine.start_action(UseCardAction('audit-multi-fixed','p1',card,('p2','p3')))
    s.state.players['p1'].disabled_skills.add('wushuang')
    seen=[]
    while s.engine.pending_request:
        s=restore(s);r=s.engine.pending_request
        if r.required_definition_id=='basic.dodge':
            a=s.engine.stack.snapshot()[-1].action
            seen.append((r.player_id,a.response_number,a.response_total))
            answer(s,next(c for c in dodges[r.player_id] if c in r.eligible_card_ids))
        else:answer(s,r.timeout_value())
    assert seen==[('p2',1,2),('p2',2,2),('p3',1,2),('p3',2,2)]


def test_liuli_horse_cost_preserves_fixed_distance_override():
    from sanguosha.engine.military_basics import MilitaryStrike
    from sanguosha.model.enums import EquipmentSlot
    from sanguosha.model.zones import ZoneType
    s=setup('xun_you');s.state.players['p2'].granted_skills['liuli']='audit'
    horse=put(s,'equipment.horse.chitu','p2',ZoneType.EQUIPMENT,EquipmentSlot.OFFENSIVE_HORSE)
    s.state.metadata['zhuikong_distance']={'audit':{'source':'p2','target':'p4','turn':s.state.turn_number}}
    slash=put(s,'basic.slash')
    action=MilitaryStrike('audit-liuli-fixed','p1','p2',slash,'basic.dodge')
    handler=s.engine.registry.handler_for(action)
    assert 'p4' in handler.liuli_targets(s.state,action,horse)

@pytest.mark.parametrize('cost_kind,target_allowed', [('horse',False),('weapon',False),('hand',True)])
def test_liuli_removing_cost_recalculates_range_without_mutating_real_equipment(cost_kind,target_allowed):
    from sanguosha.engine.military_basics import MilitaryStrike
    from sanguosha.model.enums import EquipmentSlot
    from sanguosha.model.zones import ZoneRef,ZoneType
    from sanguosha.snapshot import snapshot_session
    s=setup('xun_you')
    horse=put(s,'equipment.horse.chitu','p2',ZoneType.EQUIPMENT,EquipmentSlot.OFFENSIVE_HORSE)
    weapon=put(s,'equipment.weapon.qinggang_sword','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    hand=put(s,'basic.slash','p2')
    if cost_kind=='horse':
        # No weapon: the horse makes p4 reachable, removing it must remove p4.
        from sanguosha.engine.card_moves import CardMove,CardMoveReason
        s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-remove-weapon',(weapon,),ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.WEAPON),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    if cost_kind=='weapon':
        from sanguosha.engine.card_moves import CardMove,CardMoveReason
        s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-remove-horse',(horse,),ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.OFFENSIVE_HORSE),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    card=put(s,'basic.slash')
    a=MilitaryStrike('audit-cost-range','p1','p2',card,'basic.dodge')
    before=snapshot_session(s)
    targets=s.engine.registry.handler_for(a).liuli_targets(s.state,a,{'horse':horse,'weapon':weapon,'hand':hand}[cost_kind])
    assert ('p4' in targets) is target_allowed
    assert snapshot_session(s)==before


def test_liuli_fixed_distance_horse_cost_actual_redirect_resumes_after_reconnect():
    from sanguosha.model.enums import EquipmentSlot
    from sanguosha.model.zones import ZoneRef,ZoneType
    from sanguosha.engine.requests import RequestType
    s=setup('xun_you');s.state.players['p2'].granted_skills['liuli']='audit'
    horse=put(s,'equipment.horse.chitu','p2',ZoneType.EQUIPMENT,EquipmentSlot.OFFENSIVE_HORSE)
    s.state.metadata['zhuikong_distance']={'audit':{'source':'p2','target':'p4','turn':s.state.turn_number}}
    card=put(s,'basic.slash')
    s.engine.start_action(UseCardAction('audit-real-liuli','p1',card,('p2',)))
    answer(s,True);s=restore(s);answer(s,horse);s=restore(s)
    assert 'p4' in s.engine.pending_request.allowed_player_ids
    answer(s,'p4')
    while s.engine.pending_request:
        s=restore(s);answer(s,s.engine.pending_request.timeout_value())
    assert s.state.players['p2'].hp==4 and s.state.players['p4'].hp==3
    assert horse in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

def test_liuli_cannot_redirect_slash_to_empty_hand_kongcheng():
    from sanguosha.engine.military_basics import MilitaryStrike
    from sanguosha.model.zones import ZoneRef,ZoneType
    from sanguosha.engine.card_moves import CardMove,CardMoveReason
    s=setup('xun_you');s.state.players['p3'].granted_skills['kongcheng']='audit'
    hand=s.state.cards_in(ZoneRef(ZoneType.HAND,'p3'))
    s.engine.reaction_provider.__self__.move(s.state,CardMove('audit-empty-kongcheng',hand,ZoneRef(ZoneType.HAND,'p3'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    cost=put(s,'basic.slash','p2');card=put(s,'basic.slash')
    a=MilitaryStrike('audit-liuli-kongcheng','p1','p2',card,'basic.dodge')
    assert 'p3' not in s.engine.registry.handler_for(a).liuli_targets(s.state,a,cost)

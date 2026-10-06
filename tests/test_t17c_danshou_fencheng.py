import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.engine.events import AfterDamageEvent
from sanguosha.engine.errors import InvalidDecision
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.zones import ZoneRef,ZoneType


def game(name):
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_'+name
    for q in s.state.seat_order:empty(s,q)
    return s


@pytest.mark.parametrize('n',[1,2,3,4,5])
def test_danshou_exact_cost_all_branches_restore(n):
    s=game('zhu_ran');cost=tuple(put(s,'basic.slash') for _ in range(n));target=put(s,'basic.dodge','p2')
    s.state.play_usage.counts['skill.danshou']=n-1
    s.engine.start_action(YJ2013Action('skill','p1','danshou'));s=restore(s)
    assert s.engine.pending_request.min_count==n;answer(s,cost);s=restore(s);answer(s,'p2')
    if n<=2:s=restore(s);answer(s,target)
    assert s.engine.pending_request is None
    assert s.state.play_usage.count('skill.danshou')==n
    assert set(cost)<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    if n==1:assert target in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    if n==2:assert target in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    if n==3:assert s.state.players['p2'].hp==3
    if n>=4:assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==2 and len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==3


def test_danshou_new_play_phase_resets_count():
    from sanguosha.engine.phases import PhaseAction
    from sanguosha.model.enums import Phase
    s=game('zhu_ran');put(s,'basic.slash');s.state.play_usage.counts['skill.danshou']=3
    s.engine.start_action(PhaseAction('extra-play','p1',Phase.PLAY))
    assert s.state.play_usage.count('skill.danshou')==0
    assert 'skill:danshou' in s.engine.pending_request.choices


def test_fencheng_actual_discard_count_then_damage_resets_threshold_restore():
    s=game('li_ru');p2=tuple(put(s,'basic.slash','p2') for _ in range(3))
    for _ in range(2):put(s,'basic.dodge','p3')
    p4=put(s,'basic.slash','p4');p5=put(s,'basic.slash','p5')
    s.engine.start_action(YJ2013Action('burn','p1','fencheng'));s=restore(s)
    assert s.engine.pending_request.player_id=='p2' and s.engine.pending_request.minimum_nonempty_count==1
    answer(s,p2);s=restore(s)
    assert s.state.players['p3'].hp==2
    assert s.engine.pending_request.player_id=='p4' and s.engine.pending_request.minimum_nonempty_count==1
    answer(s,());s=restore(s);assert s.engine.pending_request.player_id=='p5'
    answer(s,(p5,));assert s.engine.pending_request is None
    victims={e.target_id:e.amount for e in s.events.events if isinstance(e,AfterDamageEvent)}
    assert victims=={'p3':2,'p4':2}
    assert s.state.players['p1'].marks['fencheng_used']==1
    with pytest.raises(InvalidCardUse):s.engine.start_action(YJ2013Action('again','p1','fencheng'))


def test_fencheng_partial_below_threshold_is_rejected_and_timeout_declines():
    s=game('li_ru');a=put(s,'basic.slash','p2');b=put(s,'basic.dodge','p3');c=put(s,'basic.slash','p3')
    s.engine.start_action(YJ2013Action('burn','p1','fencheng'));answer(s,(a,));r=s.engine.pending_request
    assert r.minimum_nonempty_count==2 and r.timeout_value()==()
    with pytest.raises(InvalidDecision):r.validate((b,))
    answer(s,(b,c))
    assert s.engine.pending_request is None


def test_danshou_equipment_cost_removes_its_range_before_target_choice():
    from sanguosha.model.enums import EquipmentSlot,PlayerStatus
    s=game('zhu_ran');weapon=put(s,'equipment.weapon.serpent_spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    s.engine.start_action(YJ2013Action('skill','p1','danshou'));answer(s,(weapon,))
    assert 'p3' not in s.engine.pending_request.allowed_player_ids
    assert 'p2' in s.engine.pending_request.allowed_player_ids
    s=restore(s);answer(s,'p2')
    assert weapon in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_fencheng_chain_can_kill_source_but_remaining_seats_still_resolve():
    from sanguosha.engine.requests import PASS_RESPONSE
    from sanguosha.model.enums import Identity
    s=game('li_ru');s.state.players['p1'].hp=1
    s.state.players['p1'].identity=Identity.REBEL
    s.state.players['p3'].identity=Identity.LORD
    s.state.players['p1'].chained=s.state.players['p2'].chained=True
    put(s,'basic.slash','p2');s.engine.start_action(YJ2013Action('burn','p1','fencheng'));answer(s,())
    for _ in range(50):
        r=s.engine.pending_request
        if r is None:break
        answer(s,PASS_RESPONSE)
    assert not s.state.players['p1'].is_alive
    victims={e.target_id for e in s.events.events if isinstance(e,AfterDamageEvent)}
    assert {'p2','p3','p4','p5'}<=victims


def test_danshou_never_offers_cost_that_removes_only_reachable_target():
    from sanguosha.engine.yj2013 import play_options
    from sanguosha.model.enums import EquipmentSlot,PlayerStatus
    s=game('zhu_ran')
    for q in ('p2','p4','p5'):s.state.players[q].hp=0;s.state.players[q].status=PlayerStatus.DEAD
    # The survivor's defensive horse makes distance two; only our weapon reaches.
    put(s,'equipment.horse.jueying','p3',ZoneType.EQUIPMENT,EquipmentSlot.DEFENSIVE_HORSE)
    weapon=put(s,'equipment.weapon.serpent_spear','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    assert 'skill:danshou' not in play_options(s.state,'p1',s.skills,s.definitions)
    cost=put(s,'basic.slash')
    assert 'skill:danshou' in play_options(s.state,'p1',s.skills,s.definitions)
    s.engine.start_action(YJ2013Action('cost-range','p1','danshou'))
    assert weapon not in s.engine.pending_request.eligible_card_ids
    answer(s,(cost,));assert s.engine.pending_request.allowed_player_ids==('p3',)

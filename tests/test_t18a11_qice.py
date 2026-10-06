"""Qice reaches every formal ordinary trick via the real action stack."""
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer
from test_t17c_qice import clear_hand
from test_t6_military_basics import put
from sanguosha.engine.yj2012 import YJ2012Action
from sanguosha.engine.requests import RequestType
from sanguosha.engine.events import CardUsedEvent
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.enums import EquipmentSlot,Phase
from sanguosha.model.zones import ZoneRef,ZoneType

@pytest.mark.parametrize('definition',[
    'trick.dismantlement','trick.snatch','trick.ex_nihilo','trick.duel',
    'trick.savage_assault','trick.archery_attack','trick.god_salvation',
    'trick.amazing_grace','trick.fire_attack','trick.iron_chain','trick.borrowed_sword',
])
def test_qice_uses_all_hand_for_each_formal_ordinary_trick(definition):
    s=setup('xun_you');clear_hand(s)
    materials=tuple(put(s,'basic.slash') for _ in range(3))
    put(s,'equipment.weapon.crossbow','p2',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
    s.state.players['p3'].hp=3
    s.engine.start_action(YJ2012Action('audit-qice-each','p1','qice'))
    assert definition in s.engine.pending_request.choices
    assert 'trick.nullification' not in s.engine.pending_request.choices
    assert not any(d.startswith('delayed.') for d in s.engine.pending_request.choices)
    s=restore(s);answer(s,definition)
    for _ in range(180):
        r=s.engine.pending_request
        if r is None:break
        s=restore(s)
        if r.request_type is RequestType.CHOOSE_PLAYERS:
            answer(s,('p2',))
        elif r.request_type is RequestType.CHOOSE_PLAYER:
            answer(s,r.allowed_player_ids[0])
        elif r.request_type is RequestType.CHOOSE_CARD:
            answer(s,r.eligible_card_ids[0])
        else:answer(s,r.timeout_value())
    else:raise AssertionError('Qice did not complete')
    assert s.engine.stack.is_empty()
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    uses=[e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='audit-qice-each:used']
    assert len(uses)==1 and uses[0].virtual_definition_id==definition
    assert uses[0].virtual_card.material_ids==materials
    assert s.state.play_usage.count('skill.qice')==1
    if not s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')):put(s,'basic.slash')
    with pytest.raises(InvalidCardUse):s.engine.start_action(YJ2012Action('audit-again','p1','qice'))
    s.state.__post_init__()

@pytest.mark.parametrize('condition',['non-play','suppressed','qiaoshui-ban','qianxi-ban'])
def test_qice_unavailable_conditions_do_not_pay_materials(condition):
    s=setup('xun_you');clear_hand(s)
    card=put(s,'basic.slash')
    if condition=='non-play':s.state.current_phase=Phase.DRAW
    if condition=='suppressed':s.state.players['p1'].disabled_skills.add('qice')
    if condition=='qiaoshui-ban':s.state.players['p1'].marks['qiaoshui_trick_lock']=s.state.turn_number
    if condition=='qianxi-ban':
        from dataclasses import replace
        from sanguosha.model.enums import Suit
        s.state.cards[card]=replace(s.state.cards[card],suit=Suit.SPADE)
        s.state.metadata['qianxi_limits']={'p2':{'target':'p1','color':'black','turn':s.state.turn_number}}
    with pytest.raises(InvalidCardUse):s.engine.start_action(YJ2012Action('audit-unavailable','p1','qice'))
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))

def test_qice_virtual_preserves_declared_skill_identity():
    from sanguosha.engine.yj2012 import YJ2012Handler
    s=setup('xun_you');clear_hand(s);put(s,'basic.slash')
    handler=YJ2012Handler(s.skills,s.engine.reaction_provider.__self__,s.definitions,None)
    virtual=handler.qice_virtual(s.state,'p1','trick.duel')
    assert virtual.skill_id=='qice'


def test_qice_rechecks_suppression_after_target_request_without_cost():
    s=setup('xun_you');clear_hand(s);card=put(s,'basic.slash')
    s.engine.start_action(YJ2012Action('audit-qice-stale','p1','qice'))
    answer(s,'trick.duel');s=restore(s)
    s.state.players['p1'].disabled_skills.add('qice')
    with pytest.raises(InvalidCardUse):answer(s,('p2',))
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))
    assert not s.state.play_usage.count('skill.qice')


def test_qice_iron_chain_cannot_recast_with_empty_targets():
    s=setup('xun_you');clear_hand(s);card=put(s,'basic.slash')
    s.engine.start_action(YJ2012Action('audit-qice-no-recast','p1','qice'))
    answer(s,'trick.iron_chain');s=restore(s)
    assert s.engine.pending_request.min_count==1
    from sanguosha.engine.errors import InvalidDecision
    with pytest.raises(InvalidDecision):answer(s,())
    assert card in s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))

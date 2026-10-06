from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put
from sanguosha.engine.yj2013 import YJ2013Action
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.errors import InvalidDecision
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.events import Event,CardUsedEvent
from sanguosha.model.enums import Suit,Phase,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType


def game(name):
    s=setup('cao_zhang');s.state.players['p1'].character_id='yj2013_'+name
    for q in s.state.seat_order:empty(s,q)
    return s


def black_trick(s,definition='trick.duel'):
    c=put(s,definition);s.state.cards[c]=replace(s.state.cards[c],suit=Suit.CLUB)
    return c


@pytest.mark.parametrize('cost_def',['trick.duel','delayed.indulgence'])
@pytest.mark.parametrize('discard_trick',[True,False])
def test_mieji_top_cost_and_exact_category_combinations_restore(cost_def,discard_trick):
    s=game('li_ru');cost=black_trick(s,cost_def);trick=put(s,'delayed.indulgence','p2')
    a=put(s,'basic.slash','p2');b=put(s,'equipment.armor.vine','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.engine.start_action(YJ2013Action('mieji','p1','mieji'));s=restore(s);answer(s,cost)
    s=restore(s);answer(s,'p2');s=restore(s)
    assert s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]==cost
    r=s.engine.pending_request
    with pytest.raises(InvalidDecision):r.validate((trick,a))
    with pytest.raises(InvalidDecision):r.validate((a,))
    answer(s,(trick,) if discard_trick else (a,b))
    assert s.engine.pending_request is None and s.state.play_usage.count('skill.mieji')==1
    with pytest.raises(InvalidCardUse):s.engine.start_action(YJ2013Action('again','p1','mieji'))


def test_mieji_only_one_nontrick_discards_available_card():
    s=game('li_ru');cost=black_trick(s);card=put(s,'basic.slash','p2')
    s.engine.start_action(YJ2013Action('mieji','p1','mieji'));answer(s,cost);answer(s,'p2')
    assert s.engine.pending_request.legal_card_sets==((card,),);answer(s,(card,))
    assert card in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


@pytest.mark.parametrize('definition',['basic.slash','equipment.armor.vine'])
def test_zhiyan_finish_draw_reveal_recover_and_use_outside_play_restore(definition):
    s=game('yu_fan');target=s.state.players['p2'];target.hp=2
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top]=replace(s.state.cards[top],definition_id=definition,suit=Suit.HEART)
    s.engine.start_action(PhaseAction('finish','p1',Phase.FINISH));s=restore(s);answer(s,True)
    s=restore(s);assert 'p1' in s.engine.pending_request.allowed_player_ids;answer(s,'p2')
    assert s.engine.pending_request is None
    shown=[e for e in s.events.events if isinstance(e,Event) and e.event_type=='card_revealed']
    assert shown[-1].metadata['card_id']==top
    if definition.startswith('equipment.'):
        assert s.state.players['p2'].hp==3
        assert top in s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.ARMOR))
        assert any(isinstance(e,CardUsedEvent) and e.player_id=='p2' and e.card_id==top for e in s.events.events)
    else:
        assert s.state.players['p2'].hp==2 and top in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))


def test_zhiyan_qianxi_recovers_but_cannot_use_prohibited_equipment():
    s=game('yu_fan');s.state.players['p2'].hp=2
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top]=replace(s.state.cards[top],definition_id='equipment.armor.vine',suit=Suit.HEART)
    s.state.metadata['qianxi_limits']={'p1':{'target':'p2','color':'red','turn':4}}
    s.engine.start_action(YJ2013Action('zhiyan','p1','zhiyan'));answer(s,True);answer(s,'p2')
    assert s.state.players['p2'].hp==3 and top in s.state.cards_in(ZoneRef(ZoneType.HAND,'p2'))
    assert not s.state.cards_in(ZoneRef(ZoneType.EQUIPMENT,'p2',EquipmentSlot.ARMOR))


def test_zhiyan_equipment_replacement_uses_existing_silver_lion_reaction():
    s=game('yu_fan');s.state.players['p2'].hp=1
    old=put(s,'equipment.armor.silver_lion','p2',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top]=replace(s.state.cards[top],definition_id='equipment.armor.vine')
    s.engine.start_action(YJ2013Action('zhiyan','p1','zhiyan'));answer(s,True);answer(s,'p2')
    assert s.state.players['p2'].hp==3 and old in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

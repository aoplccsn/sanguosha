"""Classic Luanji costs obey final trick and hand-use restrictions."""
from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17b_tier1 import answer,finish
from test_t17c_qice import clear_hand
from test_t6_military_basics import put
from sanguosha.engine.fire import LuanjiAction,LuanjiHandler
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.model.enums import Suit
from sanguosha.model.zones import ZoneRef,ZoneType

@pytest.mark.parametrize('restriction',['qianxi','qiaoshui','zhuikong','zishou'])
def test_luanji_cannot_bypass_ordinary_trick_use_restrictions(restriction):
    s=setup('xun_you');s.state.players['p1'].character_id='fire_yuan_shao';clear_hand(s)
    cards=tuple(put(s,'basic.slash') for _ in range(2))
    for c in cards:s.state.cards[c]=replace(s.state.cards[c],suit=Suit.SPADE)
    if restriction=='qianxi':
        s.state.metadata['qianxi_limits']={'p2':{'target':'p1','color':'black','turn':s.state.turn_number}}
    else:
        mark={'qiaoshui':'qiaoshui_trick_lock','zhuikong':'zhuikong_self_only','zishou':'yj_zishou'}[restriction]
        s.state.players['p1'].marks[mark]=s.state.turn_number
    with pytest.raises(InvalidCardUse):s.engine.start_action(LuanjiAction('audit-luanji-limit','p1',cards))
    assert set(cards)<=set(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    assert not s.state.play_usage.count('trick.archery_attack')


def test_luanji_pair_order_does_not_change_same_suit_legality():
    s=setup('xun_you');s.state.players['p1'].character_id='fire_yuan_shao';clear_hand(s)
    cards=tuple(put(s,'basic.slash') for _ in range(2))
    for c in cards:s.state.cards[c]=replace(s.state.cards[c],suit=Suit.HEART)
    s.engine.start_action(LuanjiAction('audit-luanji-reversed','p1',tuple(reversed(cards))))
    while s.engine.pending_request:
        s=restore(s);answer(s,s.engine.pending_request.timeout_value())
    assert set(cards)<=set(s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))

@pytest.mark.parametrize('condition',['different-suit','equipment','suppressed','duplicate','non-play'])
def test_luanji_invalid_cost_or_timing_does_not_move_cards(condition):
    from sanguosha.model.enums import Phase,EquipmentSlot
    s=setup('xun_you');s.state.players['p1'].character_id='fire_yuan_shao';clear_hand(s)
    a=put(s,'basic.slash');b=put(s,'basic.slash')
    for c in (a,b):s.state.cards[c]=replace(s.state.cards[c],suit=Suit.HEART)
    cards=(a,b)
    if condition=='different-suit':s.state.cards[b]=replace(s.state.cards[b],suit=Suit.DIAMOND)
    if condition=='equipment':
        b=put(s,'equipment.weapon.crossbow','p1',ZoneType.EQUIPMENT,EquipmentSlot.WEAPON)
        s.state.cards[b]=replace(s.state.cards[b],suit=Suit.HEART);cards=(a,b)
    if condition=='suppressed':s.state.players['p1'].disabled_skills.add('luanji')
    if condition=='duplicate':cards=(a,a)
    if condition=='non-play':s.state.current_phase=Phase.DRAW
    before=tuple(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    with pytest.raises(InvalidCardUse):s.engine.start_action(LuanjiAction('audit-luanji-invalid','p1',cards))
    assert s.state.cards_in(ZoneRef(ZoneType.HAND,'p1'))==before
    assert not s.state.play_usage.count('trick.archery_attack')


def test_luanji_hongyan_effective_suit_and_multiple_uses_restore():
    from sanguosha.engine.events import CardUsedEvent
    s=setup('xun_you');s.state.players['p1'].character_id='fire_yuan_shao';clear_hand(s)
    s.state.players['p1'].granted_skills['hongyan']='audit'
    for use in range(2):
        cards=tuple(put(s,'basic.slash') for _ in range(2))
        s.state.cards[cards[0]]=replace(s.state.cards[cards[0]],suit=Suit.SPADE)
        s.state.cards[cards[1]]=replace(s.state.cards[cards[1]],suit=Suit.HEART)
        s.engine.start_action(LuanjiAction('audit-luanji-multi:'+str(use),'p1',cards))
        while s.engine.pending_request:
            s=restore(s);answer(s,s.engine.pending_request.timeout_value())
        uses=[e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='audit-luanji-multi:'+str(use)+':used']
        assert len(uses)==1 and uses[0].virtual_card.skill_id=='luanji'
        assert uses[0].virtual_card.material_ids==cards
        assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    assert s.state.play_usage.count('trick.archery_attack')==2

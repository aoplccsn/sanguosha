from dataclasses import replace
import pytest
from test_t17c_first_batch import setup,restore
from test_t17c_juece import empty
from test_t17b_tier1 import answer
from test_t6_military_basics import put,resolve
from sanguosha.engine.yj2013 import YJ2013Action,XiansiSlashAction,counter_zone
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.card_moves import CardMove,CardMoveReason,CardMoveService
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.events import CardUsedEvent
from sanguosha.engine.requests import PASS_RESPONSE
from sanguosha.model.enums import Phase,Suit,EquipmentSlot
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.projection import project_for_human


def game():
    s=setup('cao_zhang')
    s.state.players['p2'].character_id='yj2013_liu_feng'
    for q in s.state.seat_order:empty(s,q)
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return s


def counters(s,n=4):
    cards=tuple(put(s,'basic.slash','p2') for _ in range(n))
    for c in cards:
        CardMoveService(s.events).move(s.state,CardMove('counter:'+c,(c,),ZoneRef(ZoneType.HAND,'p2'),counter_zone('p2'),CardMoveReason.SYSTEM,'p2'))
    s.state.metadata['reaction_event_cursor']=len(s.events.events)
    return cards


def test_xiansi_preparation_includes_self_and_public_counter_faces_restore():
    s=game();own=put(s,'basic.dodge','p2');other=put(s,'equipment.armor.vine','p1',ZoneType.EQUIPMENT,EquipmentSlot.ARMOR)
    s.state.current_player_id='p2'
    s.engine.start_action(PhaseAction('prep','p2',Phase.PREPARATION));s=restore(s)
    answer(s,True);s=restore(s)
    assert 'p2' in s.engine.pending_request.allowed_player_ids
    answer(s,('p2','p1'));s=restore(s)
    assert s.engine.pending_request.subject_player_id=='p1'
    answer(s,other);s=restore(s);answer(s,own)
    assert set(s.state.cards_in(counter_zone('p2')))=={own,other}
    view=project_for_human(s.state,s.definitions,'p1',{})
    player=next(p for p in view.players if p.player_id=='p2')
    assert {c.card_id for c in player.special_piles['counter']}=={own,other}
    assert s.engine.pending_request is None


def test_xiansi_materialless_slash_wine_and_shared_quota_restore():
    s=game();cards=counters(s);s.state.players['p1'].marks['wine']=1
    s.state.metadata['qianxi_limits']={'p3':{'target':'p1','color':'black','turn':4}}
    for c in cards:s.state.cards[c]=replace(s.state.cards[c],suit=Suit.SPADE)
    before=s.state.players['p2'].hp
    s.engine.start_action(XiansiSlashAction('xs','p1','p2'));s=restore(s);answer(s,cards[:2]);s=restore(s)
    answer(s,PASS_RESPONSE)
    assert s.state.players['p2'].hp==before-2
    e=next(e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='xs:used')
    assert e.virtual_card.material_ids==() and e.virtual_card.color is None and e.slash_counted
    assert s.state.play_usage.count('basic.slash')==1
    assert len(s.state.cards_in(counter_zone('p2')))==2
    with pytest.raises(InvalidCardUse):s.engine.start_action(XiansiSlashAction('again','p1','p2'))
    assert s.engine.stack.is_empty()


@pytest.mark.parametrize('invalid',['own','disabled','insufficient','outside_play','distant'])
def test_xiansi_negative_preflight_preserves_counter_and_stack(invalid):
    s=game();cards=counters(s)
    target='p2'
    if invalid=='own':target='p1'
    if invalid=='disabled':s.state.players['p2'].disabled_skills.add('xiansi')
    if invalid=='insufficient':
        CardMoveService(s.events).move(s.state,CardMove('remove',cards[:3],counter_zone('p2'),ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))
    if invalid=='outside_play':s.state.current_phase=Phase.FINISH
    if invalid=='distant':
        s.state.players['p2'].character_id='caocao';s.state.players['p3'].character_id='yj2013_liu_feng'
        CardMoveService(s.events).move(s.state,CardMove('relocate',cards,counter_zone('p2'),counter_zone('p3'),CardMoveReason.SYSTEM));target='p3'
    existing=s.state.cards_in(counter_zone(target))
    with pytest.raises(InvalidCardUse):s.engine.start_action(XiansiSlashAction('bad','p1',target))
    assert s.state.cards_in(counter_zone(target))==existing
    assert s.engine.stack.is_empty()


def test_xiansi_extra_target_uses_modifier_without_halberd_or_lihuo_bonus():
    s=game();cards=counters(s);s.state.players['p1'].marks['slash_extra_targets']=1
    s.engine.start_action(XiansiSlashAction('extra','p1','p2'));answer(s,cards[:2]);s=restore(s)
    assert s.engine.pending_request.min_count==0 and s.engine.pending_request.max_count==1
    answer(s,('p5',));resolve(s)
    used=next(e for e in s.events.events if isinstance(e,CardUsedEvent) and e.event_id=='extra:used')
    assert set(used.target_ids)=={'p2','p5'}
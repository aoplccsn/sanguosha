"""Weapon and armor costs travel through real request/decision/resume paths."""
from dataclasses import replace
import pytest
from test_t6_military_basics import game,put,resolve
from sanguosha.engine.card_moves import CardMove,CardMoveService,CardMoveReason
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.view_as import UseSpear
from sanguosha.engine.requests import RequestType,PASS_RESPONSE
from sanguosha.model.enums import EquipmentSlot,Suit
from sanguosha.model.zones import ZoneRef,ZoneType
from sanguosha.model.virtual_card import VirtualCard

def gear(s,name,owner='p1',slot=EquipmentSlot.WEAPON):
    return put(s,'equipment.'+name,owner,ZoneType.EQUIPMENT,slot)

def clear_hand(s,pid):
    hand=ZoneRef(ZoneType.HAND,pid)
    cards=s.state.cards_in(hand)
    if cards:
        CardMoveService(s.events).move(s.state,CardMove('clear:'+pid,cards,hand,ZoneRef(ZoneType.DISCARD_PILE),CardMoveReason.SYSTEM))

def choose(r):
    if r.request_type is RequestType.YES_NO:
        return True
    if r.request_type is RequestType.CHOOSE_CARDS:
        return r.eligible_card_ids[:r.min_count]
    if r.request_type is RequestType.CHOOSE_CARD:
        return r.eligible_card_ids[0]
    if r.request_type is RequestType.CHOOSE_PLAYER:
        return r.allowed_player_ids[0]
    if r.request_type is RequestType.CHOOSE_OPTION:
        return r.choices[0]
    return PASS_RESPONSE

@pytest.mark.parametrize('armor,definition,suit,expected',[
    ('armor.renwang_shield','basic.slash',Suit.SPADE,4),
    ('armor.renwang_shield','basic.slash',Suit.HEART,3),
    ('armor.vine','basic.slash',Suit.HEART,4),
    ('armor.vine','basic.thunder_slash',Suit.HEART,3)])
def test_armor_slash_filters(armor,definition,suit,expected):
    s=game(); gear(s,armor,'p2',EquipmentSlot.ARMOR)
    card=put(s,definition); s.state.cards[card]=replace(s.state.cards[card],suit=suit)
    s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    resolve(s)
    assert s.state.players['p2'].hp==expected

def test_fan_converts_to_fire_against_vine():
    s=game(); gear(s,'weapon.vermilion_fan'); gear(s,'armor.vine','p2',EquipmentSlot.ARMOR)
    card=put(s,'basic.slash')
    s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    resolve(s,choose)
    assert s.state.players['p2'].hp==2

def test_ancient_blade_empty_hand_adds_damage():
    s=game(); gear(s,'weapon.ancient_blade'); clear_hand(s,'p2')
    card=put(s,'basic.slash'); s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    resolve(s)
    assert s.state.players['p2'].hp==2

def test_double_sword_opponent_choice_draws_owner():
    s=game(); gear(s,'weapon.double_sword'); s.state.metadata['genders']={'p2':'female'}
    card=put(s,'basic.slash'); before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))
    s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    resolve(s,choose)
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p1')))==before
    assert s.state.players['p2'].hp==3

def test_ice_sword_replaces_damage_and_discards_two():
    s=game(); gear(s,'weapon.ice_sword'); before=len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))
    card=put(s,'basic.slash'); s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    resolve(s,choose)
    assert s.state.players['p2'].hp==4
    assert len(s.state.cards_in(ZoneRef(ZoneType.HAND,'p2')))==before-2

def test_kylin_bow_discards_horse_after_damage():
    s=game(); gear(s,'weapon.kylin_bow'); horse=gear(s,'horse.chitu','p2',EquipmentSlot.OFFENSIVE_HORSE)
    card=put(s,'basic.slash'); s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    resolve(s,choose)
    assert s.state.players['p2'].hp==3
    assert horse in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

@pytest.mark.parametrize('weapon',['weapon.green_dragon_blade','weapon.rock_cleaving_axe'])
def test_dodge_weapon_followup(weapon):
    s=game(); gear(s,weapon); dodge=put(s,'basic.dodge','p2'); follow=put(s,'basic.fire_slash')
    card=put(s,'basic.slash'); used=set()
    def response(r):
        if r.request_type is RequestType.RESPOND_WITH_CARD:
            if dodge in r.eligible_card_ids and dodge not in used:
                used.add(dodge); return dodge
            if follow in r.eligible_card_ids:
                return follow
            return PASS_RESPONSE
        return choose(r)
    s.engine.start_action(UseCardAction('slash','p1',card,('p2',)))
    resolve(s,response)
    assert s.state.players['p2'].hp==3

def test_halberd_last_card_hits_three_targets_and_consumes_wine_once():
    s=game(); gear(s,'weapon.halberd'); clear_hand(s,'p1'); card=put(s,'basic.slash')
    s.state.players['p1'].marks['wine']=1
    s.engine.start_action(UseCardAction('slash','p1',card,('p2','p3','p4')))
    resolve(s)
    assert [s.state.players[p].hp for p in ('p2','p3','p4')]==[2,2,2]
    assert 'wine' not in s.state.players['p1'].marks

def test_spear_response_preserves_instance_count_and_color():
    s=game(); gear(s,'weapon.serpent_spear'); a=put(s,'basic.peach'); b=put(s,'basic.wine')
    for cid in (a,b): s.state.cards[cid]=replace(s.state.cards[cid],suit=Suit.HEART)
    s.engine.start_action(RespondWithCardAction('respond','p1','basic.slash','duel'))
    resolve(s,lambda r:'virtual:spear' if r.request_type is RequestType.RESPOND_WITH_CARD else (a,b))
    assert isinstance(s.engine.last_result,VirtualCard)
    assert s.engine.last_result.material_ids==(a,b)
    assert s.engine.last_result.suit is Suit.HEART
    assert len(s.state.cards)==160

def test_spear_active_uses_two_physical_costs_and_slash_counter():
    s=game(); gear(s,'weapon.serpent_spear'); a=put(s,'basic.peach'); b=put(s,'basic.wine')
    s.engine.start_action(UseSpear('spear','p1'))
    resolve(s,lambda r:(a,b) if r.request_type is RequestType.CHOOSE_CARDS else 'p2' if r.request_type is RequestType.CHOOSE_PLAYER else PASS_RESPONSE)
    assert s.state.players['p2'].hp==3
    assert s.state.play_usage.count('basic.slash')==1
    assert all(cid in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)) for cid in (a,b))

def test_silver_lion_loss_heals_through_equipment_replacement_reaction():
    s=game(); old=gear(s,'armor.silver_lion','p1',EquipmentSlot.ARMOR); s.state.players['p1'].hp=2
    card=put(s,'equipment.armor.vine'); s.engine.start_action(UseCardAction('equip','p1',card))
    assert s.state.players['p1'].hp==3
    assert old in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert s.engine.stack.is_empty()

def test_eight_trigrams_responds_to_archery_window():
    s=game(); gear(s,'armor.eight_trigrams','p2',EquipmentSlot.ARMOR)
    top=s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]; s.state.cards[top]=replace(s.state.cards[top],suit=Suit.HEART)
    s.engine.start_action(RespondWithCardAction('archery','p2','basic.dodge','aoe'))
    resolve(s,choose)
    assert isinstance(s.engine.last_result,VirtualCard)
    assert s.engine.last_result.definition_id=='basic.dodge'

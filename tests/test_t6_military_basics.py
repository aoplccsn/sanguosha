"""Actual WAIT/Decision/resume paths for military basics and propagation."""
from dataclasses import replace
import pytest
from sanguosha.session import GameSession
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.card_effects import SlashEffectAction
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.engine.phases import PhaseAction
from sanguosha.model.enums import Phase, EquipmentSlot, DamageNature, Suit
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType

def game():
    s = GameSession.new_game(military=True)
    s.state.current_player_id = 'p1'
    s.state.current_phase = Phase.PLAY
    s.state.turn_number = 1
    s.state.play_usage = PlayUsageState('p1', 1)
    return s

def put(s, definition, owner='p1', zone=ZoneType.HAND, slot=None):
    cid = next(cid for cid in s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE)))
    s.state.cards[cid] = replace(s.state.cards[cid], definition_id=definition)
    CardMoveService(s.events).move(s.state, CardMove('setup:' + cid, (cid,),
        ZoneRef(ZoneType.DRAW_PILE), ZoneRef(zone, owner, slot), CardMoveReason.SYSTEM))
    return cid

def resolve(s, chooser=None):
    steps = 0
    while s.engine.pending_request:
        request = s.engine.pending_request
        value = chooser(request) if chooser else (False if request.request_type is RequestType.YES_NO else PASS_RESPONSE)
        s.engine.submit_decision(Decision(request.request_id, request.player_id, value))
        s.state.__post_init__()
        steps += 1
        assert steps < 100
    assert s.engine.stack.is_empty()
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))

@pytest.mark.parametrize('definition', ['basic.slash', 'basic.fire_slash', 'basic.thunder_slash'])
def test_slash_variants_damage_and_share_phase_limit(definition):
    s = game()
    card = put(s, definition)
    second = put(s, 'basic.thunder_slash')
    s.engine.start_action(UseCardAction('first', 'p1', card, ('p2',)))
    resolve(s)
    assert s.state.players['p2'].hp == 3
    with pytest.raises(InvalidCardUse):
        s.engine.start_action(UseCardAction('second', 'p1', second, ('p2',)))
    assert second in s.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))

def test_wine_next_slash_bonus_consumed_and_phase_limit():
    s = game()
    wine = put(s, 'basic.wine')
    other = put(s, 'basic.wine')
    slash = put(s, 'basic.fire_slash')
    s.engine.start_action(UseCardAction('wine', 'p1', wine))
    assert s.state.players['p1'].marks['wine'] == 1
    with pytest.raises(InvalidCardUse):
        s.engine.start_action(UseCardAction('wine-again', 'p1', other))
    s.engine.start_action(UseCardAction('slash', 'p1', slash, ('p2',)))
    resolve(s)
    assert s.state.players['p2'].hp == 2
    assert 'wine' not in s.state.players['p1'].marks

def test_wine_expires_at_finish():
    s = game()
    s.state.players['p1'].marks['wine'] = 1
    s.engine.start_action(PhaseAction('finish', 'p1', Phase.FINISH))
    assert 'wine' not in s.state.players['p1'].marks

def test_slash_eight_trigrams_red_judgment_virtual_dodge():
    s = game()
    put(s, 'equipment.armor.eight_trigrams', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    slash = put(s, 'basic.slash')
    top = s.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    s.state.cards[top] = replace(s.state.cards[top], suit=Suit.HEART)
    s.engine.start_action(UseCardAction('slash', 'p1', slash, ('p2',)))
    assert s.engine.pending_request.request_type is RequestType.YES_NO
    resolve(s, lambda r: True if r.request_type is RequestType.YES_NO else PASS_RESPONSE)
    assert s.state.players['p2'].hp == 4
    assert top in s.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))

def test_fire_chain_waits_for_peach_then_resumes_next_recipient():
    s = game()
    peach = put(s, 'basic.peach')
    s.state.players['p2'].hp = 1
    s.state.players['p2'].chained = True
    s.state.players['p3'].chained = True
    s.engine.start_action(MilitaryDamageAction('fire', 'p1', 'p2', 1, DamageNature.FIRE))
    assert s.state.players['p3'].hp == 4  # chain is paused behind dying child
    def choose(r):
        return peach if r.player_id == 'p1' and peach in r.eligible_card_ids else PASS_RESPONSE
    resolve(s, choose)
    assert s.state.players['p2'].hp > 0 and s.state.players['p2'].is_alive
    assert s.state.players['p3'].hp == 3
    assert not s.state.players['p2'].chained and not s.state.players['p3'].chained

def test_normal_damage_does_not_propagate_or_unchain():
    s = game()
    s.state.players['p2'].chained = s.state.players['p3'].chained = True
    s.engine.start_action(MilitaryDamageAction('normal', 'p1', 'p2', 1))
    assert s.state.players['p3'].hp == 4 and s.state.players['p2'].chained

def test_fire_slash_entire_chain_waits_for_rescue_before_next_target():
    s=game()
    slash=put(s,'basic.fire_slash'); peach=put(s,'basic.peach')
    s.state.players['p2'].hp=1
    s.state.players['p2'].chained=s.state.players['p3'].chained=True
    s.engine.start_action(UseCardAction('fire-slash','p1',slash,('p2',)))
    def choose(r):
        if r.required_definition_id=='basic.peach':
            assert s.state.players['p3'].hp==4
            return peach if peach in r.eligible_card_ids else PASS_RESPONSE
        return PASS_RESPONSE
    resolve(s,choose)
    assert s.state.players['p2'].hp==1 and s.state.players['p3'].hp==3
    assert all(not s.state.players[pid].chained for pid in ('p2','p3'))

@pytest.mark.parametrize('armor,nature,amount,expected', [
    ('equipment.armor.vine', DamageNature.FIRE, 1, 2),
    ('equipment.armor.silver_lion', DamageNature.THUNDER, 3, 1)])
def test_damage_armor_modifiers(armor, nature, amount, expected):
    s = game()
    put(s, armor, 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    s.engine.start_action(MilitaryDamageAction('damage', 'p1', 'p2', amount, nature))
    assert s.state.players['p2'].hp == 4 - expected

def test_qinggang_ignores_black_slash_armor():
    s = game()
    put(s, 'equipment.weapon.qinggang_sword', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    put(s, 'equipment.armor.renwang_shield', 'p2', ZoneType.EQUIPMENT, EquipmentSlot.ARMOR)
    card = put(s, 'basic.slash')
    s.state.cards[card] = replace(s.state.cards[card], suit=Suit.SPADE)
    s.engine.start_action(UseCardAction('slash', 'p1', card, ('p2',)))
    resolve(s)
    assert s.state.players['p2'].hp == 3

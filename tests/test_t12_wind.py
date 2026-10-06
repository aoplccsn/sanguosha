"""Targeted classic Wind skill and reusable turn-mechanism tests."""

import pytest
from dataclasses import replace

from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.damage import DamageAction
from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.suits import effective_color, effective_suit
from sanguosha.engine.wind import buqu_pile
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE, RequestType
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.engine.turns import TurnAction
from sanguosha.model.enums import Color, DamageNature, EquipmentSlot, Identity, Phase, Suit
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.wind_lord import HuangtianAction
from sanguosha.engine.wind_guhuo import GuhuoAction, committed_zone
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.multiplayer.protocol import serialize_projection, deserialize_projection, serialize_request
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
from sanguosha.content.characters.myth import MYTH_CHARACTERS, MYTH_SKILL_CATALOGUE
import json
import time
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.projection import project_for_human
from sanguosha.session import GameSession

from test_t6_military_basics import put


def drive(session, choose, limit=120):
    seen = []
    for _ in range(limit):
        request = session.engine.pending_request
        if request is None:
            break
        seen.append(request)
        session.engine.submit_decision(Decision(request.request_id, request.player_id,
                                                choose(request)))
        session.state.__post_init__()
    assert session.engine.pending_request is None
    assert session.engine.stack.is_empty()
    return seen


def test_shensu_both_branches_skip_phases_and_resolve_slashes():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_xiahou_yuan'
    equipment = put(session, 'equipment.weapon.serpent_spear')
    session.engine.start_action(TurnAction('wind-turn', 'p1'))

    def choose(request):
        if request.request_type is RequestType.YES_NO:
            return '神速' in request.prompt
        if request.request_type is RequestType.CHOOSE_CARD and equipment in request.eligible_card_ids:
            return equipment
        if request.request_type is RequestType.CHOOSE_PLAYER and 'p3' in request.allowed_player_ids:
            return 'p3'
        if request.request_type is RequestType.RESPOND_WITH_CARD:
            return PASS_RESPONSE
        return request.timeout_value()

    seen = drive(session, choose)
    assert sum('神速' in request.prompt and request.request_type is RequestType.YES_NO
               for request in seen) == 2
    assert session.state.players['p3'].hp == 2
    assert equipment in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert all('skip_' + phase.value not in session.state.players['p1'].marks
               for phase in (Phase.JUDGMENT, Phase.DRAW, Phase.PLAY))
    skipped = {event.phase for event in session.events.events
               if event.__class__.__name__ == 'PhaseSkippedEvent'}
    assert {Phase.JUDGMENT, Phase.DRAW, Phase.PLAY} <= skipped


def test_shensu_decline_keeps_regular_phases():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_xiahou_yuan'
    session.engine.start_action(TurnAction('wind-decline', 'p1'))
    seen = drive(session, lambda request: False if request.request_type is RequestType.YES_NO
                 else request.timeout_value())
    assert any('神速' in request.prompt for request in seen)
    assert session.state.players['p3'].hp == 4
    assert not any(event.__class__.__name__ == 'PhaseSkippedEvent'
                   for event in session.events.events)


def test_face_down_skip_turn_is_general_mechanism():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p2'].face_up = False
    session.engine.start_action(TurnAction('face-down-turn', 'p2'))
    assert session.engine.pending_request is None
    assert session.state.players['p2'].face_up
    assert session.state.current_phase is None
    assert not any(event.__class__.__name__ == 'PhaseStartedEvent'
                   for event in session.events.events)


def test_jushou_draws_three_turns_over_and_skips_next_turn():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_cao_ren'
    session.state.current_player_id = 'p1'
    before = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(PhaseAction('jushou-finish', 'p1', Phase.FINISH))
    request = session.engine.pending_request
    assert '据守' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 3
    assert not session.state.players['p1'].face_up
    view = project_for_human(session.state, session.definitions, 'p1', session.character_names)
    assert not view.players[0].face_up
    session.engine.start_action(TurnAction('jushou-next-turn', 'p1'))
    assert session.engine.pending_request is None
    assert session.state.players['p1'].face_up
    assert session.state.current_phase is None


def test_jushou_decline_and_ai_resource_choice():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_cao_ren'
    session.state.current_player_id = 'p1'
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    session.engine.start_action(PhaseAction('jushou-decline', 'p1', Phase.FINISH))
    request = session.engine.pending_request
    assert session.ai.decide(session.state, request).value is False
    session.engine.submit_decision(Decision(request.request_id, 'p1', False))
    assert session.state.players['p1'].face_up
    assert len(session.state.cards_in(hand)) == before

    cards = session.state.cards_in(hand)[:3]
    CardMoveService(session.events).move(session.state, CardMove('jushou-test-hand', cards,
        hand, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM))
    session.engine.start_action(PhaseAction('jushou-ai', 'p1', Phase.FINISH))
    request = session.engine.pending_request
    assert session.ai.decide(session.state, request).value is True


def huang_zhong_game():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_huang_zhong'
    session.state.players['p1'].hp = 4
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    return session


def reduce_hand(session, player_id, count):
    hand = ZoneRef(ZoneType.HAND, player_id)
    cards = session.state.cards_in(hand)
    removed = cards[:len(cards) - count]
    if removed:
        CardMoveService(session.events).move(session.state, CardMove(
            'setup-reduce-' + player_id, removed, hand,
            ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM))


def liegong_choice(dodge_id=None):
    def choose(request):
        if '烈弓' in request.prompt:
            return True
        if request.request_type is RequestType.RESPOND_WITH_CARD:
            return dodge_id if dodge_id in request.eligible_card_ids else PASS_RESPONSE
        return request.timeout_value()
    return choose


def test_liegong_high_hand_blocks_dodge():
    session = huang_zhong_game()
    dodge = put(session, 'basic.dodge', 'p2')
    slash = put(session, 'basic.slash')
    session.engine.start_action(UseCardAction('liegong-high', 'p1', slash, ('p2',)))
    request = session.engine.pending_request
    assert '烈弓' in request.prompt
    assert session.ai.decide(session.state, request).value is True
    seen = drive(session, liegong_choice(dodge))
    assert any('烈弓' in request.prompt for request in seen)
    assert session.state.players['p2'].hp == 3
    assert dodge in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))


def test_liegong_low_hand_blocks_dodge_but_middle_hand_does_not():
    low = huang_zhong_game()
    reduce_hand(low, 'p2', 0)
    low_dodge = put(low, 'basic.dodge', 'p2')
    low_slash = put(low, 'basic.slash')
    low.engine.start_action(UseCardAction('liegong-low', 'p1', low_slash, ('p2',)))
    seen = drive(low, liegong_choice(low_dodge))
    assert any('烈弓' in request.prompt for request in seen)
    assert low.state.players['p2'].hp == 3

    middle = huang_zhong_game()
    reduce_hand(middle, 'p2', 2)
    middle_dodge = put(middle, 'basic.dodge', 'p2')
    middle_slash = put(middle, 'basic.slash')
    middle.engine.start_action(UseCardAction('liegong-middle', 'p1', middle_slash, ('p2',)))
    seen = drive(middle, liegong_choice(middle_dodge))
    assert not any('烈弓' in request.prompt for request in seen)
    assert middle.state.players['p2'].hp == 4
    assert middle_dodge in middle.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


@pytest.mark.parametrize('slash_definition', ['basic.fire_slash', 'basic.thunder_slash'])
def test_liegong_uses_equipment_range_with_elemental_slash(slash_definition):
    session = huang_zhong_game()
    put(session, 'equipment.weapon.qinggang_sword', 'p1', ZoneType.EQUIPMENT,
        EquipmentSlot.WEAPON)
    reduce_hand(session, 'p3', 1)
    dodge = put(session, 'basic.dodge', 'p3')
    slash = put(session, slash_definition)
    session.engine.start_action(UseCardAction('liegong-elemental', 'p1', slash, ('p3',)))
    seen = drive(session, liegong_choice(dodge))
    assert any('烈弓' in request.prompt for request in seen)
    assert session.state.players['p3'].hp == 3
    assert dodge in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))


def wei_yan_game(hp=2):
    session = GameSession.new_game(military=True, five_generals=True)
    player = session.state.players['p1']
    player.character_id = 'wind_wei_yan'
    player.max_hp = 4
    player.hp = hp
    return session


@pytest.mark.parametrize(('target', 'amount', 'nature', 'expected_hp', 'recoveries'), [
    ('p2', 1, DamageNature.NORMAL, 3, 1),
    ('p2', 2, DamageNature.NORMAL, 4, 2),
    ('p2', 1, DamageNature.FIRE, 3, 1),
    ('p3', 1, DamageNature.NORMAL, 2, 0),
])
def test_kuanggu_checks_damage_distance_and_recovers_each_point(
        target, amount, nature, expected_hp, recoveries):
    session = wei_yan_game()
    session.engine.start_action(MilitaryDamageAction(
        'kuanggu-damage', 'p1', target, amount, nature))
    assert session.engine.pending_request is None
    assert session.state.players['p1'].hp == expected_hp
    assert session.state.players[target].hp == 4 - amount
    assert sum(event.__class__.__name__ == 'HpRecoveredEvent'
               for event in session.events.events) == recoveries


def test_kuanggu_at_full_hp_does_not_overheal():
    session = wei_yan_game(hp=4)
    session.engine.start_action(MilitaryDamageAction(
        'kuanggu-full', 'p1', 'p2', 2, DamageNature.THUNDER))
    assert session.engine.pending_request is None
    assert session.state.players['p1'].hp == 4
    assert session.state.players['p2'].hp == 2


def test_kuanggu_amplified_damage_recovers_each_point_with_unique_actions():
    session = wei_yan_game()
    session.state.players['p2'].marks['wind:test'] = 1
    session.engine.start_action(MilitaryDamageAction(
        'kuanggu-amplified', 'p1', 'p2', 1, DamageNature.FIRE))
    assert session.state.players['p2'].hp == 2
    assert session.state.players['p1'].hp == 4
    assert {'kuanggu-amplified:kuanggu:0', 'kuanggu-amplified:kuanggu:1'} <= session.engine._seen_action_ids
    assert session.engine.stack.is_empty()


def xiao_qiao_game():
    session = GameSession.new_game(military=True, five_generals=True)
    player = session.state.players['p1']
    player.character_id = 'wind_xiao_qiao'
    player.max_hp = 3
    player.hp = 2
    return session


def test_hongyan_interprets_spade_without_mutating_card_and_judgment():
    session = xiao_qiao_game()
    hand_card = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.state.cards[hand_card] = replace(session.state.cards[hand_card], suit=Suit.SPADE)
    assert session.state.cards[hand_card].suit is Suit.SPADE
    assert effective_suit(session.state, hand_card) is Suit.HEART
    assert effective_color(session.state, hand_card) is Color.RED
    view = project_for_human(session.state, session.definitions, 'p1', session.character_names)
    assert next(card for card in view.hand if card.card_id == hand_card).suit == '♥'

    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE)
    session.engine.start_action(JudgmentAction('hongyan-judgment', 'p1',
                                               JudgmentPattern(suit=Suit.HEART)))
    assert session.engine.pending_request is None
    assert session.engine.last_result is True
    assert session.state.cards[top].suit is Suit.SPADE


@pytest.mark.parametrize('cost_suit', [Suit.HEART, Suit.SPADE])
def test_tianxiang_transfers_damage_and_draws_after_resolution(cost_suit):
    session = xiao_qiao_game()
    cost = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.state.cards[cost] = replace(session.state.cards[cost], suit=cost_suit)
    before_hand = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p3')))
    session.engine.start_action(DamageAction('tianxiang', 'p2', 'p1', 1))

    def choose(request):
        if '天香' in request.prompt and request.request_type is RequestType.YES_NO:
            return True
        if request.request_type is RequestType.CHOOSE_CARD:
            return cost
        if request.request_type is RequestType.CHOOSE_PLAYER:
            return 'p3'
        return request.timeout_value()

    seen = drive(session, choose)
    assert any('天香' in request.prompt for request in seen)
    assert session.state.players['p1'].hp == 2
    assert session.state.players['p3'].hp == 3
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))) == before_hand + 1
    assert cost in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_tianxiang_decline_and_equipment_cannot_pay_cost():
    decline = xiao_qiao_game()
    cost = decline.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    decline.state.cards[cost] = replace(decline.state.cards[cost], suit=Suit.HEART)
    decline.engine.start_action(DamageAction('tianxiang-decline', 'p2', 'p1', 1))
    drive(decline, lambda request: False if request.request_type is RequestType.YES_NO
          else request.timeout_value())
    assert decline.state.players['p1'].hp == 1

    equipment_only = xiao_qiao_game()
    hand = ZoneRef(ZoneType.HAND, 'p1')
    cards = equipment_only.state.cards_in(hand)
    CardMoveService(equipment_only.events).move(equipment_only.state, CardMove(
        'empty-hand', cards, hand, ZoneRef(ZoneType.DISCARD_PILE), CardMoveReason.SYSTEM))
    equipment = put(equipment_only, 'equipment.weapon.serpent_spear', 'p1',
                    ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    equipment_only.state.cards[equipment] = replace(equipment_only.state.cards[equipment],
                                                  suit=Suit.HEART)
    equipment_only.engine.start_action(DamageAction('tianxiang-no-hand', 'p2', 'p1', 1))
    assert equipment_only.engine.pending_request is None
    assert equipment_only.state.players['p1'].hp == 1
    assert equipment in equipment_only.state.cards_in(
        ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON))


def test_tianxiang_target_dying_does_not_draw_after_death():
    session = xiao_qiao_game()
    cost = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.state.cards[cost] = replace(session.state.cards[cost], suit=Suit.HEART)
    session.state.players['p3'].hp = 1
    session.engine.start_action(DamageAction('tianxiang-dying', 'p2', 'p1', 1))

    def choose(request):
        if '天香' in request.prompt and request.request_type is RequestType.YES_NO:
            return True
        if request.request_type is RequestType.CHOOSE_CARD:
            return cost
        if request.request_type is RequestType.CHOOSE_PLAYER:
            return 'p3'
        if request.request_type is RequestType.RESPOND_WITH_CARD:
            return PASS_RESPONSE
        return request.timeout_value()

    drive(session, choose)
    assert session.state.players['p1'].hp == 2
    assert not session.state.players['p3'].is_alive


def zhou_tai_game():
    session = GameSession.new_game(military=True, five_generals=True)
    player = session.state.players['p1']
    player.character_id = 'wind_zhou_tai'
    player.max_hp = 4
    player.hp = 1
    return session


def test_buqu_unique_rank_recovers_and_repeated_dying_adds_a_card():
    session = zhou_tai_game()
    first = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.engine.start_action(DamageAction('buqu-first', 'p2', 'p1', 1))
    assert session.engine.pending_request is None
    assert session.state.players['p1'].hp == 1
    assert session.state.cards_in(buqu_pile('p1')) == (first,)
    next_card = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    first_rank = session.state.cards[first].rank
    session.state.cards[next_card] = replace(session.state.cards[next_card],
        rank=1 if first_rank != 1 else 2)
    session.engine.start_action(DamageAction('buqu-second', 'p2', 'p1', 1))
    assert session.engine.pending_request is None
    assert session.state.players['p1'].hp == 1
    assert len(session.state.cards_in(buqu_pile('p1'))) == 2


def test_buqu_duplicate_rank_enters_discard_then_normal_dying_and_death_cleanup():
    session = zhou_tai_game()
    draw = ZoneRef(ZoneType.DRAW_PILE)
    top, existing = session.state.cards_in(draw)[:2]
    session.state.cards[existing] = replace(session.state.cards[existing],
                                            rank=session.state.cards[top].rank)
    CardMoveService(session.events).move(session.state, CardMove('setup-buqu-pile',
        (existing,), draw, buqu_pile('p1'), CardMoveReason.SYSTEM))
    session.engine.start_action(DamageAction('buqu-duplicate', 'p2', 'p1', 1))
    assert session.engine.pending_request is not None
    drive(session, lambda request: PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD
          else request.timeout_value())
    assert not session.state.players['p1'].is_alive
    assert top in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert existing in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert not session.state.cards_in(buqu_pile('p1'))


def test_buqu_duplicate_allows_peach_rescue_and_keeps_existing_pile():
    session = zhou_tai_game()
    peach = put(session, 'basic.peach', 'p1')
    draw = ZoneRef(ZoneType.DRAW_PILE)
    top, existing = session.state.cards_in(draw)[:2]
    session.state.cards[existing] = replace(session.state.cards[existing],
                                            rank=session.state.cards[top].rank)
    CardMoveService(session.events).move(session.state, CardMove('setup-buqu-peach',
        (existing,), draw, buqu_pile('p1'), CardMoveReason.SYSTEM))
    session.engine.start_action(DamageAction('buqu-peach', 'p2', 'p1', 1))
    drive(session, lambda request: peach if request.request_type is RequestType.RESPOND_WITH_CARD
          and request.player_id == 'p1' and peach in request.eligible_card_ids
          else PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD
          else request.timeout_value())
    assert session.state.players['p1'].is_alive
    assert session.state.players['p1'].hp == 1
    assert session.state.cards_in(buqu_pile('p1')) == (existing,)


def test_buqu_pile_count_replaces_normal_hand_limit():
    session = zhou_tai_game()
    draw = ZoneRef(ZoneType.DRAW_PILE)
    cards = session.state.cards_in(draw)[:2]
    CardMoveService(session.events).move(session.state, CardMove('setup-buqu-limit',
        cards, draw, buqu_pile('p1'), CardMoveReason.SYSTEM))
    session.state.current_player_id = 'p1'
    session.engine.start_action(PhaseAction('buqu-discard', 'p1', Phase.DISCARD))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_CARDS
    assert request.min_count == request.max_count == 2
    drive(session, lambda pending: pending.timeout_value())
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == 2


def test_buqu_pile_is_public_in_each_player_projection():
    session = zhou_tai_game()
    card = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.engine.start_action(DamageAction('buqu-public', 'p2', 'p1', 1))
    for viewer in ('p1', 'p2'):
        view = project_for_human(session.state, session.definitions, viewer,
                                 session.character_names)
        pile = view.players[0].special_piles['buqu']
        assert len(pile) == 1 and pile[0].card_id == card
        assert pile[0].rank
        assert card not in {shared.card_id for shared in view.shared_cards}


def zhang_jiao_game():
    session = GameSession.new_game(military=True, five_generals=True)
    player = session.state.players['p1']
    player.character_id = 'wind_zhang_jiao'
    player.max_hp = 3
    player.hp = 2
    return session


def leiji_choice(dodge):
    def choose(request):
        if request.request_type is RequestType.RESPOND_WITH_CARD:
            return dodge if dodge in request.eligible_card_ids else PASS_RESPONSE
        if request.request_type is RequestType.YES_NO and '【雷击】' in request.prompt:
            return True
        if request.request_type is RequestType.CHOOSE_PLAYER and 'p2' in request.allowed_player_ids:
            return 'p2'
        return request.timeout_value()
    return choose


@pytest.mark.parametrize(('suit', 'target_hp', 'source_hp'), [
    (Suit.SPADE, 2, 2),
    (Suit.CLUB, 3, 3),
    (Suit.HEART, 4, 2),
])
def test_leiji_judgment_suits_use_normal_damage_and_recover(suit, target_hp, source_hp):
    session = zhang_jiao_game()
    dodge = put(session, 'basic.dodge', 'p1')
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=suit)
    session.engine.start_action(RespondWithCardAction(
        'leiji-response', 'p1', 'basic.dodge', 'incoming'))
    seen = drive(session, leiji_choice(dodge))
    assert any('雷击' in request.prompt for request in seen)
    assert session.state.players['p2'].hp == target_hp
    assert session.state.players['p1'].hp == source_hp
    assert dodge in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_leiji_thunder_damage_propagates_through_chain():
    session = zhang_jiao_game()
    dodge = put(session, 'basic.dodge', 'p1')
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE)
    session.state.players['p2'].chained = True
    session.state.players['p3'].chained = True
    session.engine.start_action(RespondWithCardAction(
        'leiji-chain-response', 'p1', 'basic.dodge', 'incoming'))
    drive(session, leiji_choice(dodge))
    assert session.state.players['p2'].hp == 2
    assert session.state.players['p3'].hp == 2
    assert not session.state.players['p2'].chained
    assert not session.state.players['p3'].chained


@pytest.mark.parametrize('zone', [ZoneType.HAND, ZoneType.EQUIPMENT])
def test_guidao_replaces_judgment_with_black_card_from_legal_zone(zone):
    session = zhang_jiao_game()
    slot = EquipmentSlot.WEAPON if zone is ZoneType.EQUIPMENT else None
    definition = 'equipment.weapon.serpent_spear' if slot else 'basic.dodge'
    material = put(session, definition, 'p1', zone, slot)
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.SPADE)
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.HEART)
    session.engine.start_action(JudgmentAction('guidao-judge', 'p2',
        JudgmentPattern(suit=Suit.SPADE), return_card_id=True))

    def choose(request):
        if '【鬼道】' in request.prompt and request.request_type is RequestType.YES_NO:
            return True
        if request.request_type is RequestType.CHOOSE_CARD:
            return material
        return request.timeout_value()

    seen = drive(session, choose)
    assert any('鬼道' in request.prompt for request in seen)
    assert session.engine.last_result == material
    assert top in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_guidao_can_change_leiji_judgment_before_thunder_damage():
    session = zhang_jiao_game()
    dodge = put(session, 'basic.dodge', 'p1')
    material = put(session, 'basic.slash', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.SPADE)
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.HEART)
    session.engine.start_action(RespondWithCardAction(
        'leiji-guidao-response', 'p1', 'basic.dodge', 'incoming'))

    def choose(request):
        if request.request_type is RequestType.RESPOND_WITH_CARD:
            return dodge if dodge in request.eligible_card_ids else PASS_RESPONSE
        if request.request_type is RequestType.YES_NO:
            return '【雷击】' in request.prompt or '【鬼道】' in request.prompt
        if request.request_type is RequestType.CHOOSE_PLAYER:
            return 'p2'
        if request.request_type is RequestType.CHOOSE_CARD:
            return material
        return request.timeout_value()

    seen = drive(session, choose)
    assert any('雷击判定' in request.prompt and '鬼道' in request.prompt for request in seen)
    assert session.state.players['p2'].hp == 2
    assert top in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def huangtian_game():
    session = zhang_jiao_game()
    session.state.current_player_id = 'p4'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p4', 1)
    return session


@pytest.mark.parametrize('definition', ['basic.dodge', 'delayed.lightning'])
def test_huangtian_gives_card_to_lord_once_per_play_phase(definition):
    session = huangtian_game()
    card = put(session, definition, 'p4')
    session.engine.start_action(HuangtianAction('huangtian-give', 'p4'))
    request = session.engine.pending_request
    assert request.player_id == 'p4'
    assert card in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p4', card))
    assert card in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert card not in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p4'))
    assert session.state.play_usage.count('skill.huangtian') == 1
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(HuangtianAction('huangtian-again', 'p4'))


def test_huangtian_play_option_and_lord_faction_limits():
    session = huangtian_game()
    put(session, 'basic.dodge', 'p4')
    session.engine.start_action(PhaseAction('huangtian-play', 'p4', Phase.PLAY))
    assert 'skill:huangtian' in session.engine.pending_request.choices
    drive(session, lambda request: 'end_play_phase'
          if request.request_type is RequestType.CHOOSE_OPTION else request.timeout_value())
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(HuangtianAction('huangtian-not-qun', 'p2'))
    session.state.players['p1'].identity = Identity.REBEL
    assert not session.skills.has(session.state, 'p1', 'huangtian')
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(HuangtianAction('huangtian-no-lord', 'p4'))


def test_huangtian_ai_gives_only_to_needy_ally():
    session = huangtian_game()
    put(session, 'basic.dodge', 'p4')
    session.state.players['p4'].identity = Identity.LOYALIST
    session.state.players['p1'].hp = 1
    session.engine.start_action(PhaseAction('huangtian-ai-play', 'p4', Phase.PLAY))
    request = session.engine.pending_request
    assert session.ai.decide(session.state, request).value == 'skill:huangtian'
    session.state.players['p4'].identity = Identity.REBEL
    assert session.ai.decide(session.state, request).value != 'skill:huangtian'


def yuji_game():
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = 'wind_yuji'
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    return session


@pytest.mark.parametrize(('actual', 'suit', 'challengers', 'hp_after', 'draws'), [
    ('basic.slash', Suit.HEART, (), 3, 0),
    ('basic.dodge', Suit.SPADE, (), 3, 0),
    ('basic.slash', Suit.HEART, ('p2',), 2, 0),
    ('basic.slash', Suit.CLUB, ('p2',), 3, 0),
    ('basic.dodge', Suit.HEART, ('p2',), 4, 1),
])
def test_guhuo_active_challenge_truth_suit_and_effect(actual, suit, challengers, hp_after, draws):
    session = yuji_game()
    material = put(session, actual, 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=suit)
    cards_before = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    action = GuhuoAction('guhuo-active', 'p1')
    session.engine.start_action(action)
    seen = drive(session, lambda request: (
        'basic.slash' if request.request_type is RequestType.CHOOSE_OPTION else
        material if request.request_type is RequestType.CHOOSE_CARD else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        request.player_id in challengers if request.request_type is RequestType.YES_NO else
        PASS_RESPONSE))
    assert len([r for r in seen if 'challenge' in r.request_id]) == 4
    assert session.state.players['p2'].hp == hp_after
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == cards_before + draws
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert not session.state.cards_in(committed_zone(action))


@pytest.mark.parametrize('challenged', [False, True])
def test_guhuo_active_ex_nihilo_resolves_normal_trick_effect(challenged):
    session = yuji_game()
    material = put(session, 'trick.ex_nihilo' if challenged else 'basic.dodge', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.HEART)
    hand = ZoneRef(ZoneType.HAND, 'p1')
    before = len(session.state.cards_in(hand))
    action = GuhuoAction('guhuo-ex-nihilo', 'p1')
    session.engine.start_action(action)
    seen = drive(session, lambda request: (
        'trick.ex_nihilo' if request.request_type is RequestType.CHOOSE_OPTION else
        material if request.request_type is RequestType.CHOOSE_CARD else
        challenged and request.player_id == 'p2' if request.request_type is RequestType.YES_NO else
        PASS_RESPONSE))
    assert seen[0].choices and 'trick.ex_nihilo' in seen[0].choices
    assert len(session.state.cards_in(hand)) == before + 1
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert session.state.players['p2'].hp == (3 if challenged else 4)

@pytest.mark.parametrize('required', ['basic.dodge', 'trick.nullification'])
def test_guhuo_response_uses_existing_response_window(required):
    session = yuji_game()
    material = put(session, required, 'p1')
    action = RespondWithCardAction('guhuo-response', 'p1', required, 'source')
    session.engine.start_action(action)
    request = session.engine.pending_request
    assert 'virtual:guhuo' in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'virtual:guhuo'))
    drive(session, lambda request: (
        required if request.request_type is RequestType.CHOOSE_OPTION else
        material if request.request_type is RequestType.CHOOSE_CARD else False))
    assert isinstance(session.engine.last_result, VirtualCard)
    assert session.engine.last_result.definition_id == required
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_guhuo_committed_card_masked_and_challenge_request_resumes():
    session = yuji_game()
    material = put(session, 'basic.slash', 'p1')
    action = GuhuoAction('guhuo-privacy', 'p1')
    session.engine.start_action(action)
    for value in ('basic.slash', material, 'p2'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id, value))
    request = session.engine.pending_request
    assert request.player_id == 'p2' and 'challenge' in request.request_id
    view = project_for_human(session.state, session.definitions, 'p2', session.character_names)
    roundtrip = deserialize_projection(serialize_projection(view))
    pile = roundtrip.players[0].special_piles[committed_zone(action).special_key]
    assert len(pile) == 1 and pile[0].name == '未知扣置牌'
    assert pile[0].card_id != material
    assert material not in json.dumps(serialize_projection(view), ensure_ascii=False)
    payload = serialize_request(request, 10000)
    assert payload['player_id'] == 'p2' and payload['request_type'] == 'yes_no'
    drive(session, lambda pending: False if pending.request_type is RequestType.YES_NO
          else PASS_RESPONSE)
    assert session.state.players['p2'].hp == 3


def test_guhuo_ai_challenge_does_not_read_committed_card_truth():
    session = yuji_game()
    material = put(session, 'basic.slash', 'p1')
    session.engine.start_action(GuhuoAction('guhuo-ai-privacy', 'p1'))
    for value in ('basic.slash', material, 'p2'):
        request = session.engine.pending_request
        session.engine.submit_decision(Decision(request.request_id, request.player_id, value))
    request = session.engine.pending_request
    first = session.ai.decide(session.state, request).value
    session.state.cards[material] = replace(session.state.cards[material],
                                            definition_id='basic.dodge', suit=Suit.CLUB)
    assert session.ai.decide(session.state, request).value == first


def test_guhuo_multiple_challengers_each_lose_hp_before_effect():
    session = yuji_game()
    material = put(session, 'basic.slash', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.HEART)
    session.engine.start_action(GuhuoAction('guhuo-many', 'p1'))
    drive(session, lambda request: (
        'basic.slash' if request.request_type is RequestType.CHOOSE_OPTION else
        material if request.request_type is RequestType.CHOOSE_CARD else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        request.player_id in ('p2', 'p3') if request.request_type is RequestType.YES_NO else
        PASS_RESPONSE))
    assert session.state.players['p2'].hp == 2
    assert session.state.players['p3'].hp == 3


def test_guhuo_unchallenged_discard_remains_masked_in_projection():
    session = yuji_game()
    material = put(session, 'basic.dodge', 'p1')
    session.engine.start_action(GuhuoAction('guhuo-no-reveal', 'p1'))
    drive(session, lambda request: (
        'basic.slash' if request.request_type is RequestType.CHOOSE_OPTION else
        material if request.request_type is RequestType.CHOOSE_CARD else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        False if request.request_type is RequestType.YES_NO else PASS_RESPONSE))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    view = project_for_human(session.state, session.definitions, 'p2', session.character_names)
    assert view.discard_top.name == '蛊惑·杀'
    assert view.discard_top.card_id != material
    assert material not in json.dumps(serialize_projection(view), ensure_ascii=False)


def test_guhuo_wine_response_and_challenged_false_nullification():
    session = yuji_game()
    session.state.players['p1'].hp = 0
    wine = put(session, 'basic.wine', 'p1')
    session.engine.start_action(RespondWithCardAction(
        'guhuo-wine-response', 'p1', 'basic.peach', 'dying', subject_player_id='p1'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'virtual:guhuo'))
    drive(session, lambda request: (
        'basic.wine' if request.request_type is RequestType.CHOOSE_OPTION else
        wine if request.request_type is RequestType.CHOOSE_CARD else False))
    assert isinstance(session.engine.last_result, VirtualCard)
    assert session.engine.last_result.definition_id == 'basic.wine'
    fake = put(session, 'basic.dodge', 'p1')
    cards_before = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    session.engine.start_action(RespondWithCardAction(
        'guhuo-false-null', 'p1', 'trick.nullification', 'trick'))
    request = session.engine.pending_request
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'virtual:guhuo'))
    drive(session, lambda request: (
        'trick.nullification' if request.request_type is RequestType.CHOOSE_OPTION else
        fake if request.request_type is RequestType.CHOOSE_CARD else
        request.player_id == 'p2'))
    assert session.engine.last_result is None
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == cards_before + 1


def test_guhuo_room_masks_card_and_restores_challenge_on_reconnect():
    messages1, messages2 = [], []
    room = MultiplayerRoom(seed=17)
    p1, _ = room.join('yuji', messages1.append)
    p2, token2 = room.join('challenger', messages2.append)
    room.session = yuji_game()
    room.phase = RoomPhase.IN_GAME
    material = put(room.session, 'basic.slash', 'p1')
    room._seen_events = len(room.session.events.events)
    room.session.engine.start_action(GuhuoAction('guhuo-room', 'p1'))
    for value in ('basic.slash', material, 'p2'):
        request = room.session.engine.pending_request
        room.session.engine.submit_decision(Decision(request.request_id, request.player_id, value))
    request = room.session.engine.pending_request
    assert request.player_id == p2
    room.request_deadline = time.time() + 30
    messages1.clear()
    messages2.clear()
    room._sync()
    assert not any(m['type'] == 'PENDING_REQUEST' for m in messages1)
    assert any(m['type'] == 'PENDING_REQUEST' and m['request']['request_id'] == request.request_id
               for m in messages2)
    assert any(m['type'] == 'PUBLIC_EVENT' and m['event']['stage'] == 'declare'
               for m in messages2)
    assert material not in json.dumps(messages2, ensure_ascii=False)
    room.disconnect(p2)
    restored = []
    assert room.join('challenger', restored.append, token=token2)[0] == p2
    assert any(m['type'] == 'PENDING_REQUEST' and m['request']['request_id'] == request.request_id
               for m in restored)
    assert material not in json.dumps(restored, ensure_ascii=False)
    room.submit(p2, Decision(request.request_id, p2, False))
    assert room.session.engine.pending_request.request_id != request.request_id


def test_wind_catalogue_is_playable_without_placeholder_descriptions():
    ordinary = [character for character in MYTH_CHARACTERS
                if character.id.startswith('wind_') and '_god_' not in character.id]
    assert len(ordinary) == 8
    skills = {skill.id: skill for skill in MYTH_SKILL_CATALOGUE}
    assert all(character.metadata['implemented'] and character.metadata['playable']
               for character in ordinary)
    assert all('规则摘要' not in skills[skill_id].description
               for character in ordinary for skill_id in character.skill_ids)
    assert all(character.metadata['implemented'] and character.metadata['playable']
               for character in MYTH_CHARACTERS if character.id.startswith('wind_god_'))


def test_guhuo_ai_selects_truthful_heart_slash_and_material():
    session = yuji_game()
    hand = ZoneRef(ZoneType.HAND, 'p1')
    for cid in session.state.cards_in(hand):
        session.state.cards[cid] = replace(session.state.cards[cid],
                                           definition_id='basic.dodge', suit=Suit.CLUB)
    material = put(session, 'basic.slash', 'p1')
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.HEART)
    session.engine.start_action(PhaseAction('guhuo-ai-play', 'p1', Phase.PLAY))
    request = session.engine.pending_request
    assert 'skill:guhuo' in request.choices
    assert session.ai.decide(session.state, request).value == 'skill:guhuo'
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'skill:guhuo'))
    request = session.engine.pending_request
    assert session.ai.decide(session.state, request).value == 'basic.slash'
    session.engine.submit_decision(Decision(request.request_id, 'p1', 'basic.slash'))
    request = session.engine.pending_request
    assert session.ai.decide(session.state, request).value == material

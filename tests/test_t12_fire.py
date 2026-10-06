"""Targeted classic Fire skill and reusable pindian tests."""
from dataclasses import replace
import pytest

from sanguosha.engine.fire import (QiangxiAction, QiangxiHandler, QuhuAction,
                                   NiepanOffer, FireViewAsTrick, TianyiAction,
                                   ShuangxiongAction, LuanjiAction, FireHandLimit)
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.military_basics import MilitaryDamageAction
from sanguosha.engine.military_basics import MilitaryStrike
from sanguosha.engine.response import RespondWithCardAction
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.engine.pindian import PindianAction
from sanguosha.engine.requests import Decision, RequestType, PASS_RESPONSE
from sanguosha.model.enums import EquipmentSlot, Phase, Suit, Identity, PlayerStatus
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession
from test_t6_military_basics import put


def fire_game(character_id='fire_dian_wei'):
    session = GameSession.new_game(military=True, five_generals=True)
    session.state.players['p1'].character_id = character_id
    session.state.current_player_id = 'p1'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p1', 1)
    return session


def drive(session, choose, limit=80):
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


def test_qiangxi_hp_cost_uses_hp_loss_then_damage():
    session = fire_game()
    before = session.state.players['p1'].hp
    session.engine.start_action(QiangxiAction('fire-qiangxi-hp', 'p1'))
    drive(session, lambda request: (
        'hp' if request.request_type is RequestType.CHOOSE_OPTION else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert session.state.players['p1'].hp == before - 1
    assert session.state.players['p2'].hp == 3
    assert session.state.play_usage.count('skill.qiangxi') == 1
    assert any(event.__class__.__name__ == 'DamageDealtEvent'
               and event.target_id == 'p2' for event in session.events.events)
    assert not any(event.__class__.__name__ == 'DamageDealtEvent'
                   and event.target_id == 'p1' for event in session.events.events)


@pytest.mark.parametrize('zone', [ZoneType.HAND, ZoneType.EQUIPMENT])
def test_qiangxi_weapon_cost_from_hand_or_equipment(zone):
    session = fire_game()
    before = session.state.players['p1'].hp
    slot = EquipmentSlot.WEAPON if zone is ZoneType.EQUIPMENT else None
    weapon = put(session, 'equipment.weapon.serpent_spear', 'p1', zone, slot)
    session.engine.start_action(QiangxiAction('fire-qiangxi-weapon', 'p1'))
    drive(session, lambda request: (
        'weapon' if request.request_type is RequestType.CHOOSE_OPTION else
        weapon if request.request_type is RequestType.CHOOSE_CARD else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        request.timeout_value()))
    assert session.state.players['p1'].hp == before
    assert session.state.players['p2'].hp == 3
    assert weapon in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_qiangxi_range_and_once_per_play_phase():
    session = fire_game()
    handler = QiangxiHandler(session.skills, None, session.definitions)
    assert 'p3' not in handler.targets(session.state, 'p1')
    put(session, 'equipment.weapon.halberd', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    assert 'p3' in handler.targets(session.state, 'p1')
    session.state.play_usage.record('skill.qiangxi')
    assert not handler.available(session.state, 'p1')


def test_qiangxi_dying_after_hp_cost_stops_damage():
    session = fire_game()
    session.state.players['p1'].hp = 1
    session.engine.start_action(QiangxiAction('fire-qiangxi-dying', 'p1'))
    drive(session, lambda request: (
        'hp' if request.request_type is RequestType.CHOOSE_OPTION else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert not session.state.players['p1'].is_alive
    assert session.state.players['p2'].hp == 4


@pytest.mark.parametrize(('first_rank', 'second_rank', 'won'), [
    (13, 1, True), (1, 13, False), (7, 7, False),
])
def test_pindian_private_choices_reveal_then_discard(first_rank, second_rank, won):
    session = fire_game('fire_xun_yu')
    first = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    second = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    session.state.cards[first] = replace(session.state.cards[first], rank=first_rank)
    session.state.cards[second] = replace(session.state.cards[second], rank=second_rank)
    session.engine.start_action(PindianAction('fire-pindian', 'p1', 'p2'))
    request = session.engine.pending_request
    assert request.player_id == 'p1'
    session.engine.submit_decision(Decision(request.request_id, 'p1', first))
    request = session.engine.pending_request
    assert request.player_id == 'p2' and first not in request.eligible_card_ids
    assert first in session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    session.engine.submit_decision(Decision(request.request_id, 'p2', second))
    assert session.engine.last_result is won
    assert first in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert second in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


@pytest.mark.parametrize('won', [True, False])
def test_quhu_pindian_win_or_loss_deals_correct_damage(won):
    session = fire_game('fire_xun_yu')
    session.state.players['p1'].hp = 2
    source = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    opponent = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    session.state.cards[source] = replace(session.state.cards[source], rank=13 if won else 1)
    session.state.cards[opponent] = replace(session.state.cards[opponent], rank=1 if won else 13)
    session.engine.start_action(QuhuAction('fire-quhu', 'p1'))
    drive(session, lambda request: (
        'p3' if request.request_type is RequestType.CHOOSE_PLAYER and '受伤角色' in request.prompt else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        source if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p1' else
        opponent if request.request_type is RequestType.CHOOSE_CARD else
        False if request.request_type is RequestType.YES_NO else request.timeout_value()))
    assert session.state.play_usage.count('skill.quhu') == 1
    assert session.state.players['p3'].hp == (3 if won else 4)
    assert session.state.players['p1'].hp == (2 if won else 1)


def test_jieming_triggers_per_damage_point_and_caps_each_draw_at_five():
    session = fire_game('fire_xun_yu')
    owner_hp = session.state.players['p1'].hp
    for pid in ('p2', 'p3'):
        session.state.players[pid].max_hp = 10
    before = {pid: len(session.state.cards_in(ZoneRef(ZoneType.HAND, pid)))
              for pid in ('p2', 'p3')}
    session.engine.start_action(MilitaryDamageAction('fire-jieming', 'p2', 'p1', 2))
    drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO else
        ('p2' if ':target:0' in request.request_id else 'p3')
        if request.request_type is RequestType.CHOOSE_PLAYER else request.timeout_value()))
    assert session.state.players['p1'].hp == owner_hp - 2
    for pid in ('p2', 'p3'):
        assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, pid))) == before[pid] + 5


def test_niepan_clears_areas_draws_three_and_recovers_once():
    session = fire_game('fire_pang_tong')
    player = session.state.players['p1']
    player.max_hp = 4
    player.hp = 1
    player.chained = True
    player.face_up = False
    put(session, 'equipment.weapon.serpent_spear', 'p1', ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    put(session, 'delayed.indulgence', 'p1', ZoneType.JUDGMENT)
    session.engine.start_action(MilitaryDamageAction('fire-niepan', 'p2', 'p1', 2))
    drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO and '涅槃' in request.prompt else
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert player.hp == 3
    assert player.is_alive and player.face_up and not player.chained
    assert player.marks['niepan_used'] == 1
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == 3
    assert not session.state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON))
    assert not session.state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p1'))
    player.hp = 0
    assert NiepanOffer(session.skills)(session.state, 'p1', 'again') is None


@pytest.mark.parametrize('targets', [(), ('p2', 'p3')])
def test_lianhuan_recasts_or_chains_two_targets(targets):
    session = fire_game('fire_pang_tong')
    hand = ZoneRef(ZoneType.HAND, 'p1')
    material = session.state.cards_in(hand)[0]
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.CLUB)
    before = len(session.state.cards_in(hand))
    session.engine.start_action(FireViewAsTrick('fire-lianhuan', 'p1', material, 'lianhuan'))
    drive(session, lambda request: (
        targets if request.request_type is RequestType.CHOOSE_PLAYERS else
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    if targets:
        assert session.state.players['p2'].chained and session.state.players['p3'].chained
        assert len(session.state.cards_in(hand)) == before - 1
    else:
        assert len(session.state.cards_in(hand)) == before


def test_bazhen_acts_as_eight_trigrams_without_physical_armor():
    session = fire_game('fire_dian_wei')
    session.state.players['p2'].character_id = 'fire_wolong'
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.HEART)
    slash = put(session, 'basic.slash', 'p1')
    before = session.state.players['p2'].hp
    session.engine.start_action(MilitaryStrike('fire-bazhen', 'p1', 'p2', slash, 'basic.dodge'))
    seen = drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO and '八卦阵' in request.prompt else
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert any('八卦阵' in request.prompt for request in seen)
    assert session.state.players['p2'].hp == before


def test_huoji_uses_red_hand_as_fire_attack():
    session = fire_game('fire_wolong')
    hand = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    material, matching = hand[:2]
    target_card = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    for cid in (material, matching, target_card):
        session.state.cards[cid] = replace(session.state.cards[cid], suit=Suit.HEART)
    before = session.state.players['p2'].hp
    session.engine.start_action(FireViewAsTrick('fire-huoji', 'p1', material, 'huoji'))
    drive(session, lambda request: (
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        target_card if request.request_type is RequestType.CHOOSE_CARD else
        matching if request.request_type is RequestType.RESPOND_WITH_CARD and '火攻：' in request.prompt else
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert session.state.players['p2'].hp == before - 1
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_kanpo_uses_black_hand_as_nullification_response():
    session = fire_game('fire_wolong')
    material = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    session.state.cards[material] = replace(session.state.cards[material], suit=Suit.SPADE)
    session.engine.start_action(RespondWithCardAction('fire-kanpo', 'p1',
        'trick.nullification', 'source'))
    request = session.engine.pending_request
    choice = f'virtual:kanpo:{material}'
    assert choice in request.eligible_card_ids
    session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert isinstance(session.engine.last_result, VirtualCard)
    assert session.engine.last_result.material_ids == (material,)
    assert material in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


@pytest.mark.parametrize('won', [True, False])
def test_tianyi_win_or_loss_modifies_slash_for_turn(won):
    session = fire_game('fire_taishi_ci')
    source = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    opponent = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    session.state.cards[source] = replace(session.state.cards[source], rank=13 if won else 1)
    session.state.cards[opponent] = replace(session.state.cards[opponent], rank=1 if won else 13)
    session.engine.start_action(TianyiAction('fire-tianyi', 'p1'))
    drive(session, lambda request: (
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        source if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p1' else
        opponent if request.request_type is RequestType.CHOOSE_CARD else
        request.timeout_value()))
    assert session.state.play_usage.count('skill.tianyi') == 1
    slash = put(session, 'basic.slash', 'p1')
    rule = session.engine.registry.handler_for(UseCardAction('probe', 'p1', slash)).validator.rules.get('basic.slash')
    if not won:
        assert not rule.can_use(session.state, 'p1')
        assert rule.target_candidates(session.state, 'p1') == ()
        return
    assert rule.usage_limit(session.state, 'p1') == 2
    assert rule.target_bounds(session.state, 'p1', slash) == (1, 2)
    assert 'p3' in rule.target_candidates(session.state, 'p1')
    before = {pid: session.state.players[pid].hp for pid in ('p2', 'p3', 'p4')}
    session.engine.start_action(UseCardAction('fire-tianyi-first', 'p1', slash, ('p3', 'p4')))
    drive(session, lambda request: (
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert session.state.players['p3'].hp == before['p3'] - 1
    assert session.state.players['p4'].hp == before['p4'] - 1
    second = put(session, 'basic.slash', 'p1')
    session.engine.start_action(UseCardAction('fire-tianyi-second', 'p1', second, ('p2',)))
    drive(session, lambda request: (
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert session.state.players['p2'].hp == before['p2'] - 1
    assert session.state.play_usage.count('basic.slash') == 2


def test_pang_de_mashu_reduces_outgoing_distance_only():
    session = fire_game('fire_pang_de')
    distance = DistanceSystem(session.definitions)
    assert distance.distance_between(session.state, 'p1', 'p3') == 1
    assert distance.distance_between(session.state, 'p3', 'p1') == 2


@pytest.mark.parametrize('zone', ['hand', 'equipment'])
def test_mengjin_after_dodge_discards_target_card_without_revealing_hand_ids(zone):
    session = fire_game('fire_pang_de')
    slash = put(session, 'basic.slash', 'p1')
    hand = ZoneRef(ZoneType.HAND, 'p2')
    target_card = (session.state.cards_in(hand)[0] if zone == 'hand' else
                   put(session, 'equipment.weapon.serpent_spear', 'p2',
                       ZoneType.EQUIPMENT, EquipmentSlot.WEAPON))
    dodge = put(session, 'basic.dodge', 'p2')
    before_hp = session.state.players['p2'].hp
    session.engine.start_action(MilitaryStrike('fire-mengjin', 'p1', 'p2', slash, 'basic.dodge'))
    request = session.engine.pending_request
    assert request.player_id == 'p2'
    session.engine.submit_decision(Decision(request.request_id, 'p2', dodge))
    request = session.engine.pending_request
    assert request.player_id == 'p1' and '猛进' in request.prompt
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_OPTION
    assert not set(session.state.cards_in(hand)).intersection(request.choices)
    choice = 'hand:0' if zone == 'hand' else f'area:{target_card}'
    assert choice in request.choices
    session.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert session.engine.pending_request is None
    assert session.engine.stack.is_empty()
    assert session.state.players['p2'].hp == before_hp
    assert target_card in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_shuangxiong_replaces_draw_and_records_judgment_color():
    session = fire_game('fire_yan_liang_wen_chou')
    session.state.current_phase = Phase.DRAW
    session.engine.start_action(ShuangxiongAction('fire-shuangxiong', 'p1'))
    request = session.engine.pending_request
    assert request.request_type is RequestType.YES_NO
    session.engine.submit_decision(Decision(request.request_id, 'p1', True))
    assert session.engine.pending_request is None
    assert session.state.players['p1'].marks.get('skip_draw') == 1
    assert session.state.players['p1'].marks.get('shuangxiong_color') in (1, 2)
    assert session.state.play_usage.count('basic.slash') == 0


def test_luanji_uses_same_suit_pair_as_archery_attack():
    session = fire_game('fire_yuan_shao')
    hand = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    first, second = hand[:2]
    session.state.cards[first] = replace(session.state.cards[first], suit=Suit.HEART)
    session.state.cards[second] = replace(session.state.cards[second], suit=Suit.HEART)
    session.engine.start_action(LuanjiAction('fire-luanji', 'p1', (first, second)))
    drive(session, lambda request: (
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert session.state.play_usage.count('trick.archery_attack') == 1
    discard = session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert first in discard and second in discard


def test_xueyi_adds_two_hand_limit_per_living_qun_character():
    session = fire_game('fire_yuan_shao')
    session.state.players['p1'].identity = Identity.LORD
    session.state.players['p2'].character_id = 'fire_yan_liang_wen_chou'
    session.state.players['p3'].character_id = 'fire_yan_liang_wen_chou'
    limit = FireHandLimit(lambda state, pid: state.players[pid].hp, session.skills)
    assert limit(session.state, 'p1') == session.state.players['p1'].hp + 6
    session.state.players['p2'].status = PlayerStatus.DEAD
    assert limit(session.state, 'p1') == session.state.players['p1'].hp + 4


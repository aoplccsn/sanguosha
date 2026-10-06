"""Targeted classic Forest package tests."""
from dataclasses import replace
import json
import time

import pytest

from sanguosha.engine.death import DeathAction
from sanguosha.engine.card_rules import InvalidCardUse
from sanguosha.engine.dying import DyingAction
from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.forest import DimengAction, DuanliangUse, JiuchiUse, LuanwuAction
from sanguosha.engine.judgment import JudgmentAction, JudgmentPattern
from sanguosha.engine.military_basics import MilitaryDamageAction, MilitaryStrike
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.pindian import PindianAction
from sanguosha.engine.requests import Decision, RequestType, PASS_RESPONSE
from sanguosha.engine.turns import TurnAction
from sanguosha.model.enums import EquipmentSlot, Identity, Phase, Suit
from sanguosha.model.enums import SkillType
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.model.virtual_card import VirtualCard
from sanguosha.session import GameSession
from sanguosha.snapshot import snapshot_session, restore_session
from sanguosha.content.characters.myth import MYTH_CHARACTERS, MYTH_SKILL_CATALOGUE
from sanguosha.projection import project_for_human
from sanguosha.multiplayer.protocol import serialize_projection
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
from test_t6_military_basics import put


def forest_game(character_id='forest_caopi'):
    session = GameSession.new_game(military=True, five_generals=True)
    player = session.state.players['p1']
    character = session.skills.characters[character_id]
    player.character_id = character_id
    player.max_hp = character.max_hp
    player.hp = character.max_hp
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


def test_xingshang_claims_cards_before_death_cleanup():
    session = forest_game()
    victim_hand = set(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    assert victim_hand
    session.engine.start_action(DeathAction('forest-death', 'p2', None))
    request = session.engine.pending_request
    assert request.player_id == 'p1' and request.request_type is RequestType.YES_NO
    drive(session, lambda request: True if '行殇' in request.prompt else request.timeout_value())
    assert victim_hand.issubset(set(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))))
    assert not session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))


def test_xingshang_decline_leaves_death_cleanup_intact():
    session = forest_game()
    hand = set(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    equipment = put(session, 'equipment.weapon.serpent_spear', 'p2',
                    ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    judgment = put(session, 'delayed.indulgence', 'p2', ZoneType.JUDGMENT)
    session.engine.start_action(DeathAction('forest-decline', 'p2', None))
    drive(session, lambda request: False if '行殇' in request.prompt
          else request.timeout_value())
    discard = set(session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE)))
    assert hand | {equipment, judgment} <= discard


def test_xingshang_claims_hand_equipment_excludes_judgment_without_private_projection_leak():
    session = forest_game()
    hand = set(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    equipment = put(session, 'equipment.weapon.serpent_spear', 'p2',
                    ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    judgment = put(session, 'delayed.indulgence', 'p2', ZoneType.JUDGMENT)
    session.engine.start_action(DeathAction('forest-claim-zones', 'p2', None))
    drive(session, lambda request: True if '行殇' in request.prompt
          else request.timeout_value())
    gained = set(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    assert hand | {equipment} <= gained
    assert judgment in session.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    stranger = json.dumps(serialize_projection(project_for_human(
        session.state, session.definitions, 'p3', session.character_names)))
    assert all(card_id not in stranger for card_id in hand | {equipment})


def test_xingshang_does_not_trigger_for_owners_own_death():
    session = forest_game()
    session.engine.start_action(DeathAction('forest-own-death', 'p1', None))
    assert session.engine.pending_request is None


def test_fangzhu_draws_then_turns_over_and_skips_next_turn():
    session = forest_game()
    before = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p3')))
    hp_before = session.state.players['p1'].hp
    session.engine.start_action(MilitaryDamageAction('forest-damage', 'p2', 'p1', 1))
    drive(session, lambda request: (True if request.request_type is RequestType.YES_NO
        else 'p3' if request.request_type is RequestType.CHOOSE_PLAYER
        else request.timeout_value()))
    assert session.state.players['p1'].hp == hp_before - 1
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))) == before + 1
    assert not session.state.players['p3'].face_up
    session.engine.start_action(TurnAction('forest-skipped-turn', 'p3'))
    assert session.engine.pending_request is None
    assert session.state.players['p3'].face_up


def test_fangzhu_turns_face_down_target_face_up():
    session = forest_game()
    session.state.players['p3'].face_up = False
    session.engine.start_action(MilitaryDamageAction('forest-flip-back', 'p2', 'p1', 1))
    drive(session, lambda request: True if request.request_type is RequestType.YES_NO
          else 'p3' if request.request_type is RequestType.CHOOSE_PLAYER
          else request.timeout_value())
    assert session.state.players['p3'].face_up


def test_songwei_black_judgment_is_wei_players_decision():
    session = forest_game()
    session.state.players['p2'].character_id = 'forest_xuhuang'
    top = session.state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    session.state.cards[top] = replace(session.state.cards[top], suit=Suit.SPADE)
    before = len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(JudgmentAction('forest-judge', 'p2', JudgmentPattern()))
    request = session.engine.pending_request
    assert request.player_id == 'p2' and '颂威' in request.prompt
    drive(session, lambda request: True if '颂威' in request.prompt else request.timeout_value())
    assert len(session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 1


def test_songwei_uses_final_color_after_retrial():
    session = forest_game()
    state = session.state
    state.players['p2'].character_id = 'forest_xuhuang'
    state.players['p3'].character_id = 'simayi'
    assert session.skills.has(state, 'p3', 'guicai')
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    state.cards[top] = replace(state.cards[top], suit=Suit.HEART)
    replacement = state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))[0]
    state.cards[replacement] = replace(state.cards[replacement], suit=Suit.SPADE)
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(JudgmentAction('forest-retrial', 'p2', JudgmentPattern()))
    seen = drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO else
        replacement if request.request_type is RequestType.CHOOSE_CARD else
        request.timeout_value()))
    assert any('颂威' in request.prompt for request in seen)
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 1


@pytest.mark.parametrize('suit, lord', [
    (Suit.HEART, True), (Suit.SPADE, False),
])
def test_songwei_requires_black_judgment_and_lord(suit, lord):
    session = forest_game()
    state = session.state
    state.players['p2'].character_id = 'forest_xuhuang'
    if not lord:
        state.players['p1'].identity = Identity.REBEL
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    state.cards[top] = replace(state.cards[top], suit=suit)
    session.engine.start_action(JudgmentAction('forest-no-songwei', 'p2', JudgmentPattern()))
    assert session.engine.pending_request is None


def test_duanliang_uses_black_basic_at_distance_two():
    session = forest_game('forest_xuhuang')
    state = session.state
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    material = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[material] = replace(state.cards[material], definition_id='basic.slash',
                                    suit=Suit.SPADE)
    session.engine.start_action(DuanliangUse('forest-duanliang', 'p1', material))
    request = session.engine.pending_request
    assert 'p3' in request.allowed_player_ids
    drive(session, lambda request: 'p3' if request.request_type is RequestType.CHOOSE_PLAYER
          else request.timeout_value())
    assert material in state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p3'))
    assert state.metadata['virtual_delayed_cards'][material] == 'delayed.supply_shortage'


@pytest.mark.parametrize('definition, suit', [
    ('basic.slash', Suit.HEART),
    ('trick.duel', Suit.SPADE),
])
def test_duanliang_rejects_red_basic_and_black_trick(definition, suit):
    session = forest_game('forest_xuhuang')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    material = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[material] = replace(state.cards[material],
                                    definition_id=definition, suit=suit)
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(DuanliangUse('forest-invalid-material', 'p1', material))


def test_duanliang_accepts_black_equipment_from_hand():
    session = forest_game('forest_xuhuang')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    material = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[material] = replace(state.cards[material],
        definition_id='equipment.weapon.serpent_spear', suit=Suit.SPADE)
    session.engine.start_action(DuanliangUse('forest-black-equipment', 'p1', material))
    drive(session, lambda request: 'p3' if request.request_type is RequestType.CHOOSE_PLAYER
          else request.timeout_value())
    assert material in state.cards_in(ZoneRef(ZoneType.JUDGMENT, 'p3'))


def test_duanliang_rejects_distance_three_after_defensive_horse():
    session = forest_game('forest_xuhuang')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    put(session, 'equipment.horse.jueying', 'p3', ZoneType.EQUIPMENT,
        EquipmentSlot.DEFENSIVE_HORSE)
    material = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[material] = replace(state.cards[material],
                                    definition_id='basic.slash', suit=Suit.SPADE)
    session.engine.start_action(DuanliangUse('forest-distance-three', 'p1', material))
    request = session.engine.pending_request
    assert 'p3' not in request.allowed_player_ids
    drive(session, lambda pending: pending.timeout_value())


@pytest.mark.parametrize('character_id, distance_two_legal', [
    ('forest_xuhuang', True), ('forest_menghuo', False),
])
def test_physical_supply_shortage_uses_xu_huangs_range_only(
        character_id, distance_two_legal):
    session = forest_game(character_id)
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    card_id = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card_id] = replace(state.cards[card_id],
                                   definition_id='delayed.supply_shortage')
    session.engine.start_action(UseCardAction('forest-physical-shortage', 'p1', card_id))
    request = session.engine.pending_request
    assert ('p3' in request.allowed_player_ids) is distance_two_legal
    drive(session, lambda pending: ('p3' if distance_two_legal else 'p2')
          if pending.request_type is RequestType.CHOOSE_PLAYER
          else pending.timeout_value())


def test_huoshou_ignores_savage_and_becomes_damage_source():
    session = forest_game('forest_menghuo')
    card_id = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    session.state.cards[card_id] = replace(session.state.cards[card_id],
                                          definition_id='trick.savage_assault')
    hp_before = session.state.players['p1'].hp
    session.state.current_player_id = 'p2'
    session.state.current_phase = Phase.PLAY
    session.state.turn_number = 1
    session.state.play_usage = PlayUsageState('p2', 1)
    session.engine.start_action(UseCardAction('forest-huoshou', 'p2', card_id))
    drive(session, lambda request: PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD
          else request.timeout_value())
    assert session.state.players['p1'].hp == hp_before
    assert any(event.__class__.__name__ == 'DamageDealtEvent'
               and event.source_id == 'p1' and event.target_id == 'p3'
               for event in session.events.events)


def test_zaiqi_replaces_draw_with_reveal_recovery_and_gain():
    session = forest_game('forest_menghuo')
    state = session.state
    state.players['p1'].hp = state.players['p1'].max_hp - 2
    state.current_player_id = 'p1'
    state.turn_number = 1
    first, second = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[:2]
    state.cards[first] = replace(state.cards[first], suit=Suit.HEART)
    state.cards[second] = replace(state.cards[second], suit=Suit.SPADE)
    hand_before = set(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(PhaseAction('forest-zaiqi', 'p1', Phase.DRAW))
    drive(session, lambda request: True if '再起' in request.prompt else request.timeout_value())
    assert state.players['p1'].hp == state.players['p1'].max_hp - 1
    assert first in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert second in state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == len(hand_before) + 1


@pytest.mark.parametrize('wounded', [False, True])
def test_zaiqi_normal_draw_when_unwounded_or_declined(wounded):
    session = forest_game('forest_menghuo')
    state = session.state
    if wounded:
        state.players['p1'].hp -= 1
    state.current_player_id = 'p1'
    state.turn_number = 1
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    event_count = len(session.events.events)
    session.engine.start_action(PhaseAction('forest-zaiqi-normal', 'p1', Phase.DRAW))
    seen = drive(session, lambda request: False if '再起' in request.prompt
                 else request.timeout_value())
    assert any('再起' in request.prompt for request in seen) is wounded
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 2
    assert not any(getattr(event, 'event_type', None) == 'card_revealed'
                   for event in session.events.events[event_count:])


def test_juxiang_captures_other_players_completed_savage_use():
    session = forest_game('forest_zhurong')
    state = session.state
    card_id = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[card_id] = replace(state.cards[card_id], definition_id='trick.savage_assault')
    hp_before = state.players['p1'].hp
    state.current_player_id = 'p2'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p2', 1)
    session.engine.start_action(UseCardAction('forest-juxiang', 'p2', card_id))
    drive(session, lambda request: PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD
          else request.timeout_value())
    assert state.players['p1'].hp == hp_before
    assert card_id in state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert card_id not in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_juxiang_does_not_capture_own_savage_use():
    session = forest_game('forest_zhurong')
    state = session.state
    card_id = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[card_id] = replace(state.cards[card_id],
                                   definition_id='trick.savage_assault')
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    session.engine.start_action(UseCardAction('forest-own-savage', 'p1', card_id))
    drive(session, lambda request: PASS_RESPONSE
          if request.request_type is RequestType.RESPOND_WITH_CARD
          else request.timeout_value())
    assert card_id in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert card_id not in state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))


def test_lieren_uses_pindian_and_hides_opponents_hand_ids():
    session = forest_game('forest_zhurong')
    state = session.state
    source_card = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    target_card = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[source_card] = replace(state.cards[source_card],
                                       definition_id='basic.slash', rank=13)
    state.cards[target_card] = replace(state.cards[target_card], rank=1)
    hp_before = state.players['p2'].hp
    hand_before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(MilitaryStrike('forest-lieren', 'p1', 'p2',
                                               source_card, 'basic.dodge'))
    seen = drive(session, lambda request: (
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        True if '烈刃' in request.prompt and request.request_type is RequestType.YES_NO else
        source_card if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p1' else
        target_card if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p2' else
        'random_hand' if request.request_type is RequestType.CHOOSE_OPTION and '烈刃' in request.prompt else
        request.timeout_value()))
    assert state.players['p2'].hp == hp_before - 1
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == hand_before
    gain = next(request for request in seen if request.request_type is RequestType.CHOOSE_OPTION
                and '烈刃' in request.prompt)
    assert all(cid not in gain.choices for cid in state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))


@pytest.mark.parametrize('accept', [False, True])
def test_lieren_decline_or_tied_pindian_does_not_gain(accept):
    session = forest_game('forest_zhurong')
    state = session.state
    own = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    theirs = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[own] = replace(state.cards[own], definition_id='basic.slash', rank=9)
    state.cards[theirs] = replace(state.cards[theirs], rank=9)
    session.engine.start_action(MilitaryStrike('forest-lieren-tie', 'p1', 'p2',
                                               own, 'basic.dodge'))
    seen = drive(session, lambda request: (
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        accept if '烈刃' in request.prompt and request.request_type is RequestType.YES_NO else
        own if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p1' else
        theirs if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p2' else
        request.timeout_value()))
    assert not any('烈刃：选择' in request.prompt for request in seen)
    assert theirs not in state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    assert (theirs in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))) is accept


def test_lieren_equipment_gain_survives_snapshot_without_hand_leak():
    session = forest_game('forest_zhurong')
    state = session.state
    own = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    theirs = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    equipment = put(session, 'equipment.weapon.serpent_spear', 'p2',
                    ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    state.cards[own] = replace(state.cards[own], definition_id='basic.slash', rank=13)
    state.cards[theirs] = replace(state.cards[theirs], rank=1)
    session.engine.start_action(MilitaryStrike('forest-lieren-snapshot', 'p1', 'p2',
                                               own, 'basic.dodge'))
    for _ in range(30):
        request = session.engine.pending_request
        assert request is not None
        if '烈刃：选择' in request.prompt:
            break
        choice = (PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
                  True if '烈刃' in request.prompt and request.request_type is RequestType.YES_NO else
                  own if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p1' else
                  theirs if request.request_type is RequestType.CHOOSE_CARD and request.player_id == 'p2' else
                  request.timeout_value())
        session.engine.submit_decision(Decision(request.request_id, request.player_id, choice))
    assert f'equipment:{equipment}' in request.choices
    restored = restore_session(snapshot_session(session))
    pending = restored.engine.pending_request
    assert pending.request_id == request.request_id
    hidden = restored.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    stranger = json.dumps(serialize_projection(project_for_human(
        restored.state, restored.definitions, 'p3', restored.character_names)))
    assert all(cid not in stranger for cid in hidden)
    restored.engine.submit_decision(Decision(pending.request_id, pending.player_id,
                                             f'equipment:{equipment}'))
    drive(restored, lambda later: later.timeout_value())
    assert equipment in restored.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))


def test_forest_pindian_ai_uses_highest_rank_in_hand():
    session = forest_game('forest_zhurong')
    hand = session.state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    low, high = hand[:2]
    session.state.cards[low] = replace(session.state.cards[low], rank=1)
    session.state.cards[high] = replace(session.state.cards[high], rank=13)
    session.engine.start_action(PindianAction('forest-ai-pindian', 'p1', 'p2'))
    request = session.engine.pending_request
    assert session.ai.decide(session.state, request).value == high


def test_forest_catalogue_has_rule_text_and_types():
    skills = {skill.id: skill for skill in MYTH_SKILL_CATALOGUE}
    ordinary = [character for character in MYTH_CHARACTERS
                if character.id.startswith('forest_') and '_god_' not in character.id]
    assert len(ordinary) == 8
    expected = {
        'xingshang': SkillType.TRIGGERED, 'fangzhu': SkillType.TRIGGERED,
        'songwei': SkillType.TRIGGERED, 'duanliang': SkillType.VIEW_AS,
        'huoshou': SkillType.LOCKED, 'zaiqi': SkillType.TRIGGERED,
        'juxiang': SkillType.LOCKED, 'lieren': SkillType.TRIGGERED,
        'yinghun': SkillType.TRIGGERED, 'haoshi': SkillType.TRIGGERED,
        'dimeng': SkillType.ACTIVE, 'wansha': SkillType.LOCKED,
        'luanwu': SkillType.LIMITED, 'weimu': SkillType.LOCKED,
        'jiuchi': SkillType.VIEW_AS, 'roulin': SkillType.LOCKED,
        'benghuai': SkillType.LOCKED, 'baonue': SkillType.TRIGGERED,
    }
    assert {skill_id for character in ordinary for skill_id in character.skill_ids} == set(expected)
    for skill_id, kind in expected.items():
        assert skills[skill_id].skill_type is kind
        assert len(skills[skill_id].description) > 15
        assert '规则摘要' not in skills[skill_id].description


def test_yinghun_draws_two_then_target_discards_one():
    session = forest_game('forest_sunjian')
    state = session.state
    state.players['p1'].hp -= 2
    state.current_player_id = 'p1'
    state.turn_number = 1
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    session.engine.start_action(PhaseAction('forest-yinghun', 'p1', Phase.PREPARATION))
    seen = drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        'draw_x_discard_one' if request.request_type is RequestType.CHOOSE_OPTION else
        request.eligible_card_ids[:request.min_count]
        if request.request_type is RequestType.CHOOSE_CARDS else request.timeout_value()))
    assert any('英魂' in request.prompt for request in seen)
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == before + 1


def test_yinghun_draw_one_then_discard_missing_hp():
    session = forest_game('forest_sunjian')
    state = session.state
    state.players['p1'].hp -= 2
    state.current_player_id, state.turn_number = 'p1', 1
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    session.engine.start_action(PhaseAction('forest-yinghun-other-mode', 'p1', Phase.PREPARATION))
    seen = drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        'draw_one_discard_x' if request.request_type is RequestType.CHOOSE_OPTION else
        request.eligible_card_ids[:request.min_count]
        if request.request_type is RequestType.CHOOSE_CARDS else request.timeout_value()))
    discard = next(request for request in seen
                   if request.request_type is RequestType.CHOOSE_CARDS)
    assert discard.min_count == discard.max_count == 2
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == before - 1


@pytest.mark.parametrize('wounded', [False, True])
def test_yinghun_unwounded_or_declined_does_not_change_target_hand(wounded):
    session = forest_game('forest_sunjian')
    state = session.state
    if wounded:
        state.players['p1'].hp -= 1
    state.current_player_id, state.turn_number = 'p1', 1
    before = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    session.engine.start_action(PhaseAction('forest-yinghun-decline', 'p1', Phase.PREPARATION))
    seen = drive(session, lambda request: False if '英魂' in request.prompt
                 else request.timeout_value())
    assert any('英魂' in request.prompt for request in seen) is wounded
    assert state.cards_in(ZoneRef(ZoneType.HAND, 'p2')) == before


def test_haoshi_gives_exact_half_to_lowest_hand_player():
    session = forest_game('forest_lusu')
    state = session.state
    state.current_player_id = 'p1'
    state.turn_number = 1
    own_before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    target_before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p2')))
    session.engine.start_action(PhaseAction('forest-haoshi', 'p1', Phase.DRAW))
    seen = drive(session, lambda request: (
        True if '好施' in request.prompt and request.request_type is RequestType.YES_NO else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        request.eligible_card_ids[:request.min_count]
        if request.request_type is RequestType.CHOOSE_CARDS else request.timeout_value()))
    give = next(request for request in seen if request.request_type is RequestType.CHOOSE_CARDS)
    assert give.min_count == give.max_count == (own_before + 4) // 2
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == own_before + 4 - give.min_count
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))) == target_before + give.min_count


def test_haoshi_decline_draws_two_and_does_not_force_gift():
    session = forest_game('forest_lusu')
    state = session.state
    state.current_player_id, state.turn_number = 'p1', 1
    before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    session.engine.start_action(PhaseAction('forest-haoshi-decline', 'p1', Phase.DRAW))
    seen = drive(session, lambda request: False if '好施' in request.prompt
                 else request.timeout_value())
    assert any('好施' in request.prompt for request in seen)
    assert not any(request.request_type is RequestType.CHOOSE_CARDS for request in seen)
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == before + 2


def test_haoshi_only_offers_lowest_hand_recipient():
    session = forest_game('forest_lusu')
    state = session.state
    state.current_player_id, state.turn_number = 'p1', 1
    for pid in ('p3', 'p4', 'p5'):
        put(session, 'basic.slash', pid, ZoneType.HAND)
    session.engine.start_action(PhaseAction('forest-haoshi-lowest', 'p1', Phase.DRAW))
    seen = drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO and '好施' in request.prompt else
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER else
        request.eligible_card_ids[:request.min_count]
        if request.request_type is RequestType.CHOOSE_CARDS else request.timeout_value()))
    recipient = next(request for request in seen
                     if request.request_type is RequestType.CHOOSE_PLAYER and '好施' in request.prompt)
    assert recipient.allowed_player_ids == ('p2',)


def test_dimeng_swaps_entire_hands_once_per_turn():
    session = forest_game('forest_lusu')
    state = session.state
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    first = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    second = state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))
    session.engine.start_action(DimengAction('forest-dimeng', 'p1'))
    drive(session, lambda request: 'p2' if '第一名' in request.prompt else 'p3')
    assert state.cards_in(ZoneRef(ZoneType.HAND, 'p2')) == second
    assert state.cards_in(ZoneRef(ZoneType.HAND, 'p3')) == first
    assert state.play_usage.count('skill.dimeng') == 1


def test_dimeng_pays_hand_difference_and_swap_stays_private():
    session = forest_game('forest_lusu')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    put(session, 'basic.slash', 'p2', ZoneType.HAND)
    own_before = len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1')))
    first = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    second = state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))
    assert len(first) == len(second) + 1
    session.engine.start_action(DimengAction('forest-dimeng-cost', 'p1'))
    seen = drive(session, lambda request: (
        'p2' if request.request_type is RequestType.CHOOSE_PLAYER and '第一名' in request.prompt else
        'p3' if request.request_type is RequestType.CHOOSE_PLAYER else
        request.eligible_card_ids[:request.min_count]
        if request.request_type is RequestType.CHOOSE_CARDS else request.timeout_value()))
    cost = next(request for request in seen if request.request_type is RequestType.CHOOSE_CARDS)
    assert cost.min_count == cost.max_count == 1
    assert len(state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))) == own_before - 1
    assert state.cards_in(ZoneRef(ZoneType.HAND, 'p2')) == second
    assert state.cards_in(ZoneRef(ZoneType.HAND, 'p3')) == first
    stranger = json.dumps(serialize_projection(project_for_human(
        state, session.definitions, 'p4', session.character_names)))
    assert all(card_id not in stranger for card_id in first + second)


def test_wansha_limits_peach_rescue_to_owner_and_dying_player():
    session = forest_game('forest_jia_xu')
    state = session.state
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.players['p2'].hp = 0
    session.engine.start_action(DyingAction('forest-wansha', 'p2', 'p1'))
    seen = drive(session, lambda request: request.timeout_value())
    rescuers = {request.player_id for request in seen
                if request.request_type is RequestType.RESPOND_WITH_CARD
                and request.required_definition_id == 'basic.peach'}
    assert rescuers == {'p1', 'p2'}


def test_roulin_requires_two_dodges_against_female_target():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.players['p2'].character_id = 'forest_zhurong'
    slash = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[slash] = replace(state.cards[slash], definition_id='basic.slash')
    dodges = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[:2]
    for card_id in dodges:
        state.cards[card_id] = replace(state.cards[card_id], definition_id='basic.dodge')
    before = state.players['p2'].hp
    session.engine.start_action(MilitaryStrike('forest-roulin', 'p1', 'p2',
                                               slash, 'basic.dodge'))
    seen = drive(session, lambda request: next(
        (card_id for card_id in dodges if card_id in request.eligible_card_ids),
        request.timeout_value()) if request.request_type is RequestType.RESPOND_WITH_CARD
        else request.timeout_value())
    dodge_requests = [request for request in seen
                      if request.required_definition_id == 'basic.dodge']
    assert len(dodge_requests) == 2
    assert all(request.player_id == 'p2' for request in dodge_requests)
    assert state.players['p2'].hp == before


def test_benghuai_can_reduce_max_hp_and_clamps_current_hp():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.current_player_id = 'p1'
    state.turn_number = 1
    session.engine.start_action(PhaseAction('forest-benghuai', 'p1', Phase.FINISH))
    seen = drive(session, lambda request: 'lose_max_hp'
                 if '崩坏' in request.prompt else request.timeout_value())
    assert any('崩坏' in request.prompt for request in seen)
    assert state.players['p1'].max_hp == 7
    assert state.players['p1'].hp == 7


def test_baonue_spade_judgment_recovers_dong_zhuo():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.players['p1'].hp -= 1
    state.players['p2'].character_id = 'forest_jia_xu'
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    state.cards[top] = replace(state.cards[top], suit=Suit.SPADE)
    session.engine.start_action(MilitaryDamageAction('forest-baonue', 'p2', 'p3', 1))
    seen = drive(session, lambda request: True if '暴虐' in request.prompt
                 else request.timeout_value())
    assert any(request.player_id == 'p2' and '暴虐' in request.prompt
               for request in seen)
    assert state.players['p1'].hp == state.players['p1'].max_hp


def test_luanwu_forces_nearest_slash_then_other_players_lose_hp():
    session = forest_game('forest_jia_xu')
    state = session.state
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    for pid in ('p2', 'p3', 'p4', 'p5'):
        for card_id in state.cards_in(ZoneRef(ZoneType.HAND, pid)):
            state.cards[card_id] = replace(state.cards[card_id], definition_id='basic.dodge')
    slash = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[slash] = replace(state.cards[slash], definition_id='basic.slash')
    hp_before = {pid: state.players[pid].hp for pid in ('p2', 'p3', 'p4', 'p5')}
    session.engine.start_action(LuanwuAction('forest-luanwu', 'p1'))
    seen = drive(session, lambda request: (
        'slash' if request.request_type is RequestType.CHOOSE_OPTION
            and '乱武' in request.prompt else
        slash if request.request_type is RequestType.CHOOSE_CARD
            and '乱武' in request.prompt else
        'p3' if request.request_type is RequestType.CHOOSE_PLAYER
            and '乱武' in request.prompt and 'p3' in request.allowed_player_ids else
        PASS_RESPONSE if request.request_type is RequestType.RESPOND_WITH_CARD else
        request.timeout_value()))
    assert any(request.player_id == 'p2' and '乱武' in request.prompt for request in seen)
    assert slash in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    assert state.players['p2'].hp == hp_before['p2']
    assert state.players['p3'].hp == hp_before['p3'] - 2
    assert state.players['p4'].hp == hp_before['p4'] - 1
    assert state.players['p5'].hp == hp_before['p5'] - 1
    assert state.players['p1'].marks['luanwu_used'] == 1


def test_jiuchi_uses_spade_hand_card_as_wine():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.current_player_id = 'p1'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p1', 1)
    material = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[material] = replace(state.cards[material], definition_id='basic.slash', suit=Suit.SPADE)
    session.engine.start_action(JiuchiUse('forest-jiuchi', 'p1', material))
    assert session.engine.pending_request is None
    assert state.players['p1'].marks['wine'] == 1
    assert state.play_usage.count('basic.wine') == 1
    assert material in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_jiuchi_spade_hand_card_can_self_rescue():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.players['p1'].hp = 0
    material = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[material] = replace(state.cards[material], definition_id='basic.slash', suit=Suit.SPADE)
    session.engine.start_action(DyingAction('forest-jiuchi-dying', 'p1', None))
    request = session.engine.pending_request
    assert f'virtual:jiuchi:{material}' in request.eligible_card_ids
    drive(session, lambda pending: f'virtual:jiuchi:{material}'
          if pending.request_type is RequestType.RESPOND_WITH_CARD
          and f'virtual:jiuchi:{material}' in pending.eligible_card_ids
          else pending.timeout_value())
    assert state.players['p1'].hp == 1
    assert material in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


def test_weimu_excludes_black_trick_target_but_allows_red_trick():
    for suit, allowed in ((Suit.SPADE, False), (Suit.HEART, True)):
        session = forest_game('forest_jia_xu')
        state = session.state
        state.current_player_id = 'p2'
        state.current_phase = Phase.PLAY
        state.turn_number = 1
        state.play_usage = PlayUsageState('p2', 1)
        card_id = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
        state.cards[card_id] = replace(state.cards[card_id],
                                       definition_id='trick.duel', suit=suit)
        session.engine.start_action(UseCardAction('forest-weimu-duel', 'p2', card_id))
        request = session.engine.pending_request
        assert ('p1' in request.allowed_player_ids) is allowed
        drive(session, lambda pending: ('p1' if allowed else 'p3')
              if pending.request_type is RequestType.CHOOSE_PLAYER
              else PASS_RESPONSE if pending.request_type is RequestType.RESPOND_WITH_CARD
              else pending.timeout_value())


def test_weimu_ignores_black_savage_assault_effect():
    session = forest_game('forest_jia_xu')
    state = session.state
    state.current_player_id = 'p2'
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState('p2', 1)
    card_id = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[card_id] = replace(state.cards[card_id],
                                   definition_id='trick.savage_assault', suit=Suit.SPADE)
    before = state.players['p1'].hp
    session.engine.start_action(UseCardAction('forest-weimu-savage', 'p2', card_id))
    drive(session, lambda pending: PASS_RESPONSE
          if pending.request_type is RequestType.RESPOND_WITH_CARD
          else pending.timeout_value())
    assert state.players['p1'].hp == before


def test_wansha_only_limits_rescue_during_owner_turn():
    session = forest_game('forest_jia_xu')
    state = session.state
    state.current_player_id, state.current_phase = 'p3', Phase.PLAY
    state.players['p2'].hp = 0
    session.engine.start_action(DyingAction('forest-wansha-other-turn', 'p2', 'p3'))
    seen = drive(session, lambda request: request.timeout_value())
    rescuers = {request.player_id for request in seen
                if request.request_type is RequestType.RESPOND_WITH_CARD
                and request.required_definition_id == 'basic.peach'}
    assert {'p3', 'p4'}.issubset(rescuers)


def test_luanwu_cannot_be_used_twice():
    session = forest_game('forest_jia_xu')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    for pid in ('p2', 'p3', 'p4', 'p5'):
        for card_id in state.cards_in(ZoneRef(ZoneType.HAND, pid)):
            state.cards[card_id] = replace(state.cards[card_id], definition_id='basic.dodge')
    session.engine.start_action(LuanwuAction('forest-luanwu-once', 'p1'))
    assert state.players['p1'].marks['luanwu_used'] == 1
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(LuanwuAction('forest-luanwu-again', 'p1'))


def test_luanwu_pending_choice_restores_without_private_card_ids():
    session = forest_game('forest_jia_xu')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    slash = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[slash] = replace(state.cards[slash], definition_id='basic.slash')
    session.engine.start_action(LuanwuAction('forest-luanwu-restore', 'p1'))
    pending = session.engine.pending_request
    assert pending.player_id == 'p2' and '乱武' in pending.prompt
    restored = restore_session(snapshot_session(session))
    assert restored.engine.pending_request.request_id == pending.request_id
    stranger = json.dumps(serialize_projection(project_for_human(
        restored.state, restored.definitions, 'p4', restored.character_names)))
    assert slash not in stranger
    drive(restored, lambda request: 'lose_hp'
          if request.request_type is RequestType.CHOOSE_OPTION and '乱武' in request.prompt
          else request.timeout_value())
    assert restored.state.players['p1'].marks['luanwu_used'] == 1


@pytest.mark.parametrize('suit, allowed', [(Suit.SPADE, False), (Suit.HEART, True)])
def test_weimu_blocks_black_delayed_trick_targets(suit, allowed):
    session = forest_game('forest_jia_xu')
    state = session.state
    state.current_player_id, state.current_phase = 'p2', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p2', 1)
    card_id = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[card_id] = replace(state.cards[card_id],
                                   definition_id='delayed.indulgence', suit=suit)
    session.engine.start_action(UseCardAction('forest-weimu-delayed', 'p2', card_id))
    request = session.engine.pending_request
    assert ('p1' in request.allowed_player_ids) is allowed


@pytest.mark.parametrize('suit', [Suit.HEART, Suit.CLUB, Suit.DIAMOND])
def test_jiuchi_rejects_non_spade_material(suit):
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    material = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[material] = replace(state.cards[material], suit=suit)
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(JiuchiUse('forest-jiuchi-suit', 'p1', material))
    assert material in state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))


def test_jiuchi_rejects_equipped_spade_and_offers_hand_only():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    equipment = put(session, 'equipment.weapon.serpent_spear', 'p1',
                    ZoneType.EQUIPMENT, EquipmentSlot.WEAPON)
    state.cards[equipment] = replace(state.cards[equipment], suit=Suit.SPADE)
    hand = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))
    for card_id in hand:
        state.cards[card_id] = replace(state.cards[card_id], suit=Suit.HEART)
    with pytest.raises(InvalidCardUse):
        session.engine.start_action(JiuchiUse('forest-jiuchi-equipped', 'p1', equipment))
    assert equipment in state.cards_in(ZoneRef(ZoneType.EQUIPMENT, 'p1', EquipmentSlot.WEAPON))


@pytest.mark.parametrize('attacker_female,target_female,expected', [
    (False, True, 2), (True, False, 2), (False, False, 1),
])
def test_roulin_applies_only_across_female_dong_pair(attacker_female, target_female, expected):
    session = forest_game('forest_dong_zhuo')
    state = session.state
    if attacker_female:
        state.players['p1'].character_id = 'forest_zhurong'
        state.players['p2'].character_id = 'forest_dong_zhuo'
    elif target_female:
        state.players['p2'].character_id = 'forest_zhurong'
    slash = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    state.cards[slash] = replace(state.cards[slash], definition_id='basic.slash')
    session.engine.start_action(MilitaryStrike('forest-roulin-direction', 'p1', 'p2',
                                               slash, 'basic.dodge'))
    seen = drive(session, lambda request: PASS_RESPONSE
                 if request.request_type is RequestType.RESPOND_WITH_CARD
                 else request.timeout_value())
    dodges = [request for request in seen
              if request.required_definition_id == 'basic.dodge']
    assert len(dodges) == 1
    assert dodges[0].player_id == 'p2'
    from sanguosha.engine.military_basics import required_dodge_count
    assert required_dodge_count(state, 'p1', 'p2', session.skills) == expected


def test_roulin_first_dodge_then_reconnect_requires_second_and_pass_takes_damage():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.players['p2'].character_id = 'forest_zhurong'
    slash = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[0]
    dodge = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[slash] = replace(state.cards[slash], definition_id='basic.slash')
    state.cards[dodge] = replace(state.cards[dodge], definition_id='basic.dodge')
    for card_id in state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[1:]:
        state.cards[card_id] = replace(state.cards[card_id], definition_id='basic.slash')
    before = state.players['p2'].hp
    session.engine.start_action(MilitaryStrike('forest-roulin-restore', 'p1', 'p2',
                                               slash, 'basic.dodge'))
    first = session.engine.pending_request
    assert first.player_id == 'p2' and dodge in first.eligible_card_ids
    session.engine.submit_decision(Decision(first.request_id, 'p2', dodge))
    second = session.engine.pending_request
    assert second.player_id == 'p2' and second.request_id != first.request_id
    assert '第二张闪' in second.prompt
    restored = restore_session(snapshot_session(session))
    assert restored.engine.pending_request.request_id == second.request_id
    drive(restored, lambda request: PASS_RESPONSE
          if request.request_type is RequestType.RESPOND_WITH_CARD
          else request.timeout_value())
    assert restored.state.players['p2'].hp == before - 1
    assert dodge in restored.state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))


@pytest.mark.parametrize('owner_hp, other_hp, triggered', [
    (2, 3, False), (2, 2, False), (3, 2, True),
])
def test_benghuai_only_when_another_living_player_has_lower_hp(owner_hp, other_hp, triggered):
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.current_player_id, state.turn_number = 'p1', 1
    state.players['p1'].hp = owner_hp
    for pid in ('p2', 'p3', 'p4', 'p5'):
        state.players[pid].hp = 3
    state.players['p2'].hp = other_hp
    session.engine.start_action(PhaseAction('forest-benghuai-minimum', 'p1', Phase.FINISH))
    pending = session.engine.pending_request
    assert (pending is not None and '崩坏' in pending.prompt) is triggered
    if pending:
        drive(session, lambda request: 'lose_hp' if '崩坏' in request.prompt
              else request.timeout_value())


def test_benghuai_loses_hp_without_damage_and_restores_choice():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.current_player_id, state.turn_number = 'p1', 1
    before = state.players['p1'].hp
    session.engine.start_action(PhaseAction('forest-benghuai-hp', 'p1', Phase.FINISH))
    pending = session.engine.pending_request
    restored = restore_session(snapshot_session(session))
    assert restored.engine.pending_request.request_id == pending.request_id
    restored.engine.submit_decision(Decision(pending.request_id, 'p1', 'lose_hp'))
    assert restored.state.players['p1'].hp == before - 1
    assert any(getattr(event, 'event_type', '') == 'hp_lost' for event in restored.events.events)
    assert not any(type(event).__name__ == 'DamageDealtEvent'
                   for event in restored.events.events)


@pytest.mark.parametrize('source_character,lord_identity,expect_offer', [
    ('forest_jia_xu', Identity.LORD, True),
    ('forest_sunjian', Identity.LORD, False),
    ('forest_jia_xu', Identity.REBEL, False),
    ('forest_dong_zhuo', Identity.LORD, True),
])
def test_baonue_requires_other_qun_source_and_dong_lord(
        source_character, lord_identity, expect_offer):
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.players['p1'].identity = lord_identity
    state.players['p2'].character_id = source_character
    session.engine.start_action(MilitaryDamageAction('forest-baonue-eligibility', 'p2', 'p3', 1))
    seen = drive(session, lambda request: False if '暴虐' in request.prompt
                 else request.timeout_value())
    assert any(request.player_id == 'p2' and '暴虐' in request.prompt
               for request in seen) is expect_offer


def test_baonue_does_not_trigger_from_dong_own_damage():
    session = forest_game('forest_dong_zhuo')
    session.engine.start_action(MilitaryDamageAction('forest-baonue-self', 'p1', 'p2', 1))
    seen = drive(session, lambda request: request.timeout_value())
    assert not any('暴虐' in request.prompt for request in seen)


@pytest.mark.parametrize('suit,accept,healed', [
    (Suit.SPADE, True, True), (Suit.HEART, True, False),
    (Suit.SPADE, False, False),
])
def test_baonue_final_judgment_and_decline(suit, accept, healed):
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.players['p1'].hp -= 1
    state.players['p2'].character_id = 'forest_jia_xu'
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    state.cards[top] = replace(state.cards[top], suit=suit)
    before = state.players['p1'].hp
    session.engine.start_action(MilitaryDamageAction('forest-baonue-result', 'p2', 'p3', 1))
    request = session.engine.pending_request
    assert request.player_id == 'p2' and '暴虐' in request.prompt
    restored = restore_session(snapshot_session(session))
    assert restored.engine.pending_request.request_id == request.request_id
    drive(restored, lambda pending: accept if '暴虐' in pending.prompt
          else pending.timeout_value())
    assert restored.state.players['p1'].hp == before + int(healed)


@pytest.mark.parametrize('character_id', [
    'forest_caopi', 'forest_xuhuang', 'forest_menghuo', 'forest_zhurong',
    'forest_sunjian', 'forest_lusu', 'forest_jia_xu', 'forest_dong_zhuo',
])
def test_forest_ai_uses_authoritative_requests_without_stalling(character_id):
    session = forest_game(character_id)
    session.human_id = 'observer'
    steps = 0
    for _ in range(120):
        if not session.step_auto():
            break
        steps += 1
        session.state.__post_init__()
    assert steps >= 5
    request = session.engine.pending_request
    if request is not None:
        request.validate(session.ai.decide(session.state, request).value)


def test_forest_room_only_sends_luanwu_request_to_current_actor():
    messages = {f'p{index}': [] for index in range(1, 6)}
    room = MultiplayerRoom(seed=17)
    for index in range(1, 6):
        room.join(f'forest-{index}', messages[f'p{index}'].append)
    room.session = forest_game('forest_jia_xu')
    room.phase = RoomPhase.IN_GAME
    state = room.session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    slash = state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))[0]
    state.cards[slash] = replace(state.cards[slash], definition_id='basic.slash')
    room.session.engine.start_action(LuanwuAction('forest-room-luanwu', 'p1'))
    room.request_deadline = time.time() + 30
    for inbox in messages.values():
        inbox.clear()
    room._sync()
    assert any(message['type'] == 'PENDING_REQUEST' for message in messages['p2'])
    assert all(message['type'] != 'PENDING_REQUEST'
               for pid, inbox in messages.items() if pid != 'p2' for message in inbox)
    assert all(slash not in json.dumps(inbox, ensure_ascii=False)
               for pid, inbox in messages.items() if pid != 'p2')


def test_forest_full_match_ai_smoke():
    session = forest_game('forest_dong_zhuo')
    for pid, character_id in zip(('p2', 'p3', 'p4', 'p5'),
                                 ('forest_jia_xu', 'forest_zhurong',
                                  'forest_menghuo', 'forest_lusu')):
        character = session.skills.characters[character_id]
        player = session.state.players[pid]
        player.character_id = character_id
        player.max_hp = player.hp = character.max_hp
    session.human_id = 'observer'
    for _ in range(12000):
        if not session.step_auto():
            break
    session.state.__post_init__()
    assert session.state.status.value == 'finished'
    assert session.engine.pending_request is None
    assert session.engine.stack.is_empty()
    assert not session.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_jiuchi_virtual_wine_adds_damage_to_next_slash():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.current_player_id, state.current_phase = 'p1', Phase.PLAY
    state.turn_number, state.play_usage = 1, PlayUsageState('p1', 1)
    wine, slash = state.cards_in(ZoneRef(ZoneType.HAND, 'p1'))[:2]
    state.cards[wine] = replace(state.cards[wine], definition_id='basic.dodge', suit=Suit.SPADE)
    state.cards[slash] = replace(state.cards[slash], definition_id='basic.slash')
    session.engine.start_action(JiuchiUse('forest-jiuchi-wine-slash', 'p1', wine))
    virtual = session.engine.last_result
    assert isinstance(virtual, VirtualCard)
    assert virtual.definition_id == 'basic.wine' and virtual.material_ids == (wine,)
    assert wine in state.cards_in(ZoneRef(ZoneType.DISCARD_PILE))
    before = state.players['p2'].hp
    session.engine.start_action(UseCardAction('forest-jiuchi-slash', 'p1', slash, ('p2',)))
    drive(session, lambda request: PASS_RESPONSE
          if request.request_type is RequestType.RESPOND_WITH_CARD
          else request.timeout_value())
    assert state.players['p2'].hp == before - 2
    assert state.players['p1'].marks.get('wine', 0) == 0


def test_baonue_uses_final_spade_after_guicai_retrial():
    session = forest_game('forest_dong_zhuo')
    state = session.state
    state.players['p1'].hp -= 1
    state.players['p2'].character_id = 'forest_jia_xu'
    state.players['p3'].character_id = 'simayi'
    top = state.cards_in(ZoneRef(ZoneType.DRAW_PILE))[0]
    replacement = state.cards_in(ZoneRef(ZoneType.HAND, 'p3'))[0]
    state.cards[top] = replace(state.cards[top], suit=Suit.HEART)
    state.cards[replacement] = replace(state.cards[replacement], suit=Suit.SPADE)
    before = state.players['p1'].hp
    session.engine.start_action(MilitaryDamageAction('forest-baonue-retrial', 'p2', 'p4', 1))
    seen = drive(session, lambda request: (
        True if request.request_type is RequestType.YES_NO else
        replacement if request.request_type is RequestType.CHOOSE_CARD
        and request.player_id == 'p3' else request.timeout_value()))
    assert any('鬼才' in request.prompt for request in seen)
    assert state.players['p1'].hp == before + 1


@pytest.mark.parametrize('character_id,skill,action_kind', [
    ('forest_caopi', '放逐', 'damage'),
    ('forest_menghuo', '再起', 'draw'),
    ('forest_sunjian', '英魂', 'preparation'),
    ('forest_lusu', '好施', 'draw'),
    ('forest_lusu', '缔盟', 'dimeng'),
])
def test_forest_pending_skill_request_restores_without_repeating(
        character_id, skill, action_kind):
    session = forest_game(character_id)
    state = session.state
    state.current_player_id, state.turn_number = 'p1', 1
    if action_kind in ('draw', 'preparation') and skill != '好施':
        state.players['p1'].hp -= 1
    if action_kind == 'damage':
        action = MilitaryDamageAction('forest-restore-offer', 'p2', 'p1', 1)
    elif action_kind == 'draw':
        action = PhaseAction('forest-restore-offer', 'p1', Phase.DRAW)
    elif action_kind == 'preparation':
        action = PhaseAction('forest-restore-offer', 'p1', Phase.PREPARATION)
    else:
        state.current_phase, state.play_usage = Phase.PLAY, PlayUsageState('p1', 1)
        action = DimengAction('forest-restore-offer', 'p1')
    session.engine.start_action(action)
    request = session.engine.pending_request
    assert request is not None and skill in request.prompt
    restored = restore_session(snapshot_session(session))
    pending = restored.engine.pending_request
    assert pending.request_id == request.request_id
    assert pending.player_id == request.player_id
    assert pending.request_type is request.request_type
    assert pending.choices == request.choices
    assert pending.allowed_player_ids == request.allowed_player_ids
    drive(restored, lambda later: later.timeout_value())

"""Distance is calculated from living seats and the single equipment zone store."""

import pytest

from sanguosha.content.cards.basic import EquipmentSlashLimit, ReachableOpponent, SlashRule, register_basic_cards
from sanguosha.engine.card_moves import CardMoveService
from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.engine.card_rules import CardRuleRegistry, CardUseValidator, InvalidCardUse, TargetValidator
from sanguosha.engine.card_use import UseCardAction, UseCardActionHandler
from sanguosha.engine.distance import DistanceSystem
from sanguosha.engine.engine import GameEngine
from sanguosha.engine.events import EventRecorder
from sanguosha.engine.registry import ActionHandlerRegistry
from sanguosha.model.card import CardDefinition, CardInstance
from sanguosha.model.enums import CardCategory, EquipmentSlot, Identity, Phase, PlayerStatus, Suit
from sanguosha.model.ids import CardDefinitionId, CardInstanceId, CharacterId, PlayerId
from sanguosha.model.player import PlayerState
from sanguosha.model.state import GameState
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType


def make_state(*, offensive=False, defensive=False, weapon_range=None):
    ids = tuple(PlayerId(f"p{i}") for i in range(1, 6))
    players = {pid: PlayerState(pid, i, CharacterId("test"), Identity.REBEL, 4, 4)
               for i, pid in enumerate(ids)}
    cards = {}
    zones = {}
    definitions = CardDefinitionRegistry()

    def equip(owner, slot, key, attack_range=None):
        card_id = CardInstanceId(key)
        definition_id = CardDefinitionId(f"equipment.{key}")
        cards[card_id] = CardInstance(card_id, definition_id, Suit.SPADE, 1)
        definitions.register(CardDefinition(definition_id, key, CardCategory.EQUIPMENT,
                                            equipment_slot=slot, attack_range=attack_range))
        ref = ZoneRef(ZoneType.EQUIPMENT, owner, slot)
        zones[ref] = CardZone(ref, [card_id])

    if offensive:
        equip(ids[0], EquipmentSlot.OFFENSIVE_HORSE, "offensive")
    if defensive:
        equip(ids[2], EquipmentSlot.DEFENSIVE_HORSE, "defensive")
    if weapon_range:
        equip(ids[0], EquipmentSlot.WEAPON, "weapon", weapon_range)
    return GameState("t6-test", players, ids, cards, zones), DistanceSystem(definitions)


def test_living_seat_ring_and_death():
    state, distance = make_state()
    p1, p2, p3, p4, p5 = state.seat_order
    assert [distance.distance_between(state, p1, target) for target in (p2, p3, p4, p5)] == [1, 2, 2, 1]
    state.players[p2].status = PlayerStatus.DEAD
    assert distance.distance_between(state, p1, p3) == 1
    with pytest.raises(ValueError):
        distance.distance_between(state, p1, p2)


def test_horses_stack_and_distance_never_drops_below_one():
    state, distance = make_state(offensive=True, defensive=True)
    p1, p2, p3, *_ = state.seat_order
    assert distance.distance_between(state, p1, p3) == 2
    assert distance.distance_between(state, p3, p1) == 2
    assert distance.distance_between(state, p1, p2) == 1


def test_weapon_range_and_slash_validation_use_same_distance():
    state, distance = make_state(weapon_range=2)
    p1, _, p3, *_ = state.seat_order
    rule = SlashRule(ReachableOpponent(distance))
    assert distance.attack_range(state, p1) == 2
    assert p3 in rule.target_candidates(state, p1)
    rule.validate_targets(state, p1, (p3,))
    state.zones[ZoneRef(ZoneType.EQUIPMENT, p1, EquipmentSlot.WEAPON)].card_ids.clear()
    with pytest.raises(InvalidCardUse):
        rule.validate_targets(state, p1, (p3,))


def test_crossbow_usage_modifier_tracks_equipment_zone():
    state, _ = make_state()
    p1 = state.seat_order[0]
    modifier = EquipmentSlashLimit()
    assert modifier.limit(state, p1) == 1
    card_id = CardInstanceId('crossbow')
    state.cards[card_id] = CardInstance(card_id, CardDefinitionId('equipment.weapon.crossbow'), Suit.CLUB, 1)
    ref = ZoneRef(ZoneType.EQUIPMENT, p1, EquipmentSlot.WEAPON)
    state.zones[ref] = CardZone(ref, [card_id])
    assert modifier.limit(state, p1) is None
    state.zones[ref].card_ids.clear()
    assert modifier.limit(state, p1) == 1


def test_forced_out_of_range_slash_is_rejected_before_card_moves():
    state, _ = make_state()
    p1, _, p3, *_ = state.seat_order
    card_id = CardInstanceId('slash')
    state.cards[card_id] = CardInstance(card_id, CardDefinitionId('basic.slash'), Suit.SPADE, 7)
    hand = ZoneRef(ZoneType.HAND, p1)
    state.zones[hand] = CardZone(hand, [card_id])
    state.current_player_id = p1
    state.current_phase = Phase.PLAY
    state.turn_number = 1
    state.play_usage = PlayUsageState(p1, 1)
    definitions = CardDefinitionRegistry()
    rules = CardRuleRegistry()
    register_basic_cards(definitions, rules, DistanceSystem(definitions))
    events = EventRecorder()
    handler = UseCardActionHandler(CardUseValidator(definitions, rules, TargetValidator()),
                                   CardMoveService(events), events)
    registry = ActionHandlerRegistry()
    registry.register(UseCardAction, handler)
    engine = GameEngine(state, registry)
    with pytest.raises(InvalidCardUse):
        engine.start_action(UseCardAction('forced', p1, card_id, (p3,)))
    assert state.cards_in(hand) == (card_id,)
    assert not events.events

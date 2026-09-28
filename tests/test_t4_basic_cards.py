import pytest

from sanguosha.content.cards.basic import DODGE_ID, PEACH_ID, SLASH_ID, register_basic_cards
from sanguosha.engine import (
    ActionHandlerRegistry, BeforeDamageEvent, CardDefinitionRegistry, CardMove,
    CardMovedEvent, CardMoveReason, CardMoveService, CardRespondedEvent,
    CardResolvedEvent, CardRuleRegistry, CardUseValidator, CardUsedEvent,
    DamageAction, DamageActionHandler, DamageDealtEvent, Decision,
    DyingRequiredEvent, END_PLAY_PHASE, EngineStatus, EventRecorder, GameEngine,
    HpRecoveredEvent, InvalidCardMove, InvalidCardUse, InvalidDecision,
    LegalPlayActionProvider, PASS_RESPONSE, PeachEffectAction, PeachEffectHandler,
    PhaseAction, PhaseActionHandler, RecoverAction, RecoverActionHandler,
    RespondWithCardAction, RespondWithCardHandler, SlashEffectAction,
    SlashEffectHandler, TargetValidator, TurnAction, TurnActionHandler,
    UseCardAction, UseCardActionHandler, standard_phase_bodies,
)
from sanguosha.model.card import CardInstance
from sanguosha.model.enums import Identity, Phase, PlayerStatus, Suit
from sanguosha.model.ids import CardInstanceId, CharacterId, PlayerId
from sanguosha.model.ids import CardDefinitionId
from sanguosha.model.player import PlayerState
from sanguosha.model.state import GameState
from sanguosha.model.usage import PlayUsageState
from sanguosha.model.zones import CardZone, ZoneRef, ZoneType


P1, P2, P3 = (PlayerId(f"p{i}") for i in range(1, 4))
HAND1, HAND2, HAND3 = (ZoneRef(ZoneType.HAND, pid) for pid in (P1, P2, P3))
PROCESSING = ZoneRef(ZoneType.PROCESSING)
DISCARD = ZoneRef(ZoneType.DISCARD_PILE)


def make_state(cards=(), hp=(4, 4, 4), dead=()):
    players = {
        pid: PlayerState(pid, i, CharacterId("test"), Identity.LORD if i == 0 else Identity.REBEL,
                         hp[i], 4, PlayerStatus.DEAD if pid in dead else PlayerStatus.ALIVE)
        for i, pid in enumerate((P1, P2, P3))
    }
    instances = {}
    zones = {}
    for index, (card_id, definition_id, owner) in enumerate(cards):
        cid = CardInstanceId(card_id)
        instances[cid] = CardInstance(cid, definition_id, Suit.HEART, index % 13 + 1)
        ref = ZoneRef(ZoneType.HAND, owner)
        zones.setdefault(ref, CardZone(ref)).card_ids.append(cid)
    return GameState("t4-test", players=players, seat_order=(P1, P2, P3), cards=instances, zones=zones)


def setup(cards=(), hp=(4, 4, 4), dead=()):
    state = make_state(cards, hp, dead)
    events = EventRecorder()
    definitions = CardDefinitionRegistry()
    rules = CardRuleRegistry()
    register_basic_cards(definitions, rules)
    validator = CardUseValidator(definitions, rules, TargetValidator())
    moves = CardMoveService(events)
    registry = ActionHandlerRegistry()
    registry.register(TurnAction, TurnActionHandler(events))
    registry.register(PhaseAction, PhaseActionHandler(standard_phase_bodies(LegalPlayActionProvider(validator)), events))
    registry.register(UseCardAction, UseCardActionHandler(validator, moves, events))
    registry.register(SlashEffectAction, SlashEffectHandler())
    registry.register(RespondWithCardAction, RespondWithCardHandler(moves, events))
    registry.register(DamageAction, DamageActionHandler(events))
    registry.register(PeachEffectAction, PeachEffectHandler())
    registry.register(RecoverAction, RecoverActionHandler(events))
    return GameEngine(state, registry), events, validator, moves


def answer(engine, value):
    request = engine.pending_request
    assert request is not None
    return engine.submit_decision(Decision(request.request_id, request.player_id, value))


def start_play(engine, player=P1, action_id="turn-1"):
    assert engine.start_action(TurnAction(action_id, player)) is EngineStatus.WAITING_FOR_DECISION
    assert engine.state.current_phase is Phase.PLAY


def choose_slash_target(engine, card="slash-1", target=P2):
    assert answer(engine, f"use:{card}") is EngineStatus.WAITING_FOR_DECISION
    assert engine.pending_request.request_type.value == "choose_player"
    assert answer(engine, target) is EngineStatus.WAITING_FOR_DECISION
    assert engine.pending_request.request_type.value == "respond_with_card"


def assert_location(state, card_id, ref):
    cid = CardInstanceId(card_id)
    assert cid in state.cards_in(ref)
    assert sum(cid in zone.card_ids for zone in state.zones.values()) == 1


def test_basic_definition_registry_and_model_separation():
    e, _, validator, _ = setup()
    definitions = validator.definitions
    assert [definitions.get(identifier).name for identifier in (SLASH_ID, DODGE_ID, PEACH_ID)] == ["杀", "闪", "桃"]
    assert definitions.get(SLASH_ID).nature.value == "normal"
    assert all(definitions.get(identifier).category.value == "basic" for identifier in (SLASH_ID, DODGE_ID, PEACH_ID))
    assert not hasattr(CardInstance, "zone") and not hasattr(PlayerState, "hand")


def test_unregistered_card_is_not_offered_and_forced_use_rejected():
    unknown = CardDefinitionId("future.card")
    e, _, _, _ = setup((("future-1", unknown, P1),))
    start_play(e)
    assert e.pending_request.choices == (END_PLAY_PHASE,)
    forced = GameEngine(e.state, e.registry)
    with pytest.raises(InvalidCardUse, match="unregistered"):
        forced.start_action(UseCardAction("forced-future", P1, CardInstanceId("future-1")))
    assert_location(e.state, "future-1", HAND1)


def test_card_move_atomic_validation_and_order():
    e, events, _, moves = setup((("a", SLASH_ID, P1), ("b", DODGE_ID, P1)))
    bad = CardMove("bad", (CardInstanceId("a"), CardInstanceId("b")), HAND2, PROCESSING, CardMoveReason.USE)
    before = {ref: tuple(zone.card_ids) for ref, zone in e.state.zones.items()}
    with pytest.raises(InvalidCardMove):
        moves.move(e.state, bad)
    assert {ref: tuple(zone.card_ids) for ref, zone in e.state.zones.items()} == before
    assert events.events == []
    moves.move(e.state, CardMove("to-processing", (CardInstanceId("a"),), HAND1, PROCESSING, CardMoveReason.USE, P1))
    assert_location(e.state, "a", PROCESSING)
    moves.move(e.state, CardMove("to-discard", (CardInstanceId("a"),), PROCESSING, DISCARD, CardMoveReason.USE, P1))
    assert_location(e.state, "a", DISCARD)
    assert [event.event_id for event in events.events] == ["to-processing", "to-discard"]
    assert all(isinstance(event, CardMovedEvent) for event in events.events)
    moves.move(e.state, CardMove("direct-discard", (CardInstanceId("b"),), HAND1, DISCARD, CardMoveReason.DISCARD, P1))
    assert_location(e.state, "b", DISCARD)


def test_batch_move_is_atomic_when_one_card_is_invalid():
    e, events, _, moves = setup((("a", SLASH_ID, P1), ("b", DODGE_ID, P2)))
    with pytest.raises(InvalidCardMove):
        moves.move(e.state, CardMove("batch", (CardInstanceId("a"), CardInstanceId("b")), HAND1, PROCESSING, CardMoveReason.SYSTEM))
    assert_location(e.state, "a", HAND1)
    assert_location(e.state, "b", HAND2)
    assert events.events == []


def test_slash_dodged_with_specific_instance_and_return_to_play():
    e, events, _, _ = setup((("slash-1", SLASH_ID, P1), ("dodge-1", DODGE_ID, P2), ("dodge-2", DODGE_ID, P2)))
    start_play(e)
    assert e.pending_request.choices == ("use:slash-1", END_PLAY_PHASE)
    choose_slash_target(e)
    assert e.stack.depth == 5
    request = e.pending_request
    assert request.required_definition_id == DODGE_ID
    assert request.eligible_card_ids == (CardInstanceId("dodge-1"), CardInstanceId("dodge-2"))
    assert answer(e, CardInstanceId("dodge-2")) is EngineStatus.WAITING_FOR_DECISION
    assert e.stack.depth == 2 and e.state.players[P2].hp == 4
    assert_location(e.state, "slash-1", DISCARD)
    assert_location(e.state, "dodge-2", DISCARD)
    assert_location(e.state, "dodge-1", HAND2)
    assert e.state.play_usage.count(SLASH_ID) == 1
    assert e.state.cards_in(PROCESSING) == ()
    assert e.pending_request.choices == (END_PLAY_PHASE,)
    assert sum(isinstance(event, CardRespondedEvent) for event in events.events) == 1
    assert answer(e, END_PLAY_PHASE) is EngineStatus.COMPLETED


def test_slash_pass_deals_normal_damage_and_cleans_processing():
    e, events, _, _ = setup((("slash-1", SLASH_ID, P1),))
    start_play(e)
    choose_slash_target(e)
    assert e.pending_request.eligible_card_ids == ()
    assert answer(e, PASS_RESPONSE) is EngineStatus.WAITING_FOR_DECISION
    assert e.state.players[P2].hp == 3
    assert_location(e.state, "slash-1", DISCARD)
    assert e.state.cards_in(PROCESSING) == ()
    kinds = [type(event) for event in events.events]
    assert kinds.index(BeforeDamageEvent) < kinds.index(DamageDealtEvent)
    assert kinds.index(CardUsedEvent) < kinds.index(DamageDealtEvent) < kinds.index(CardResolvedEvent)


def test_player_with_dodge_may_pass_without_moving_it():
    e, _, _, _ = setup((("slash-1", SLASH_ID, P1), ("dodge-1", DODGE_ID, P2)))
    start_play(e)
    choose_slash_target(e)
    answer(e, PASS_RESPONSE)
    assert e.state.players[P2].hp == 3
    assert_location(e.state, "dodge-1", HAND2)


def test_second_slash_not_offered_and_forced_use_rejected():
    e, _, _, _ = setup((("slash-1", SLASH_ID, P1), ("slash-2", SLASH_ID, P1)))
    start_play(e)
    choose_slash_target(e)
    answer(e, PASS_RESPONSE)
    assert e.pending_request.choices == (END_PLAY_PHASE,)
    forced = GameEngine(e.state, e.registry)
    with pytest.raises(InvalidCardUse, match="limit"):
        forced.start_action(UseCardAction("forced-second", P1, CardInstanceId("slash-2"), (P2,)))
    assert_location(e.state, "slash-2", HAND1)
    assert e.state.play_usage.count(SLASH_ID) == 1
    answer(e, END_PLAY_PHASE)


def test_new_play_phase_resets_slash_count():
    e, _, _, _ = setup((("slash-1", SLASH_ID, P1), ("slash-2", SLASH_ID, P1)))
    start_play(e)
    choose_slash_target(e)
    answer(e, PASS_RESPONSE)
    answer(e, END_PLAY_PHASE)
    start_play(e, action_id="turn-2")
    assert e.state.play_usage.count(SLASH_ID) == 0
    assert e.pending_request.choices == ("use:slash-2", END_PLAY_PHASE)
    choose_slash_target(e, "slash-2")
    answer(e, PASS_RESPONSE)
    assert e.state.play_usage.count(SLASH_ID) == 1


def test_dodge_is_response_only():
    e, _, _, _ = setup((("dodge-1", DODGE_ID, P1),))
    start_play(e)
    assert e.pending_request.choices == (END_PLAY_PHASE,)
    forced = GameEngine(e.state, e.registry)
    with pytest.raises(InvalidCardUse):
        forced.start_action(UseCardAction("forced-dodge", P1, CardInstanceId("dodge-1")))
    assert_location(e.state, "dodge-1", HAND1)


def test_peach_recovers_one_and_moves_to_discard():
    e, events, _, _ = setup((("peach-1", PEACH_ID, P1),), hp=(2, 4, 4))
    start_play(e)
    assert e.pending_request.choices == ("use:peach-1", END_PLAY_PHASE)
    assert answer(e, "use:peach-1") is EngineStatus.WAITING_FOR_DECISION
    assert e.state.players[P1].hp == 3
    assert_location(e.state, "peach-1", DISCARD)
    assert e.state.cards_in(PROCESSING) == ()
    assert any(isinstance(event, HpRecoveredEvent) and event.amount == 1 for event in events.events)


def test_full_hp_peach_not_offered_or_usable():
    e, _, _, _ = setup((("peach-1", PEACH_ID, P1),))
    start_play(e)
    assert e.pending_request.choices == (END_PLAY_PHASE,)
    forced = GameEngine(e.state, e.registry)
    with pytest.raises(InvalidCardUse):
        forced.start_action(UseCardAction("forced-peach", P1, CardInstanceId("peach-1")))
    assert_location(e.state, "peach-1", HAND1)


def test_recover_action_clamps_to_max_hp():
    e, events, _, _ = setup(hp=(3, 4, 4))
    assert e.start_action(RecoverAction("recover", P2, P1, 2)) is EngineStatus.COMPLETED
    assert e.state.players[P1].hp == 4 and e.last_result == 1
    assert any(isinstance(event, HpRecoveredEvent) and event.amount == 1 for event in events.events)


@pytest.mark.parametrize("invalid_target", [P1, P3, PlayerId("missing")])
def test_invalid_slash_target_decision_preserves_hand_and_usage(invalid_target):
    e, _, _, _ = setup((("slash-1", SLASH_ID, P1),), dead=(P3,))
    start_play(e)
    assert answer(e, "use:slash-1") is EngineStatus.WAITING_FOR_DECISION
    request = e.pending_request
    assert request.allowed_player_ids == (P2,)
    stack = e.stack.snapshot()
    with pytest.raises(InvalidDecision):
        answer(e, invalid_target)
    assert e.pending_request == request and e.stack.snapshot() == stack
    assert_location(e.state, "slash-1", HAND1)
    assert e.state.play_usage.count(SLASH_ID) == 0
    answer(e, P2)
    answer(e, PASS_RESPONSE)
    assert_location(e.state, "slash-1", DISCARD)


def test_forced_invalid_target_preflight_has_no_effect():
    e, _, _, _ = setup((("slash-1", SLASH_ID, P1),), dead=(P3,))
    start_play(e)
    for index, target in enumerate((P1, P3, PlayerId("missing"))):
        forced = GameEngine(e.state, e.registry)
        with pytest.raises(InvalidCardUse):
            forced.start_action(UseCardAction(f"forced-{index}", P1, CardInstanceId("slash-1"), (target,)))
        assert_location(e.state, "slash-1", HAND1)
        assert e.state.play_usage.count(SLASH_ID) == 0


@pytest.mark.parametrize("invalid_card", [CardInstanceId("peach-2"), CardInstanceId("dodge-3")])
def test_invalid_response_card_keeps_pending_request(invalid_card):
    e, _, _, _ = setup((
        ("slash-1", SLASH_ID, P1), ("dodge-2", DODGE_ID, P2),
        ("peach-2", PEACH_ID, P2), ("dodge-3", DODGE_ID, P3),
    ))
    start_play(e)
    choose_slash_target(e)
    request = e.pending_request
    stack = e.stack.snapshot()
    with pytest.raises(InvalidDecision):
        answer(e, invalid_card)
    assert e.pending_request == request and e.stack.snapshot() == stack
    assert_location(e.state, str(invalid_card), HAND2 if invalid_card == "peach-2" else HAND3)
    answer(e, CardInstanceId("dodge-2"))
    assert e.state.players[P2].hp == 4


def test_multilevel_stack_and_dying_marker_without_death():
    e, events, _, _ = setup((("slash-1", SLASH_ID, P1),), hp=(4, 1, 4))
    start_play(e)
    assert e.stack.depth == 2
    answer(e, "use:slash-1")
    assert e.stack.depth == 3
    answer(e, P2)
    assert e.stack.depth == 5
    answer(e, PASS_RESPONSE)
    assert e.stack.depth == 2 and e.state.players[P2].hp == 0
    assert e.state.players[P2].status is PlayerStatus.ALIVE
    assert any(isinstance(event, DyingRequiredEvent) and event.hp == 0 for event in events.events)
    assert e.state.cards_in(PROCESSING) == ()
    answer(e, END_PLAY_PHASE)
    assert e.status is EngineStatus.COMPLETED and e.stack.depth == 0


def test_damage_can_leave_negative_hp_without_marking_dead():
    e, events, _, _ = setup(hp=(4, 1, 4))
    assert e.start_action(DamageAction("heavy", P1, P2, 2)) is EngineStatus.COMPLETED
    assert e.state.players[P2].hp == -1
    assert e.state.players[P2].status is PlayerStatus.ALIVE
    assert any(isinstance(event, DyingRequiredEvent) and event.hp == -1 for event in events.events)


def test_deterministic_card_flow():
    def run():
        e, events, _, _ = setup((("slash-1", SLASH_ID, P1), ("dodge-1", DODGE_ID, P2)))
        start_play(e)
        choose_slash_target(e)
        answer(e, CardInstanceId("dodge-1"))
        answer(e, END_PLAY_PHASE)
        return tuple(repr(event) for event in events.events), tuple((str(ref), tuple(zone.card_ids)) for ref, zone in e.state.zones.items()), e.state.players[P2].hp
    assert run() == run()

import pytest

from sanguosha.content.cards.ids import DODGE_ID, PEACH_ID, SLASH_ID
from sanguosha.engine.card_moves import CardMove, CardMoveReason, CardMoveService
from sanguosha.engine.death import DeathAction
from sanguosha.engine.dying import DyingAction
from sanguosha.engine.events import (
    CardMovedEvent, DyingRescuedEvent, GameEndedEvent, KillRewardEvent,
    LordPenaltyEvent, PlayerDiedEvent,
)
from sanguosha.engine.phases import END_PLAY_PHASE
from sanguosha.engine.requests import PASS_RESPONSE, Decision, PendingRequest, RequestType
from sanguosha.engine.errors import InvalidDecision
from sanguosha.model.enums import Identity, Phase, PlayerStatus
from sanguosha.model.enums import EquipmentSlot
from sanguosha.model.ids import CardInstanceId, PlayerId
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.projection import project_for_human
from sanguosha.session import GameSession


P1, P2, P3, P4, P5 = (PlayerId(f"p{i}") for i in range(1, 6))
DRAW = ZoneRef(ZoneType.DRAW_PILE)
DISCARD = ZoneRef(ZoneType.DISCARD_PILE)


def hand(pid):
    return ZoneRef(ZoneType.HAND, pid)


def zone_of(session, card_id):
    return next(ref for ref, zone in session.state.zones.items() if card_id in zone.card_ids)


def relocate(session, card_id, destination, label):
    source = zone_of(session, card_id)
    if source != destination:
        CardMoveService(session.events).move(session.state, CardMove(
            label, (card_id,), source, destination, CardMoveReason.SYSTEM,
        ))


def find_card(session, definition_id):
    return next(cid for cid, card in session.state.cards.items() if card.definition_id == definition_id)


def answer(session, value):
    request = session.engine.pending_request
    assert request is not None
    return session.engine.submit_decision(Decision(request.request_id, request.player_id, value))


def test_finite_seeded_deck_and_initial_deal():
    first = GameSession.new_game(9)
    second = GameSession.new_game(9)
    assert len(first.state.cards) == 80
    assert tuple(first.state.cards_in(DRAW)) == tuple(second.state.cards_in(DRAW))
    assert all(len(first.state.cards_in(hand(pid))) == 4 for pid in first.state.seat_order)
    assert len(first.state.cards_in(DRAW)) == 60
    assert sum(len(zone.card_ids) for zone in first.state.zones.values()) == 80
    assert len({card_id for zone in first.state.zones.values() for card_id in zone.card_ids}) == 80


def test_draw_phase_moves_two_cards_via_service():
    session = GameSession.new_game()
    before = len(session.state.cards_in(hand(P1)))
    session.pump_until_human_or_end()
    assert session.state.current_phase is Phase.PLAY
    assert len(session.state.cards_in(hand(P1))) == before + 2
    draws = [event for event in session.events.events if isinstance(event, CardMovedEvent)
             and event.from_zone == DRAW and event.to_zone == hand(P1)]
    assert [len(event.card_ids) for event in draws] == [4, 2]


def test_deck_exhaustion_recycles_discard_deterministically():
    session = GameSession.new_game(3)
    all_draw = session.state.cards_in(DRAW)
    relocate_service = CardMoveService(session.events)
    relocate_service.move(session.state, CardMove("empty-deck", all_draw, DRAW, DISCARD, CardMoveReason.SYSTEM))
    assert not session.state.cards_in(DRAW)
    session.engine.start_action(__import__("sanguosha.engine.deck", fromlist=["DrawCardsAction"]).DrawCardsAction("recycle", P1, 2))
    assert len(session.state.cards_in(hand(P1))) == 6
    assert any(event.event_id.startswith("recycle:reshuffle") for event in session.events.events if isinstance(event, CardMovedEvent))


def test_discard_phase_requests_exact_excess_and_moves_selection():
    session = GameSession.new_game(6)
    session.state.players[P1].hp = 2
    session.pump_until_human_or_end()
    answer(session, END_PLAY_PHASE)
    request = session.engine.pending_request
    assert request.request_type is RequestType.CHOOSE_CARDS
    assert request.min_count == request.max_count == 4
    before = session.state.cards_in(hand(P1))
    with pytest.raises(InvalidDecision):
        answer(session, (before[0],))
    with pytest.raises(InvalidDecision):
        answer(session, (before[0],) * 4)
    with pytest.raises(InvalidDecision):
        answer(session, (before[0], before[1], before[2], CardInstanceId("foreign")))
    assert session.engine.pending_request == request
    answer(session, before[:4])
    assert len(session.state.cards_in(hand(P1))) == 2
    assert all(card_id in session.state.cards_in(DISCARD) for card_id in before[:4])


def test_dying_peach_response_rescues_and_consumes_real_card():
    session = GameSession.new_game(6)
    peach = find_card(session, PEACH_ID)
    relocate(session, peach, hand(P2), "give-peach")
    session.state.players[P2].hp = 0
    session.engine.start_action(DyingAction("dying-p2", P2, P3))
    request = session.engine.pending_request
    assert request.player_id == P2 and peach in request.eligible_card_ids
    answer(session, peach)
    assert session.state.players[P2].hp == 1
    assert session.state.players[P2].is_alive
    assert peach in session.state.cards_in(DISCARD)
    assert any(isinstance(event, DyingRescuedEvent) for event in session.events.events)


def test_negative_hp_can_be_rescued_by_multiple_peaches():
    session = GameSession.new_game(6)
    peaches = [cid for cid, card in session.state.cards.items() if card.definition_id == PEACH_ID][:2]
    for index, peach in enumerate(peaches):
        relocate(session, peach, hand(P2), f"give-peach-{index}")
    session.state.players[P2].hp = -1
    session.engine.start_action(DyingAction("deep-dying", P2, P3))
    answer(session, peaches[0])
    assert session.state.players[P2].hp == 0
    assert session.engine.pending_request is not None
    answer(session, peaches[1])
    assert session.state.players[P2].hp == 1
    assert session.engine.pending_request is None


def test_dying_all_passes_leads_to_death_and_reveal():
    session = GameSession.new_game(6)
    session.state.players[P3].hp = 0
    session.engine.start_action(DyingAction("dying-p3", P3, P1))
    while session.engine.pending_request is not None:
        answer(session, PASS_RESPONSE)
    assert session.state.players[P3].status is PlayerStatus.DEAD
    assert P3 in session.state.revealed_identities
    assert session.state.cards_in(hand(P3)) == ()
    assert any(isinstance(event, PlayerDiedEvent) for event in session.events.events)


def test_rebel_kill_reward_draws_three():
    session = GameSession.new_game(6)
    before = len(session.state.cards_in(hand(P1)))
    session.engine.start_action(DeathAction("death-rebel", P3, P1))
    assert session.state.players[P3].status is PlayerStatus.DEAD
    assert len(session.state.cards_in(hand(P1))) == before + 3
    assert any(isinstance(event, KillRewardEvent) and event.cards_drawn == 3 for event in session.events.events)


def test_lord_kills_loyalist_penalty_discards_all_lord_cards():
    session = GameSession.new_game(6)
    assert session.state.cards_in(hand(P1))
    session.engine.start_action(DeathAction("death-loyalist", P2, P1))
    assert session.state.cards_in(hand(P1)) == ()
    assert any(isinstance(event, LordPenaltyEvent) for event in session.events.events)


def test_death_cleanup_includes_equipment_and_judgment_zones():
    session = GameSession.new_game(6)
    cards = session.state.cards_in(hand(P3))
    weapon = ZoneRef(ZoneType.EQUIPMENT, P3, EquipmentSlot.WEAPON)
    judgment = ZoneRef(ZoneType.JUDGMENT, P3)
    relocate(session, cards[0], weapon, "setup-weapon")
    relocate(session, cards[1], judgment, "setup-judgment")
    session.engine.start_action(DeathAction("death-with-zones", P3, P1))
    assert session.state.cards_in(weapon) == ()
    assert session.state.cards_in(judgment) == ()
    assert all(card_id in session.state.cards_in(DISCARD) for card_id in cards)


def test_identity_victory_lord_team_rebels_and_renegade():
    session = GameSession.new_game(6)
    session.state.players[P3].status = PlayerStatus.DEAD
    session.state.players[P4].status = PlayerStatus.DEAD
    session.engine.start_action(DeathAction("death-renegade", P5, P1))
    assert session.state.status is GameStatus.FINISHED
    assert session.state.victory.label == "主公与忠臣胜利"
    assert any(isinstance(event, GameEndedEvent) for event in session.events.events)


@pytest.mark.parametrize("survivors,expected", [((P3, P5), "反贼胜利"), ((P5,), "内奸胜利")])
def test_identity_victory_when_lord_dies(survivors, expected):
    session = GameSession.new_game(6)
    for pid in (P2, P3, P4, P5):
        if pid not in survivors:
            session.state.players[pid].status = PlayerStatus.DEAD
    session.engine.start_action(DeathAction("death-lord", P1, P3 if P3 in survivors else P5))
    assert session.state.status is GameStatus.FINISHED
    assert session.state.victory.label == expected


def test_next_turn_loop_skips_dead_player():
    session = GameSession.new_game(6)
    session.state.players[P2].status = PlayerStatus.DEAD
    for _ in range(100):
        if session.state.turn_number >= 2:
            break
        request = session.engine.pending_request
        if request is not None and request.player_id == P1:
            session.submit_human(session.ai.decide(session.state, request))
        else:
            session.step_auto()
    assert session.state.turn_number == 2
    assert session.state.current_player_id == P3


def test_ai_response_play_discard_and_dying_decisions_are_legal():
    session = GameSession.new_game(6)
    dodge = find_card(session, DODGE_ID)
    peach = find_card(session, PEACH_ID)
    relocate(session, dodge, hand(P2), "ai-dodge")
    relocate(session, peach, hand(P2), "ai-peach")
    ai = session.ai
    response = PendingRequest("response", P2, RequestType.RESPOND_WITH_CARD, "闪", "a", "f",
                              required_definition_id=DODGE_ID, eligible_card_ids=(dodge,), allow_pass=True)
    assert ai.decide(session.state, response).value == dodge
    rescue = PendingRequest("rescue", P2, RequestType.RESPOND_WITH_CARD, "桃", "a", "f",
                            required_definition_id=PEACH_ID, eligible_card_ids=(peach,), allow_pass=True,
                            subject_player_id=P2)
    assert ai.decide(session.state, rescue).value == peach
    discard = PendingRequest("discard", P2, RequestType.CHOOSE_CARDS, "弃牌", "a", "f",
                             eligible_card_ids=session.state.cards_in(hand(P2)), min_count=2, max_count=2)
    decision = ai.decide(session.state, discard)
    discard.validate(decision.value)
    assert peach not in decision.value
    choices = (f"use:{peach}", END_PLAY_PHASE)
    session.state.players[P2].hp = 3
    play = PendingRequest("play", P2, RequestType.CHOOSE_OPTION, "出牌", "a", "f", choices=choices)
    assert ai.decide(session.state, play).value == f"use:{peach}"


def test_projection_hides_opponent_cards_and_identities():
    session = GameSession.new_game(6)
    view = project_for_human(session.state, session.definitions, P1, session.character_names)
    assert len(view.hand) == 4
    assert all(player.hand_count == 4 for player in view.players)
    assert view.players[0].identity_label == "主公"
    assert all(player.identity_label == "未知" for player in view.players[1:])
    assert not hasattr(view.players[1], "hand")
    session.state.players[P3].status = PlayerStatus.DEAD
    session.state.revealed_identities.add(P3)
    view = project_for_human(session.state, session.definitions, P1, session.character_names)
    assert view.players[2].identity_label == "反贼"


def test_full_five_player_match_completes_headlessly_with_shared_decisions():
    session = GameSession.new_game(6)
    for _ in range(2000):
        if session.state.status is GameStatus.FINISHED:
            break
        request = session.engine.pending_request
        if request is not None and request.player_id == session.human_id:
            session.submit_human(session.ai.decide(session.state, request))
        else:
            session.step_auto()
    assert session.state.status is GameStatus.FINISHED
    assert session.state.victory is not None
    assert session.state.turn_number > 5
    assert not session.state.cards_in(ZoneRef(ZoneType.PROCESSING))

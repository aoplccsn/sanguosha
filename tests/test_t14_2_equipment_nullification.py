"""Equipment use must never open a trick nullification window."""

import pytest

from sanguosha.engine.card_use import UseCardAction
from sanguosha.engine.requests import Decision, PASS_RESPONSE
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.session import GameSession

from test_t6_military_basics import game, put


@pytest.mark.parametrize("definition", [
    "equipment.horse.dilu",
    "equipment.horse.chitu",
    "equipment.horse.jueying",
    "equipment.horse.dayuan",
    "equipment.horse.zixing",
    "equipment.horse.zhaohuangfeidian",
    "equipment.horse.hualiu",
    "equipment.weapon.crossbow",
    "equipment.armor.eight_trigrams",
])
def test_equipment_use_has_no_nullification_request(definition):
    session = game()
    card_id = put(session, definition)
    session.engine.start_action(UseCardAction("equip-check", "p1", card_id))
    assert session.engine.pending_request is None
    assert not session.engine.stack.snapshot()
    assert card_id not in session.state.cards_in(ZoneRef(ZoneType.PROCESSING))


def test_trick_still_opens_nullification_with_legal_response():
    session = game()
    card_id = put(session, "trick.duel")
    put(session, "trick.nullification", "p2")
    session.engine.start_action(UseCardAction("trick-check", "p1", card_id, ("p2",)))
    request = session.engine.pending_request
    assert request is not None
    assert request.required_definition_id == "trick.nullification"
    assert not request.has_legal_response()
    session.engine.submit_decision(Decision(request.request_id, request.player_id, PASS_RESPONSE))
    request = session.engine.pending_request
    assert request is not None
    assert request.player_id == "p2"
    assert request.has_legal_response()


@pytest.mark.parametrize('definition,targets', [
    ('basic.slash', ('p2',)), ('basic.peach', ()), ('basic.wine', ()),
])
def test_basic_use_never_opens_nullification(definition, targets):
    session = game()
    session.state.players['p1'].hp = 3
    card_id = put(session, definition)
    put(session, 'trick.nullification', 'p1')
    session.engine.start_action(UseCardAction('basic-check', 'p1', card_id, targets))
    request = session.engine.pending_request
    assert request is None or request.required_definition_id != 'trick.nullification'


@pytest.mark.parametrize('black,disabled,expected', [
    (True, False, True), (False, False, False), (True, True, False),
])
def test_room_nullification_legality_retains_only_effective_kanpo(black, disabled, expected):
    from dataclasses import replace
    from sanguosha.engine.military_tricks import NullificationWindow
    from sanguosha.model.enums import Suit
    from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
    room = MultiplayerRoom()
    pid, _ = room.join('human', lambda _: None)
    session = GameSession.new_game(military=True, five_generals=True)
    room.session, room.phase = session, RoomPhase.IN_GAME
    session.state.players[pid].character_id = 'fire_wolong'
    # A single material isolates physical, color and skill-suppression eligibility.
    hand = ZoneRef(ZoneType.HAND, pid)
    session.state.zones[hand].card_ids.clear()
    cid = put(session, 'basic.dodge', pid)
    session.state.cards[cid] = replace(session.state.cards[cid], suit=Suit.SPADE if black else Suit.HEART)
    if disabled:
        session.state.players[pid].disabled_skills.add('kanpo')
    session.engine.start_action(NullificationWindow('kanpo-legality', 'p2'))
    request = session.engine.pending_request
    assert request.player_id == pid
    assert any(str(value).startswith('virtual:kanpo:') for value in request.eligible_card_ids) is expected
    room.suspend_on_budget = True
    room.pump(max_steps=1)
    assert (session.engine.pending_request is request) is expected

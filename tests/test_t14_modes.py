"""Five- and eight-seat identity mode contracts."""

import pytest
from collections import Counter

from sanguosha.game_modes import MILITARY_EIGHT, MILITARY_FIVE
from sanguosha.model.enums import Identity
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
from sanguosha.room_snapshot import restore_room, snapshot_room
from sanguosha.engine.requests import Decision
from sanguosha.engine.requests import PendingRequest, RequestType
from sanguosha.projection import project_for_human
from sanguosha.model.zones import ZoneRef, ZoneType


def test_mode_definitions_have_classic_role_distributions():
    assert Counter(MILITARY_FIVE.roles) == {
        Identity.LORD: 1, Identity.LOYALIST: 1,
        Identity.REBEL: 2, Identity.RENEGADE: 1}
    assert Counter(MILITARY_EIGHT.roles) == {
        Identity.LORD: 1, Identity.LOYALIST: 2,
        Identity.REBEL: 4, Identity.RENEGADE: 1}


def test_eight_player_session_and_snapshot_restore():
    session = GameSession.new_game(military=True, five_generals=True,
                                   mode_id='military-eight')
    assert len(session.state.players) == 8
    assert session.state.metadata['mode_id'] == 'military-eight'
    restored = restore_session(snapshot_session(session))
    assert len(restored.state.players) == 8
    assert restored.state.seat_order == session.state.seat_order


def test_eight_player_pregame_distributes_roles_without_duplicates():
    setup = Pregame.create(11, 'military-eight')
    assert set(setup.identities) == set(MILITARY_EIGHT.seats)
    assert Counter(setup.identities.values()) == Counter(MILITARY_EIGHT.roles)


def test_eight_player_room_autofills_ai_and_restores():
    room = MultiplayerRoom(seed=8, mode_id='military-eight', allow_gods=True)
    sent = []
    host, _ = room.join('host', sent.append)
    guest, _ = room.join('guest', sent.append)
    room.ready(guest, True)
    room.start(host)
    assert room.phase is RoomPhase.DRAFT
    assert len(room.seats) == 8
    assert sum(seat.controller.value == 'AI' for seat in room.seats.values()) == 6
    restored = restore_room(snapshot_room(room))
    assert restored.mode.mode_id == 'military-eight'
    assert restored.allow_gods
    assert len(restored.seats) == 8


def test_switching_to_five_preserves_human_seats():
    room = MultiplayerRoom(mode_id='military-eight')
    host, _ = room.join('host', lambda _: None)
    room.join('guest', lambda _: None)
    room.configure(host, mode_id='military-five')
    assert len(room.seats) == 5
    assert room.seats['p2'].name == 'guest'


def test_eight_player_mixed_room_starts_shared_game_with_private_identities():
    room = MultiplayerRoom(seed=17, mode_id='military-eight', allow_gods=True)
    host, _ = room.join('host', lambda _: None)
    guest, _ = room.join('guest', lambda _: None)
    room.ready(guest, True)
    room.start(host)
    for pid in (host, guest):
        request = room.draft_requests[pid]
        room.submit(pid, Decision(request.request_id, pid, request.choices[0]))
    assert room.phase in (RoomPhase.IN_GAME, RoomPhase.FINISHED)
    assert len(room.session.state.players) == 8
    view = project_for_human(room.session.state, room.session.definitions,
                             host, room.session.character_names)
    for player in view.players:
        if player.player_id not in (host, room.pregame.lord_id):
            assert player.identity_label == '未知'


def test_lobby_disconnect_keeps_token_and_kick_releases_seat():
    room = MultiplayerRoom(mode_id='military-eight')
    host, _ = room.join('host', lambda _: None)
    guest, token = room.join('guest', lambda _: None)
    room.disconnect(guest)
    assert room.seats[guest].controller.value == 'HUMAN'
    assert not room.seats[guest].connected
    rejoined, same_token = room.join('guest', lambda _: None, token=token)
    assert rejoined == guest and same_token == token
    room.kick(host, guest)
    assert room.seats[guest].controller.value == 'EMPTY'


def test_mode_switch_refuses_to_drop_an_occupied_human_seat():
    from sanguosha.multiplayer.room import RoomError
    import pytest
    room = MultiplayerRoom(mode_id='military-eight')
    host, _ = room.join('host', lambda _: None)
    for index in range(5):
        room.join(f'guest-{index}', lambda _: None)
    with pytest.raises(RoomError, match='occupied'):
        room.configure(host, mode_id='military-five')
    assert room.mode.mode_id == 'military-eight'


def test_hidden_opponent_hand_uses_opaque_choice_and_restores_after_snapshot():
    room = MultiplayerRoom(mode_id='military-eight')
    room.session = GameSession.new_game(military=True, five_generals=True,
                                        mode_id='military-eight')
    hand = room.session.state.cards_in(ZoneRef(ZoneType.HAND, 'p2'))
    request = PendingRequest('private-choice', 'p1', RequestType.CHOOSE_CARD,
                             '选择目标手牌', 'action', 'frame',
                             eligible_card_ids=hand, subject_player_id='p2')
    payload = room._request_payload(request)
    assert payload['eligible_card_ids'] == [f'hidden-hand:{i}' for i in range(1, len(hand) + 1)]
    assert not any(card in str(payload) for card in hand)
    restored = restore_room(snapshot_room(room))
    assert restored._request_payload(request)['eligible_card_ids'] == payload['eligible_card_ids']
    decision = restored._resolve_hidden_choice(request, Decision('private-choice', 'p1', 'hidden-hand:1'))
    assert decision.value == hand[0]

def test_god_toggle_changes_private_draft_pool_and_reconnect_keeps_owner():
    import json

    def started(allow_gods):
        wire = {"p1": [], "p2": []}
        room = MultiplayerRoom(seed=0, allow_gods=allow_gods)
        host, host_token = room.join("host", wire["p1"].append)
        guest, guest_token = room.join("guest", wire["p2"].append)
        room.ready(guest, True)
        room.start(host)
        return room, wire, host, guest, host_token, guest_token

    ordinary, ordinary_wire, host, guest, host_token, guest_token = started(False)
    enabled, enabled_wire, _, _, enabled_host_token, enabled_guest_token = started(True)
    assert not any("_god_" in choice for choice in ordinary.draft_requests[host].choices)
    assert any("_god_" in choice for choice in enabled.draft_requests[host].choices)
    for room, wire, tokens in (
        (ordinary, ordinary_wire, (host_token, guest_token)),
        (enabled, enabled_wire, (enabled_host_token, enabled_guest_token)),
    ):
        host_request = next(message for message in wire["p1"] if message["type"] == "DRAFT_REQUEST")
        guest_request = next(message for message in wire["p2"] if message["type"] == "DRAFT_REQUEST")
        assert host_request["request"]["player_id"] == host
        assert guest_request["request"]["player_id"] == guest
        assert host_request["request"]["request_id"] != guest_request["request"]["request_id"]
        assert all(token not in json.dumps(wire) for token in tokens)
        room.disconnect(guest)
        restored = []
        assert room.join("guest", restored.append, token=tokens[1])[0] == guest
        restored_request = next(message for message in restored if message["type"] == "DRAFT_REQUEST")["request"]
        assert {key: value for key, value in restored_request.items() if key != "remaining_ms"} == {
            key: value for key, value in guest_request["request"].items() if key != "remaining_ms"}
        assert 0 <= restored_request["remaining_ms"] <= guest_request["request"]["remaining_ms"]
        assert all(token not in json.dumps(restored) for token in tokens)

def test_each_viewer_projection_hides_other_hands_and_unrevealed_roles():
    import json

    wire = {"p1": [], "p2": []}
    room = MultiplayerRoom(seed=2, mode_id="military-five")
    host, host_token = room.join("host", wire["p1"].append)
    guest, guest_token = room.join("guest", wire["p2"].append)
    room.ready(guest, True)
    room.start(host)
    for pid in (host, guest):
        request = room.draft_requests[pid]
        room.submit(pid, Decision(request.request_id, pid, request.choices[0]))
    projections = {
        pid: next(message["projection"] for message in wire[pid]
                  if message["type"] == "PROJECTION_UPDATE")
        for pid in (host, guest)
    }

    def all_card_ids(value):
        if isinstance(value, dict):
            result = {value["card_id"]} if "card_id" in value else set()
            for child in value.values():
                result.update(all_card_ids(child))
            return result
        if isinstance(value, (list, tuple)):
            result = set()
            for child in value:
                result.update(all_card_ids(child))
            return result
        return set()

    for viewer, opponent in ((host, guest), (guest, host)):
        view = projections[viewer]
        opponent_view = projections[opponent]
        own_hand = {card["card_id"] for card in view["hand"]}
        assert own_hand
        assert own_hand.isdisjoint(all_card_ids(opponent_view))
        assert host_token not in json.dumps(view) and guest_token not in json.dumps(view)
        for player in view["players"]:
            pid = player["player_id"]
            if pid != viewer and pid != room.pregame.lord_id:
                assert player["identity_label"] == "未知"

@pytest.mark.parametrize("seed", [23, 47])
def test_eight_player_random_roster_ai_match_finishes(seed):
    import random
    from sanguosha.content.characters.standard import PLAYABLE_65_GENERAL_POOL
    from sanguosha.pregame import SetupStage

    setup = Pregame.create(seed, "military-eight")
    ids = tuple(setup.identities)
    selected = random.Random(seed).sample([character.id for character in PLAYABLE_65_GENERAL_POOL], 8)
    setup.generals = dict(zip(ids, selected))
    setup.stage = SetupStage.COMPLETE
    session = GameSession.new_game(military=True, setup=setup)
    session.human_id = "automated"
    session.pump_until_human_or_end(20_000)
    assert session.state.status.value == "finished"
    assert session.state.victory is not None
    assert session.engine.pending_request is None
    assert session.engine.stack.is_empty()
    assert len(session.state.players) == 8

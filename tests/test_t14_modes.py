"""Five- and eight-seat identity mode contracts."""

from collections import Counter

from sanguosha.game_modes import MILITARY_EIGHT, MILITARY_FIVE
from sanguosha.model.enums import Identity
from sanguosha.pregame import Pregame
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
from sanguosha.room_snapshot import restore_room, snapshot_room
from sanguosha.engine.requests import Decision
from sanguosha.projection import project_for_human


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

from sanguosha.engine.requests import Decision
from sanguosha.multiplayer.room import MultiplayerRoom, RoomPhase
from sanguosha.room_snapshot import snapshot_room, restore_room
from sanguosha.snapshot import snapshot_session


def test_lobby_and_draft_restore():
    room = MultiplayerRoom(seed=23)
    host, token1 = room.join("host", lambda _: None)
    guest, token2 = room.join("guest", lambda _: None)
    room.ready(guest, True)
    restored = restore_room(snapshot_room(room))
    assert restored.seats[host].token == token1
    assert restored.seats[guest].ready
    assert restored.seats[host].connected is False
    restored.join("host", lambda _: None, token=token1)
    restored.join("guest", lambda _: None, token=token2)
    restored.start(host)
    assert restored.phase is RoomPhase.DRAFT
    draft = restore_room(snapshot_room(restored))
    assert {pid: request.request_id for pid, request in draft.draft_requests.items()} == {
        pid: request.request_id for pid, request in restored.draft_requests.items()
    }
    assert draft.draft_deadlines == restored.draft_deadlines


def test_gameplay_pending_request_restore():
    room = MultiplayerRoom(seed=17)
    host, token1 = room.join("host", lambda _: None)
    guest, token2 = room.join("guest", lambda _: None)
    room.ready(guest, True)
    room.start(host)
    for pid in (host, guest):
        request = room.draft_requests[pid]
        room.submit(pid, Decision(request.request_id, pid, request.choices[0]))
    assert room.phase is RoomPhase.IN_GAME
    request = room.session.engine.pending_request
    assert request is not None
    restored = restore_room(snapshot_room(room))
    assert restored.session.engine.pending_request == request
    assert restored.request_deadline == room.request_deadline
    assert snapshot_session(restored.session) == snapshot_session(room.session)
    restored.join("host", lambda _: None, token=token1)
    restored.join("guest", lambda _: None, token=token2)

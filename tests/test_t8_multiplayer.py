import asyncio
import json
import time
from unittest.mock import patch

import pytest

from sanguosha.engine.requests import Decision, PASS_RESPONSE
from sanguosha.engine.errors import InvalidDecision
from sanguosha.model.ids import PlayerId
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.multiplayer.protocol import (PROTOCOL_VERSION, ProtocolError, decode,
                                            decision_to_wire, encode, envelope,
                                            serialize_request)
from sanguosha.multiplayer.room import Controller, MultiplayerRoom, RoomError, RoomPhase
from sanguosha.multiplayer.transport import GameClient, GameServer


def choose(payload):
    kind = payload["request_type"]
    if kind == "choose_cards" and payload.get("legal_card_sets"):
        return tuple(payload["legal_card_sets"][0])

    if kind == "choose_option":
        usable = next((c for c in payload["choices"] if c.startswith("use:")), None)
        return usable or ("end_play_phase" if "end_play_phase" in payload["choices"] else payload["choices"][0])
    if kind == "yes_no":
        return False
    if kind == "respond_with_card":
        return PASS_RESPONSE if payload["allow_pass"] else payload["eligible_card_ids"][0]
    if kind in ("choose_card", "choose_player"):
        return (payload["eligible_card_ids"] if kind == "choose_card" else payload["allowed_player_ids"])[0]
    if kind in ("choose_cards", "choose_players"):
        values = payload["eligible_card_ids"] if kind == "choose_cards" else payload["allowed_player_ids"]
        return tuple(values[:payload["min_count"]])
    raise AssertionError(kind)


def test_protocol_rejects_unknown_malformed_and_version():
    original = envelope("PING")
    assert decode(encode(original)) == original
    for raw in (b"not json", b"{}", b'{"type":"OTHER","version":1}',
                b'{"type":"PING","version":99}'):
        with pytest.raises(ProtocolError):
            decode(raw)


@pytest.mark.parametrize("humans", range(1, 6))
def test_lobby_autofill_and_unique_general(humans):
    room = MultiplayerRoom(seed=7)
    ids = [room.join(f"human{i}", lambda _: None)[0] for i in range(humans)]
    with pytest.raises(RoomError):
        room.start(ids[-1] if humans > 1 else PlayerId("p2"))
    for pid in ids[1:]:
        room.ready(pid, True)
    room.start(ids[0])
    assert sum(s.controller is Controller.HUMAN for s in room.seats.values()) == humans
    assert sum(s.controller is Controller.AI for s in room.seats.values()) == 5 - humans
    assert sorted(role.value for role in room.pregame.identities.values()) == sorted(
        ["lord", "loyalist", "rebel", "rebel", "renegade"])
    for pid in ids:
        req = room.draft_requests[pid]
        choice = next(c for c in req.choices if c not in room.pregame.generals.values())
        room.submit(pid, Decision(req.request_id, pid, choice))
    assert room.phase in (RoomPhase.IN_GAME, RoomPhase.FINISHED)
    assert len(set(room.pregame.generals.values())) == 5


def test_sixth_rejected_and_ready_toggle():
    room = MultiplayerRoom()
    ids = [room.join(str(i), lambda _: None)[0] for i in range(5)]
    with pytest.raises(RoomError):
        room.join("six", lambda _: None)
    room.ready(ids[1], True)
    assert room.seats[ids[1]].ready
    room.ready(ids[1], False)
    assert not room.seats[ids[1]].ready
    with pytest.raises(RoomError):
        room.start(ids[0])


def test_private_draft_and_projection_and_rejected_decisions():
    wire = {"p1": [], "p2": []}
    room = MultiplayerRoom(seed=3)
    p1, _ = room.join("A", wire["p1"].append)
    p2, _ = room.join("B", wire["p2"].append)
    room.ready(p2, True)
    room.start(p1)
    a_draft = room.draft_requests[p1]
    assert not any(m["type"] == "DRAFT_REQUEST" and m["request"]["request_id"] == a_draft.request_id
                   for m in wire["p2"])
    with pytest.raises(RoomError):
        room.submit(p2, Decision(a_draft.request_id, p2, a_draft.choices[0]))
    for pid in (p1, p2):
        req = room.draft_requests[pid]
        room.submit(pid, Decision(req.request_id, pid, next(c for c in req.choices if c not in room.pregame.generals.values())))
    session = room.session
    assert session is not None
    b_hand = session.state.cards_in(__import__("sanguosha.model.zones", fromlist=["ZoneRef"]).ZoneRef(
        __import__("sanguosha.model.zones", fromlist=["ZoneType"]).ZoneType.HAND, p2))
    b_card = session.state.cards[b_hand[0]]
    a_projection = next(m["projection"] for m in reversed(wire["p1"]) if m["type"] == "PROJECTION_UPDATE")
    a_json = json.dumps(a_projection)
    assert str(b_hand[0]) not in a_json
    assert str(b_card.definition_id) not in json.dumps(a_projection["hand"]) or str(b_hand[0]) not in a_json
    assert a_projection["players"][1]["identity_label"] == "未知" or room.pregame.identities[p2].value == "lord"
    request = session.engine.pending_request
    if request:
        other = p1 if request.player_id == p2 else p2
        with pytest.raises(RoomError):
            room.submit(other, Decision(request.request_id, other, request.timeout_value()))
        with pytest.raises(RoomError):
            room.submit(request.player_id, Decision("old-request", request.player_id, request.timeout_value()))
        with pytest.raises(InvalidDecision):
            room.submit(request.player_id, Decision(request.request_id, request.player_id, "illegal-card-or-target"))
        assert session.engine.pending_request.request_id == request.request_id


def test_disconnect_reconnect_and_timeout():
    messages = []
    room = MultiplayerRoom(seed=4, timeout_seconds=0)
    p1, token = room.join("host", messages.append)
    room.start(p1)
    room.poll()
    assert room.session is not None
    room.disconnect(p1)
    assert not room.seats[p1].connected
    room.poll()
    restored = []
    assert room.join("host", restored.append, token=token)[0] == p1
    assert any(m["type"] == "PROJECTION_UPDATE" for m in restored)


def test_draft_commit_survives_deadline_and_delayed_ack():
    messages = []
    room = MultiplayerRoom(seed=4)
    pid, _ = room.join("host", messages.append)
    room.start(pid)
    request = room.draft_requests[pid]
    choice = request.choices[0]
    room.draft_deadlines[pid] = time.time() + 0.1
    deadline = room.draft_deadlines[pid]
    room.submit(pid, Decision(request.request_id, pid, choice),
                defer_resolution=True, send_ack=False)
    assert pid not in room.draft_requests
    assert room.pregame.generals[pid] == choice
    with patch("sanguosha.multiplayer.room.time.time", return_value=deadline + 2):
        room.poll()
    assert room.pregame.generals[pid] == choice
    assert not any(m["type"] == "DECISION_RESULT" for m in messages)
    room.resolve_accepted()
    assert room.pregame.generals[pid] == choice


@pytest.mark.parametrize("humans", range(1, 6))
@pytest.mark.parametrize("seed", [4, 1, 2, 3])
def test_20_full_game_smoke(humans, seed):
    room = MultiplayerRoom(seed=seed, timeout_seconds=30)
    ids = [room.join(f"h{i}", lambda _: None)[0] for i in range(humans)]
    for pid in ids[1:]:
        room.ready(pid, True)
    room.start(ids[0])
    for pid in ids:
        req = room.draft_requests[pid]
        room.submit(pid, Decision(req.request_id, pid, next(c for c in req.choices if c not in room.pregame.generals.values())))
    for _ in range(2000):
        if room.phase is RoomPhase.FINISHED:
            break
        request = room.session.engine.pending_request
        assert request is not None
        value = choose(serialize_request(request, 30_000))
        room.submit(request.player_id, Decision(request.request_id, request.player_id, value))
    assert room.phase is RoomPhase.FINISHED
    assert room.session.engine.pending_request is None
    assert room.session.engine.stack.is_empty()
    assert room.session.state.victory is not None


def test_two_real_tcp_clients_and_reconnect():
    async def scenario():
        server = GameServer(host="127.0.0.1", port=0, seed=2, timeout_seconds=2)
        await server.start()
        a = GameClient("127.0.0.1", server.port)
        b = GameClient("127.0.0.1", server.port)
        await a.connect("A")
        await b.connect("B")
        async def seat(client):
            for _ in range(10):
                msg = await asyncio.wait_for(client.receive(), 2)
                if msg["type"] == "WELCOME" and msg.get("seat_id"):
                    return msg
            raise AssertionError("missing seat welcome")
        wa, wb = await seat(a), await seat(b)
        assert wa["seat_id"] != wb["seat_id"]
        await b.send("READY", ready=True)
        await a.send("START_GAME")
        assert server.room.phase in (RoomPhase.OPEN, RoomPhase.READY, RoomPhase.DRAFT)
        await asyncio.sleep(0.05)
        assert server.room.phase is RoomPhase.DRAFT
        await b.close()
        await asyncio.sleep(0.05)
        assert not server.room.seats[PlayerId(wb["seat_id"])].connected
        b2 = GameClient("127.0.0.1", server.port)
        await b2.connect("B", token=wb["reconnect_token"])
        await asyncio.sleep(0.05)
        assert server.room.seats[PlayerId(wb["seat_id"])].connected
        await a.close()
        await b2.close()
        await server.close()
    asyncio.run(scenario())


def test_tcp_illegal_decision_rejected_and_pending_reconnect():
    async def scenario():
        server = GameServer(host="127.0.0.1", port=0, seed=9, timeout_seconds=30)
        await server.start()
        client = GameClient("127.0.0.1", server.port)
        await client.connect("host")
        async def until(connection, kind):
            for _ in range(100):
                msg = await asyncio.wait_for(connection.receive(), 3)
                if msg["type"] == kind:
                    return msg
            raise AssertionError(f"missing {kind}")
        try:
            welcome = await until(client, "WELCOME")
            await client.send("START_GAME")
            draft = await until(client, "DRAFT_REQUEST")
            await client.send("SUBMIT_DECISION", decision={
                "request_id": draft["request"]["request_id"], "value": draft["request"]["choices"][0]})
            pending = await until(client, "PENDING_REQUEST")
            rid = pending["request"]["request_id"]
            await client.send("SUBMIT_DECISION", decision={"request_id": rid, "value": "illegal"})
            error = await until(client, "ERROR")
            assert "illegal" in error["message"]
            assert server.room.session.engine.pending_request.request_id == rid
            await client.close()
            await asyncio.sleep(0.02)
            restored = GameClient("127.0.0.1", server.port)
            await restored.connect("host", token=welcome["reconnect_token"])
            assert (await until(restored, "PENDING_REQUEST"))["request"]["request_id"] == rid
            server.room.request_deadline = 0
            server.room.poll()
            assert server.room.session.engine.pending_request is None or server.room.session.engine.pending_request.request_id != rid
            await restored.close()
        finally:
            await server.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("humans", range(1, 6))
@pytest.mark.parametrize("seed", [4, 1, 2, 3])
def test_tcp_full_game_smoke(humans, seed):
    async def scenario():
        server = GameServer(host="127.0.0.1", port=0, seed=seed, timeout_seconds=30)
        await server.start()
        clients = [GameClient("127.0.0.1", server.port) for _ in range(humans)]
        try:
            for index, client in enumerate(clients):
                await client.connect(f"human{index}")
            async def play(client, index):
                seat_id = None
                seen_requests = set()
                while True:
                    msg = await asyncio.wait_for(client.receive(), 15)
                    kind = msg["type"]
                    if kind == "WELCOME" and msg.get("seat_id"):
                        seat_id = msg["seat_id"]
                        if index:
                            await client.send("READY", ready=True)
                    elif kind == "DRAFT_REQUEST":
                        request = msg["request"]
                        assert request["player_id"] == seat_id
                        await client.send("SUBMIT_DECISION", decision={
                            "request_id": request["request_id"], "value": request["choices"][0]})
                    elif kind == "PENDING_REQUEST":
                        request = msg["request"]
                        assert request["player_id"] == seat_id
                        assert request["request_id"] not in seen_requests
                        seen_requests.add(request["request_id"])
                        await client.send("SUBMIT_DECISION", decision=decision_to_wire(
                            Decision(request["request_id"], PlayerId(seat_id), choose(request))))
                    elif kind == "GAME_OVER":
                        assert seat_id is not None
                        assert seen_requests
                        return
                    elif kind == "ERROR":
                        if msg["message"] != "general already taken; new candidates sent":
                            raise AssertionError(msg["message"])
            tasks = [asyncio.create_task(play(client, i)) for i, client in enumerate(clients)]
            while any(server.room.seats[PlayerId(f"p{i+1}")].ready is False for i in range(1, humans)):
                await asyncio.sleep(0.005)
            await clients[0].send("START_GAME")
            await asyncio.wait_for(asyncio.gather(*tasks), 30)
            assert server.room.phase is RoomPhase.FINISHED
            assert server.room.session.engine.pending_request is None
            assert server.room.session.engine.stack.is_empty()
            assert server.room.session.state.victory is not None
            server.room.session.state.__post_init__()
            assert not server.room.session.state.cards_in(ZoneRef(ZoneType.PROCESSING))
        finally:
            for client in clients:
                await client.close()
            await server.close()
    asyncio.run(scenario())

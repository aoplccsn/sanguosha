from __future__ import annotations

import asyncio
import json
import socket
import pytest
import uvicorn
import websockets

from sanguosha.multiplayer.protocol import PROTOCOL_VERSION
from sanguosha.web.app import create_app
from sanguosha.web.config import WebConfig
from sanguosha.model.zones import ZoneRef, ZoneType


def wire(kind: str, **fields):
    return {"type": kind, "version": PROTOCOL_VERSION, **fields}


def choose(request: dict):
    kind = request["request_type"]
    if kind == "choose_cards" and request.get("legal_card_sets"):
        return request["legal_card_sets"][0]

    if kind == "choose_option":
        usable = next((item for item in request["choices"] if item.startswith("use:")), None)
        return usable or ("end_play_phase" if "end_play_phase" in request["choices"] else request["choices"][0])
    if kind == "yes_no":
        return False
    if kind == "respond_with_card":
        return {"pass": True} if request["allow_pass"] else request["eligible_card_ids"][0]
    if kind == "choose_card":
        return request["eligible_card_ids"][0]
    if kind == "choose_cards":
        return request["eligible_card_ids"][:request["min_count"]]
    if kind == "choose_player":
        return request["allowed_player_ids"][0]
    if kind == "choose_players":
        return request["allowed_player_ids"][:request["min_count"]]
    raise AssertionError(kind)


async def recv_until(ws, kind: str, timeout: float = 15):
    while True:
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout))
        if message["type"] == kind:
            return message


async def start_server():
    port_socket = socket.socket()
    port_socket.bind(("127.0.0.1", 0))
    port = port_socket.getsockname()[1]
    port_socket.close()
    app = create_app(WebConfig(ai_presentation=False))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            return app, server, task, f"ws://127.0.0.1:{port}/ws"
        await asyncio.sleep(0.02)
    raise AssertionError("web server did not start")


async def play_web_match(url: str, humans: int, seed: int, audit_app=None, audit_seen=None,
                         mode_id: str = "military-five"):
    clients = [await websockets.connect(url) for _ in range(humans)]
    seats: list[str] = []
    try:
        for ws in clients:
            await ws.send(json.dumps(wire("HELLO")))
            await recv_until(ws, "WELCOME")
        await clients[0].send(json.dumps(wire("CREATE_ROOM", name="web-human-0", seed=seed,
                                              mode_id=mode_id)))
        room_code = (await recv_until(clients[0], "ROOM_CREATED"))["room_code"]
        host_welcome = await recv_until(clients[0], "WELCOME")
        seats.append(host_welcome["seat_id"])
        for index, ws in enumerate(clients[1:], 1):
            await ws.send(json.dumps(wire("JOIN_ROOM", room_code=room_code, name=f"web-human-{index}")))
            welcome = await recv_until(ws, "WELCOME")
            seats.append(welcome["seat_id"])
            await ws.send(json.dumps(wire("READY", ready=True)))
        await clients[0].send(json.dumps(wire("START_GAME")))

        seen: list[set[str]] = [set() for _ in clients]

        async def drive(index: int, ws):
            while True:
                message = json.loads(await asyncio.wait_for(ws.recv(), 60))
                kind = message["type"]
                if audit_app is not None:
                    audit_seen.add(kind)
                    room = audit_app.state.room_manager.rooms[room_code].game
                    if room.session is not None:
                        raw = json.dumps(message, ensure_ascii=False)
                        for opponent_id in seats:
                            if opponent_id != seats[index]:
                                private_ids = room.session.state.cards_in(ZoneRef(ZoneType.HAND, opponent_id))
                                assert all(str(card_id) not in raw for card_id in private_ids), (
                                    kind, seats[index], opponent_id, tuple(map(str, private_ids)), message)
                        assert "deck_order" not in raw and "draw_pile" not in raw
                        if kind == "PROJECTION_UPDATE":
                            for player in message["projection"]["players"]:
                                if player["player_id"] != seats[index]:
                                    assert "hand" not in player
                                    actual = room.session.state.players[player["player_id"]]
                                    if actual.is_alive and actual.identity.value != "lord":
                                        assert player["identity_label"] == "未知"
                    if kind in {"DRAFT_REQUEST", "PENDING_REQUEST"}:
                        assert message["request"]["player_id"] == seats[index]
                if kind == "DRAFT_REQUEST":
                    request = message["request"]
                    await ws.send(json.dumps(wire("SUBMIT_DECISION", decision={
                        "request_id": request["request_id"], "value": request["choices"][0],
                    })))
                elif kind == "PENDING_REQUEST":
                    request = message["request"]
                    assert request["player_id"] == seats[index]
                    assert request["request_id"] not in seen[index]
                    seen[index].add(request["request_id"])
                    await ws.send(json.dumps(wire("SUBMIT_DECISION", decision={
                        "request_id": request["request_id"], "value": choose(request),
                    })))
                elif kind == "GAME_OVER":
                    return message
                elif kind == "ERROR":
                    if "general already taken" not in message.get("message", ""):
                        raise AssertionError(message)

        results = await asyncio.wait_for(asyncio.gather(*(drive(i, ws) for i, ws in enumerate(clients))), 180)
        assert all(result.get("result") for result in results)
        return room_code, seen
    finally:
        await asyncio.gather(*(ws.close() for ws in clients))


@pytest.mark.parametrize("humans", range(1, 6))
@pytest.mark.parametrize("seed", [4, 1, 2, 3])
def test_fastapi_websocket_full_game_smoke(humans, seed):
    async def scenario():
        app, server, task, url = await start_server()
        try:
            audit_seen = set() if (humans, seed) == (2, 4) else None
            room_code, seen = await play_web_match(
                url, humans, seed, app if audit_seen is not None else None, audit_seen,
            )
            if audit_seen is not None:
                assert {"LOBBY_STATE", "PROJECTION_UPDATE", "PUBLIC_EVENT", "PENDING_REQUEST", "GAME_OVER"} <= audit_seen
            room = app.state.room_manager.rooms[room_code].game
            assert room.phase.value == "FINISHED"
            assert room.session is not None
            assert room.session.state.victory is not None
            assert room.session.engine.pending_request is None
            assert room.session.engine.stack.is_empty()
            assert not room.session.state.cards_in(ZoneRef(ZoneType.PROCESSING))
            assert all(seen)
            assert len(room.session.state.cards) == len(set(room.session.state.cards))
            room.session.state.__post_init__()
        finally:
            server.should_exit = True
            await task

    asyncio.run(scenario())


def test_fastapi_websocket_eight_player_mixed_full_game():
    async def scenario():
        app, server, task, url = await start_server()
        try:
            room_code, seen = await play_web_match(
                url, humans=2, seed=8, audit_app=app, audit_seen=set(),
                mode_id="military-eight",
            )
            room = app.state.room_manager.rooms[room_code].game
            assert room.mode.mode_id == "military-eight"
            assert len(room.seats) == 8
            assert sum(seat.controller.value == "AI" for seat in room.seats.values()) == 6
            assert room.phase.value == "FINISHED"
            assert all(seen)
        finally:
            server.should_exit = True
            await task

    asyncio.run(scenario())


def test_fastapi_websocket_privacy_payload():
    async def scenario():
        app, server, task, url = await start_server()
        host = await websockets.connect(url)
        guest = await websockets.connect(url)
        host_payloads: list[dict] = []
        guest_payloads: list[dict] = []

        async def receive_recorded(ws, payloads, kind):
            while True:
                item = json.loads(await asyncio.wait_for(ws.recv(), 15))
                payloads.append(item)
                if item["type"] == kind:
                    return item

        try:
            await host.send(json.dumps(wire("HELLO")))
            await guest.send(json.dumps(wire("HELLO")))
            await receive_recorded(host, host_payloads, "WELCOME")
            await receive_recorded(guest, guest_payloads, "WELCOME")
            await host.send(json.dumps(wire("CREATE_ROOM", name="privacy-a", seed=7)))
            room_code = (await receive_recorded(host, host_payloads, "ROOM_CREATED"))["room_code"]
            host_welcome = await receive_recorded(host, host_payloads, "WELCOME")
            await guest.send(json.dumps(wire("JOIN_ROOM", room_code=room_code, name="privacy-b")))
            guest_welcome = await receive_recorded(guest, guest_payloads, "WELCOME")
            await guest.send(json.dumps(wire("READY", ready=True)))
            await host.send(json.dumps(wire("START_GAME")))
            host_draft = await receive_recorded(host, host_payloads, "DRAFT_REQUEST")
            guest_draft = await receive_recorded(guest, guest_payloads, "DRAFT_REQUEST")

            assert host_draft["request"]["player_id"] == host_welcome["seat_id"]
            assert guest_draft["request"]["player_id"] == guest_welcome["seat_id"]
            assert host_draft["request"]["request_id"] not in json.dumps(guest_payloads)
            assert guest_draft["request"]["request_id"] not in json.dumps(host_payloads)

            await host.send(json.dumps(wire("SUBMIT_DECISION", decision={
                "request_id": host_draft["request"]["request_id"],
                "value": host_draft["request"]["choices"][0],
            })))
            await guest.send(json.dumps(wire("SUBMIT_DECISION", decision={
                "request_id": guest_draft["request"]["request_id"],
                "value": guest_draft["request"]["choices"][0],
            })))
            host_projection = await receive_recorded(host, host_payloads, "PROJECTION_UPDATE")
            guest_projection = await receive_recorded(guest, guest_payloads, "PROJECTION_UPDATE")
            room = app.state.room_manager.rooms[room_code].game
            assert room.session is not None

            host_id = host_welcome["seat_id"]
            guest_id = guest_welcome["seat_id"]
            host_opponent = next(player for player in host_projection["projection"]["players"] if player["player_id"] == guest_id)
            guest_opponent = next(player for player in guest_projection["projection"]["players"] if player["player_id"] == host_id)
            assert "hand" not in host_opponent and "hand" not in guest_opponent
            assert host_opponent["hand_count"] >= 0 and guest_opponent["hand_count"] >= 0

            guest_hand_ids = set(room.session.state.cards_in(ZoneRef(ZoneType.HAND, guest_id)))
            host_raw = json.dumps(host_payloads, ensure_ascii=False)
            assert not any(str(card_id) in host_raw for card_id in guest_hand_ids)
            assert "deck_order" not in host_raw and "draw_pile" not in host_raw

            actual_guest_identity = room.session.state.players[guest_id].identity.value
            if actual_guest_identity != "lord":
                assert host_opponent["identity_label"] == "未知"

            pending = room.session.engine.pending_request
            if pending is not None:
                owner_payloads = host_payloads if str(pending.player_id) == host_id else guest_payloads
                other_payloads = guest_payloads if owner_payloads is host_payloads else host_payloads
                owner_ws = host if owner_payloads is host_payloads else guest
                await receive_recorded(owner_ws, owner_payloads, "PENDING_REQUEST")
                assert all(item["type"] != "PENDING_REQUEST" for item in other_payloads)
        finally:
            await host.close()
            await guest.close()
            server.should_exit = True
            await task

    asyncio.run(scenario())

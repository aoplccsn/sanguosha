from __future__ import annotations

import asyncio
import secrets

import pytest

from sanguosha.multiplayer.transport import GameServer
from sanguosha.multiplayer.protocol import decision_to_wire
from sanguosha.engine.requests import Decision
from sanguosha.model.ids import PlayerId
from sanguosha.model.zones import ZoneRef, ZoneType
from sanguosha.multiplayer.room import RoomPhase
from test_t8_multiplayer import choose
from sanguosha.relay.config import RelayConfig
from sanguosha.relay.protocol import ROOM_ALPHABET, RelayProtocolError, envelope
from sanguosha.relay.server import RelayServer
from sanguosha.relay.transport import HostRelayTransport, RelayGameClient
from sanguosha.session_store import clear_session, load_session, save_session


def test_room_alphabet_excludes_ambiguous_characters():
    assert not set("01IO").intersection(ROOM_ALPHABET)


def test_relay_message_rejects_unknown_type():
    with pytest.raises(RelayProtocolError):
        envelope("NOT_A_MESSAGE")


def test_session_store_contains_only_reconnect_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    save_session(relay_url="wss://relay.test", room_code="7KQ9MX", player_id="p2", reconnect_token="secret")
    payload = load_session()
    assert payload["room_code"] == "7KQ9MX"
    assert set(payload) == {"relay_url", "room_code", "player_id", "reconnect_token", "game_version", "timestamp"}
    clear_session()
    assert load_session() is None


def test_real_relay_round_trip_and_room_isolation():
    async def scenario():
        relay = RelayServer(RelayConfig(host="127.0.0.1", port=0, room_ttl=60, host_reconnect_grace=1))
        await relay.start()
        url = f"ws://127.0.0.1:{relay.config.port}"
        games = [GameServer(host="127.0.0.1", port=0, seed=n) for n in (1, 2)]
        hosts = []
        clients = []
        try:
            for game in games:
                await game.start()
                host = HostRelayTransport(url, "127.0.0.1", game.port)
                await host.start()
                hosts.append(host)
            assert hosts[0].room_code != hosts[1].room_code
            for index, host in enumerate(hosts):
                client = RelayGameClient(url, host.room_code)
                await client.connect(f"guest{index}")
                clients.append(client)
                for _ in range(8):
                    item = await asyncio.wait_for(client.receive(), 3)
                    if item["type"] == "WELCOME" and item.get("seat_id"):
                        break
                else:
                    raise AssertionError("missing seat welcome")
                assert item["seat_id"] == "p1"
                assert games[index].room.seats["p1"].name == f"guest{index}"
                assert games[1 - index].room.seats["p1"].name != f"guest{index}"
        finally:
            for client in clients:
                await client.close()
            for host in hosts:
                await host.close()
            for game in games:
                await game.close()
            await relay.close()
    asyncio.run(scenario())


def test_host_token_reconnect_and_invalid_token():
    async def scenario():
        relay = RelayServer(RelayConfig(host="127.0.0.1", port=0, host_reconnect_grace=2))
        await relay.start()
        url = f"ws://127.0.0.1:{relay.config.port}"
        game = GameServer(host="127.0.0.1", port=0)
        await game.start()
        first = HostRelayTransport(url, "127.0.0.1", game.port)
        code, token = await first.start()
        await first.close(close_room=False)
        await asyncio.sleep(.05)
        restored = HostRelayTransport(url, "127.0.0.1", game.port, room_code=code, host_token=token)
        try:
            assert (await restored.start())[0] == code
            bad = HostRelayTransport(url, "127.0.0.1", game.port, room_code=code, host_token=secrets.token_urlsafe())
            with pytest.raises(Exception):
                await bad.start()
        finally:
            await restored.close()
            await game.close()
            await relay.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("humans", range(1, 6))
@pytest.mark.parametrize("seed", [4, 1, 2, 3])
def test_relay_full_game_smoke(humans, seed):
    async def scenario():
        relay = RelayServer(RelayConfig(host="127.0.0.1", port=0, room_ttl=120))
        await relay.start()
        url = f"ws://127.0.0.1:{relay.config.port}"
        server = GameServer(host="127.0.0.1", port=0, seed=seed, timeout_seconds=30)
        await server.start()
        host = HostRelayTransport(url, "127.0.0.1", server.port)
        await host.start()
        clients = [RelayGameClient(url, host.room_code) for _ in range(humans)]
        try:
            for index, client in enumerate(clients):
                await client.connect(f"relay-human-{index}")

            async def play(client, index):
                seat_id = None
                seen_requests = set()
                while True:
                    msg = await asyncio.wait_for(client.receive(), 20)
                    kind = msg["type"]
                    if kind == "WELCOME" and msg.get("seat_id"):
                        seat_id = msg["seat_id"]
                        if index:
                            await client.send("READY", ready=True)
                    elif kind == "DRAFT_REQUEST":
                        request = msg["request"]
                        await client.send(
                            "SUBMIT_DECISION",
                            decision={
                                "request_id": request["request_id"],
                                "value": request["choices"][0],
                            },
                        )
                    elif kind == "PENDING_REQUEST":
                        request = msg["request"]
                        assert request["player_id"] == seat_id
                        assert request["request_id"] not in seen_requests
                        seen_requests.add(request["request_id"])
                        await client.send(
                            "SUBMIT_DECISION",
                            decision=decision_to_wire(
                                Decision(
                                    request["request_id"],
                                    PlayerId(seat_id),
                                    choose(request),
                                )
                            ),
                        )
                    elif kind == "GAME_OVER":
                        assert seat_id is not None
                        assert seen_requests
                        return
                    elif kind == "ERROR":
                        if msg["message"] != "general already taken; new candidates sent":
                            raise AssertionError(msg["message"])

            tasks = [asyncio.create_task(play(client, i)) for i, client in enumerate(clients)]
            while any(
                server.room.seats[PlayerId(f"p{i + 1}")].ready is False
                for i in range(1, humans)
            ):
                await asyncio.sleep(0.005)
            await clients[0].send("START_GAME")
            await asyncio.wait_for(asyncio.gather(*tasks), 45)
            assert server.room.phase is RoomPhase.FINISHED
            assert server.room.session.engine.pending_request is None
            assert server.room.session.engine.stack.is_empty()
            assert server.room.session.state.victory is not None
            server.room.session.state.__post_init__()
            assert not server.room.session.state.cards_in(ZoneRef(ZoneType.PROCESSING))
        finally:
            for client in clients:
                await client.close()
            await host.close()
            await server.close()
            await relay.close()

    asyncio.run(scenario())

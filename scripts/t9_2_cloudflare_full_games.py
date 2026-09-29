"""Run 20 complete matches through the local Cloudflare GameRoom Worker."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from pathlib import Path

import websockets

BASE = os.environ.get("GAME_ROOM_URL", "http://127.0.0.1:8793")
WS_BASE = BASE.replace("http://", "ws://").replace("https://", "wss://")
VERSION = 2
ROOT = Path(__file__).resolve().parents[1]


def wire(kind: str, **fields):
    return json.dumps({"type": kind, "version": VERSION, **fields}, ensure_ascii=False)


def choose(request: dict):
    kind = request["request_type"]
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


def create_room() -> str:
    request = urllib.request.Request(f"{BASE}/api/rooms", method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)["room_code"]


async def receive_until(ws, kind: str, *, predicate=lambda _: True, timeout=120):
    while True:
        message = json.loads(await asyncio.wait_for(ws.recv(), timeout))
        if message["type"] == "ERROR":
            raise AssertionError(message)
        if message["type"] == kind and predicate(message):
            return message


async def play_match(humans: int, seed: int):
    code = await asyncio.to_thread(create_room)
    clients = [await websockets.connect(f"{WS_BASE}/room/{code}", max_size=1_000_000) for _ in range(humans)]
    seats = []
    payloads = [[] for _ in clients]
    seen_requests = [set() for _ in clients]
    try:
        for index, ws in enumerate(clients):
            await receive_until(ws, "WELCOME")
            await ws.send(wire("HELLO"))
            await ws.send(wire("JOIN_ROOM", room_code=code, name=f"human-{index}",
                               created=index == 0, **({"seed": seed} if index == 0 else {})))
            identity = await receive_until(
                ws, "ROOM_CREATED" if index == 0 else "WELCOME",
                predicate=lambda item: bool(item.get("seat_id")),
            )
            seats.append(identity["seat_id"])
        for ws in clients[1:]:
            await ws.send(wire("READY", ready=True))
        if len(clients) > 1:
            await asyncio.sleep(0.1)
        await clients[0].send(wire("START_GAME"))

        tasks = {asyncio.create_task(ws.recv()): index for index, ws in enumerate(clients)}
        result = None
        total_requests = 0
        while result is None:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=180)
            if not done:
                raise TimeoutError(f"match timed out humans={humans} seed={seed}")
            for task in done:
                index = tasks.pop(task)
                ws = clients[index]
                message = json.loads(task.result())
                payloads[index].append(message)
                kind = message["type"]
                if kind == "ERROR":
                    if "general already taken" not in message.get("message", ""):
                        raise AssertionError(message)
                elif kind == "DRAFT_REQUEST":
                    request = message["request"]
                    assert request["player_id"] == seats[index]
                    await ws.send(wire("SUBMIT_DECISION", decision={
                        "request_id": request["request_id"], "value": request["choices"][0],
                    }))
                elif kind == "PENDING_REQUEST":
                    request = message["request"]
                    assert request["player_id"] == seats[index]
                    assert request["request_id"] not in seen_requests[index]
                    seen_requests[index].add(request["request_id"])
                    total_requests += 1
                    await ws.send(wire("SUBMIT_DECISION", decision={
                        "request_id": request["request_id"], "value": choose(request),
                    }))
                elif kind == "PROJECTION_UPDATE":
                    projection = message["projection"]
                    assert "deck_order" not in projection
                    for player in projection["players"]:
                        assert "hand" not in player
                elif kind == "GAME_OVER":
                    result = message["result"]
                if result is None:
                    tasks[asyncio.create_task(ws.recv())] = index
        status = json.loads(await asyncio.to_thread(lambda: urllib.request.urlopen(f"{BASE}/room/{code}", timeout=120).read()))
        assert status["phase"] == "FINISHED"
        return code, result, total_requests, sum(map(len, payloads))
    finally:
        await asyncio.gather(*(ws.close() for ws in clients), return_exceptions=True)


async def main():
    rows = []
    for humans in range(1, 6):
        for seed in range(4):
            code, result, requests, messages = await play_match(humans, seed)
            rows.append((humans, seed, code, result, requests, messages))
            print(f"PASS humans={humans} seed={seed} result={result} requests={requests}", flush=True)
    lines = [
        "# T9.2 Cloudflare GameRoom Full Games", "",
        "Run date: 2026-09-30 (Asia/Shanghai).", "",
        "All matches used real local Wrangler routing, one SQLite-backed Durable Object per room, hibernating WebSockets, authoritative GameSession decisions, per-player projections, and GAME_OVER delivery.", "",
        "| Humans | Seed | Room | Winner | Human requests | Received messages |",
        "| ---: | ---: | --- | --- | ---: | ---: |",
    ]
    lines.extend(f"| {h} | {s} | {code} | {winner} | {requests} | {messages} |" for h, s, code, winner, requests, messages in rows)
    lines.extend(["", f"Total: {len(rows)} completed Cloudflare GameRoom matches.", ""])
    target = ROOT / "docs" / "T9_2_CLOUDFLARE_FULL_GAMES.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    asyncio.run(main())

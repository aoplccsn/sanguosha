from __future__ import annotations

import json
import secrets
import time
from urllib.parse import parse_qs, urlparse

from js import WebSocketPair
from workers import DurableObject, Response, WorkerEntrypoint

from sanguosha.engine.requests import Decision
from sanguosha.model.ids import PlayerId
from sanguosha.multiplayer.protocol import (
    MAX_MESSAGE_BYTES,
    ProtocolError,
    check_message,
    decision_from_wire,
    envelope,
)
from sanguosha.multiplayer.room import MultiplayerRoom, RoomError, RoomPhase
from sanguosha.room_snapshot import restore_room, snapshot_room

ROOM_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ROOM_CODE_LENGTH = 6
SNAPSHOT_KEY = "room_snapshot"
ROOM_CODE_KEY = "room_code"
LAST_ACTIVE_KEY = "last_active_ms"
PROTOCOL_VERSION = 2


def _attachment(ws) -> dict:
    value = ws.deserializeAttachment()
    if not value:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    return value.to_py() if hasattr(value, "to_py") else dict(value)


def _save_attachment(ws, value: dict) -> None:
    # Structured-clone cannot clone a Pyodide dict proxy. JSON is portable across
    # hibernation and preserves every routing/reconnect field we need.
    ws.serializeAttachment(json.dumps(value, separators=(",", ":")))


def _room_code() -> str:
    return "".join(secrets.choice(ROOM_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def _normalize_room_code(value: str) -> str:
    code = (value or "").strip().upper()
    if len(code) != ROOM_CODE_LENGTH or any(char not in ROOM_ALPHABET for char in code):
        raise ValueError("invalid room code")
    return code


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path
        if path == "/health":
            return Response.json({"ok": True, "runtime": "cloudflare-python"})
        if path == "/api/rooms" and request.method == "POST":
            for _ in range(32):
                code = _room_code()
                stub = self.env.GAME_ROOMS.getByName(code)
                response = await stub.fetch(f"https://room.internal/init/{code}", method="POST")
                if response.status == 201:
                    return Response.json({"room_code": code}, status=201)
            return Response.json({"error": "unable to allocate room code"}, status=503)
        if path.startswith("/room/"):
            try:
                code = _normalize_room_code(path.split("/", 3)[2])
            except ValueError as exc:
                return Response.json({"error": str(exc)}, status=400)
            return await self.env.GAME_ROOMS.getByName(code).fetch(request)
        return await self.env.ASSETS.fetch(request)


class GameRoomDurableObject(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.room: MultiplayerRoom | None = None
        self.room_code = ""
        self.sockets: dict[str, object] = {}
        self.rate: dict[str, tuple[int, int]] = {}
        for ws in self.ctx.getWebSockets():
            attachment = _attachment(ws)
            if attachment and attachment.get("session_id"):
                self.sockets[attachment["session_id"]] = ws

    async def _load(self) -> bool:
        if self.room is not None:
            return True
        blob = await self.ctx.storage.get(SNAPSHOT_KEY)
        self.room_code = await self.ctx.storage.get(ROOM_CODE_KEY) or self.room_code
        if blob is None:
            return False
        if isinstance(blob, str):
            blob = blob.encode("utf-8")
        self.room = restore_room(blob)
        self._rebind_sockets()
        return True

    def _rebind_sockets(self) -> None:
        if self.room is None:
            return
        for ws in self.ctx.getWebSockets():
            attachment = _attachment(ws)
            player_id = attachment.get("player_id")
            session_id = attachment.get("session_id")
            if not player_id or not session_id:
                continue
            pid = PlayerId(player_id)
            seat = self.room.seats.get(pid)
            if seat is None or seat.token != attachment.get("reconnect_token"):
                continue
            seat.connected = True
            seat.send = self._sender(ws)
            self.sockets[session_id] = ws

    def _sender(self, ws):
        def send(message: dict) -> None:
            ws.send(json.dumps(message, ensure_ascii=False, separators=(",", ":")))
        return send

    async def _persist(self) -> None:
        if self.room is None:
            return
        now_ms = int(time.time() * 1000)
        await self.ctx.storage.put(SNAPSHOT_KEY, snapshot_room(self.room).decode("utf-8"))
        await self.ctx.storage.put(LAST_ACTIVE_KEY, now_ms)
        await self._schedule_alarm(now_ms)

    async def _schedule_alarm(self, now_ms: int | None = None) -> None:
        if self.room is None:
            return
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        deadlines = list(self.room.draft_deadlines.values())
        if self.room.request_deadline is not None:
            deadlines.append(self.room.request_deadline)
        ttl_seconds = int(getattr(self.env, "ROOM_TTL_SECONDS", "7200"))
        deadlines.append(now_ms / 1000 + ttl_seconds)
        await self.ctx.storage.setAlarm(int(min(deadlines) * 1000))

    async def fetch(self, request):
        parsed = urlparse(request.url)
        if parsed.path.startswith("/init/") and request.method == "POST":
            code = _normalize_room_code(parsed.path.rsplit("/", 1)[-1])
            existing = await self.ctx.storage.get(ROOM_CODE_KEY)
            if existing is not None:
                return Response.json({"room_code": existing}, status=200)
            self.room_code = code
            self.room = MultiplayerRoom()
            await self.ctx.storage.put(ROOM_CODE_KEY, code)
            await self._persist()
            return Response.json({"room_code": code}, status=201)

        if request.headers.get("Upgrade", "").lower() != "websocket":
            if not await self._load():
                return Response.json({"error": "room not found"}, status=404)
            return Response.json({"room_code": self.room_code, "phase": self.room.phase.value})
        if not await self._load():
            return Response.json({"error": "room not found"}, status=404)
        maximum = int(getattr(self.env, "MAX_CONNECTIONS_PER_ROOM", "5"))
        if len(self.ctx.getWebSockets()) >= maximum:
            return Response.json({"error": "room connection limit reached"}, status=429)
        client, server = WebSocketPair.new().object_values()
        session_id = secrets.token_urlsafe(18)
        attachment = {
            "player_id": "",
            "seat": "",
            "room_code": self.room_code,
            "reconnect_token": "",
            "session_id": session_id,
            "protocol_version": PROTOCOL_VERSION,
        }
        self.ctx.acceptWebSocket(server)
        _save_attachment(server, attachment)
        self.sockets[session_id] = server
        server.send(json.dumps(envelope("WELCOME", room_code=self.room_code)))
        return Response(None, status=101, web_socket=client)

    def _check_rate(self, session_id: str) -> None:
        window = int(time.time() // 10)
        previous_window, count = self.rate.get(session_id, (window, 0))
        count = count + 1 if previous_window == window else 1
        self.rate[session_id] = (window, count)
        limit = int(getattr(self.env, "MESSAGE_RATE_PER_10_SECONDS", "300"))
        if count > limit:
            raise ProtocolError("message rate limit exceeded")

    async def webSocketMessage(self, ws, raw):
        attachment = _attachment(ws)
        session_id = attachment.get("session_id", "")
        try:
            self._check_rate(session_id)
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
                raise ProtocolError("message is too large")
            message = json.loads(raw)
            check_message(message)
            await self._handle_message(ws, attachment, message)
            await self._persist()
        except (ProtocolError, RoomError, ValueError, KeyError, json.JSONDecodeError) as exc:
            ws.send(json.dumps(envelope("ERROR", message=str(exc))))

    async def _handle_message(self, ws, attachment: dict, message: dict) -> None:
        assert self.room is not None
        kind = message["type"]
        if kind == "HELLO":
            return
        if kind == "PING":
            ws.send(json.dumps(envelope("PONG")))
            return
        if kind not in {"JOIN_ROOM", "RECONNECT"} and not attachment.get("player_id"):
            raise ProtocolError("join or reconnect is required")
        if kind in {"JOIN_ROOM", "RECONNECT"}:
            requested = _normalize_room_code(message.get("room_code", self.room_code))
            if requested != self.room_code:
                raise RoomError("room code mismatch")
            if kind == "JOIN_ROOM" and message.get("created") and self.room.host_id is None:
                seed = message.get("seed")
                if seed is not None:
                    if type(seed) is not int or seed < 0:
                        raise ProtocolError("seed must be a non-negative integer")
                    self.room.seed = seed
            token = message.get("token") if kind == "RECONNECT" else None
            pid, reconnect_token = self.room.join(message.get("name", "player"), self._sender(ws), token=token)
            attachment.update({
                "player_id": str(pid),
                "seat": str(pid),
                "reconnect_token": reconnect_token,
            })
            _save_attachment(ws, attachment)
            ws.send(json.dumps(envelope("ROOM_CREATED" if message.get("created") else "WELCOME",
                                        room_code=self.room_code, seat_id=str(pid),
                                        reconnect_token=reconnect_token)))
            if message.get("created"):
                ws.send(json.dumps(envelope("WELCOME", room_code=self.room_code, seat_id=str(pid),
                                            reconnect_token=reconnect_token)))
            self.room._send_current(pid)
            if message.get("single_player") is True:
                self.room.start(pid)
            return
        pid = PlayerId(attachment["player_id"])
        if kind == "READY":
            self.room.ready(pid, message.get("ready"))
        elif kind == "START_GAME":
            self.room.start(pid)
        elif kind == "SUBMIT_DECISION":
            self.room.submit(pid, decision_from_wire(message.get("decision"), pid))
        elif kind == "TAKEOVER_AI":
            self.room.takeover_ai(pid, PlayerId(message["seat_id"]))
        elif kind == "LEAVE_ROOM":
            self.room.disconnect(pid)
            ws.close(1000, "left room")
        else:
            raise ProtocolError(f"unsupported client message: {kind}")

    async def webSocketClose(self, ws, code, reason, was_clean):
        await self._disconnect(ws)

    async def webSocketError(self, ws, error):
        await self._disconnect(ws)

    async def _disconnect(self, ws):
        if not await self._load():
            return
        attachment = _attachment(ws)
        session_id = attachment.get("session_id")
        if session_id:
            self.sockets.pop(session_id, None)
            self.rate.pop(session_id, None)
        player_id = attachment.get("player_id")
        if player_id:
            self.room.disconnect(PlayerId(player_id))
            await self._persist()

    async def alarm(self):
        if not await self._load():
            return
        now = time.time()
        last_active_ms = await self.ctx.storage.get(LAST_ACTIVE_KEY) or int(now * 1000)
        ttl_seconds = int(getattr(self.env, "ROOM_TTL_SECONDS", "7200"))
        if not self.ctx.getWebSockets() and now * 1000 - last_active_ms >= ttl_seconds * 1000:
            await self.ctx.storage.deleteAll()
            self.room = None
            return
        self.room.poll()
        await self._persist()

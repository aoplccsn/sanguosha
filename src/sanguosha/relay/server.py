from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

try:
    from websockets.asyncio.server import serve
except ImportError:
    from websockets.server import serve

from .config import RelayConfig
from .protocol import ROOM_ALPHABET, ROOM_CODE_LENGTH, RelayProtocolError, decode, encode, envelope

LOG = logging.getLogger("sanguosha.relay")


@dataclass(slots=True)
class Channel:
    channel_id: str
    guest: Any


@dataclass(slots=True)
class Room:
    code: str
    host_token: str
    host: Any
    created_at: float
    last_activity: float
    state: str = "LOBBY"
    host_deadline: float | None = None
    channels: dict[str, Channel] = field(default_factory=dict)


class RelayServer:
    def __init__(self, config: RelayConfig | None = None):
        self.config = config or RelayConfig.from_env()
        self.rooms: dict[str, Room] = {}
        self._server = None
        self._cleanup_task = None
        self._connections = defaultdict(int)
        self._creation_times = defaultdict(deque)
        self._send_locks = {}

    async def start(self) -> None:
        self._server = await serve(
            self._handle, self.config.host, self.config.port,
            max_size=300_000, ping_interval=20, ping_timeout=20, close_timeout=5,
        )
        if self._server.sockets:
            self.config.port = self._server.sockets[0].getsockname()[1]
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def close(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        for room in list(self.rooms.values()):
            await self._close_room(room, "relay shutting down")
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _send(self, websocket, payload: dict) -> None:
        lock = self._send_locks.setdefault(id(websocket), asyncio.Lock())
        async with lock:
            await websocket.send(encode(payload))

    async def _error(self, websocket, text: str) -> None:
        try:
            await self._send(websocket, envelope("ERROR", message=text))
        except Exception:
            pass

    def _peer_ip(self, websocket) -> str:
        remote = getattr(websocket, "remote_address", None)
        return str(remote[0]) if remote else "unknown"

    async def _handle(self, websocket) -> None:
        ip = self._peer_ip(websocket)
        if self._connections[ip] >= self.config.max_connections_per_ip:
            await self._error(websocket, "connection limit exceeded")
            await websocket.close(code=1008)
            return
        self._connections[ip] += 1
        try:
            first = decode(await asyncio.wait_for(websocket.recv(), 15))
            if first["type"] == "CREATE_ROOM":
                await self._host_session(websocket, first, ip)
            elif first["type"] == "JOIN_ROOM":
                await self._guest_session(websocket, first)
            else:
                raise RelayProtocolError("CREATE_ROOM or JOIN_ROOM required")
        except RelayProtocolError as exc:
            await self._error(websocket, str(exc))
        except asyncio.TimeoutError:
            await self._error(websocket, "relay handshake timed out")
        except Exception as exc:
            if not type(exc).__name__.startswith("ConnectionClosed"):
                LOG.warning("relay connection failed: %s", exc)
        finally:
            self._connections[ip] = max(0, self._connections[ip] - 1)
            self._send_locks.pop(id(websocket), None)

    def _allow_creation(self, ip: str) -> bool:
        now = time.monotonic()
        entries = self._creation_times[ip]
        while entries and now - entries[0] > 60:
            entries.popleft()
        if len(entries) >= self.config.room_creations_per_minute:
            return False
        entries.append(now)
        return True

    def _new_code(self) -> str:
        for _ in range(100):
            code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(ROOM_CODE_LENGTH))
            if code not in self.rooms:
                return code
        raise RuntimeError("room code capacity exhausted")

    async def _host_session(self, websocket, first: dict, ip: str) -> None:
        requested = str(first.get("room_code") or "").upper()
        supplied_token = str(first.get("host_token") or "")
        if requested:
            room = self.rooms.get(requested)
            if room is None or not secrets.compare_digest(room.host_token, supplied_token):
                raise RelayProtocolError("invalid host token")
            if room.host is not None and room.host is not websocket:
                raise RelayProtocolError("host is already connected")
            room.host = websocket
            room.host_deadline = None
            room.last_activity = time.monotonic()
            for channel in list(room.channels.values()):
                await self._error(channel.guest, "房主已恢复，请重新连接房间")
            room.channels.clear()
        else:
            if len(self.rooms) >= self.config.max_rooms:
                raise RelayProtocolError("relay room capacity reached")
            if not self._allow_creation(ip):
                raise RelayProtocolError("room creation rate limit exceeded")
            now = time.monotonic()
            room = Room(self._new_code(), secrets.token_urlsafe(32), websocket, now, now)
            self.rooms[room.code] = room
            LOG.info("room created code=%s host_token=%s", room.code, self._token_tag(room.host_token))
        await self._send(websocket, envelope(
            "ROOM_CREATED", room_code=room.code, host_token=room.host_token,
            host_reconnect_grace=self.config.host_reconnect_grace,
        ))
        try:
            async for raw in websocket:
                payload = decode(raw)
                room.last_activity = time.monotonic()
                kind = payload["type"]
                channel_id = str(payload.get("channel_id", ""))
                if kind == "CHANNEL_DATA":
                    channel = room.channels.get(channel_id)
                    if channel is None:
                        raise RelayProtocolError("unknown logical channel")
                    await self._send(channel.guest, envelope(
                        "CHANNEL_DATA", channel_id=channel_id, payload=payload.get("payload")
                    ))
                elif kind == "CHANNEL_CLOSED":
                    channel = room.channels.pop(channel_id, None)
                    if channel:
                        await self._error(channel.guest, "host closed channel")
                        await channel.guest.close()
                elif kind == "ROOM_STATE":
                    state = str(payload.get("state", ""))
                    if state not in {"LOBBY", "IN_GAME", "FINISHED"}:
                        raise RelayProtocolError("invalid room state")
                    room.state = state
                    if state == "FINISHED":
                        await self._close_room(room, "game finished")
                        return
                elif kind == "CLOSE_ROOM":
                    if not secrets.compare_digest(room.host_token, str(payload.get("host_token", ""))):
                        raise RelayProtocolError("invalid host token")
                    await self._close_room(room, "host closed room")
                    return
                elif kind == "PING":
                    await self._send(websocket, envelope("PONG"))
                else:
                    raise RelayProtocolError("unexpected host relay message")
        finally:
            if self.rooms.get(room.code) is room and room.host is websocket:
                room.host = None
                room.host_deadline = time.monotonic() + self.config.host_reconnect_grace
                for channel in list(room.channels.values()):
                    try:
                        await self._send(channel.guest, envelope(
                            "HOST_RECONNECTING", room_code=room.code,
                            remaining_seconds=self.config.host_reconnect_grace,
                        ))
                    except Exception:
                        pass

    async def _guest_session(self, websocket, first: dict) -> None:
        code = str(first.get("room_code") or "").strip().upper()
        room = self.rooms.get(code)
        if room is None:
            raise RelayProtocolError("房间码不存在或已失效")
        if room.host is None:
            raise RelayProtocolError("房主正在重连，请稍后再试")
        if len(room.channels) >= 5:
            raise RelayProtocolError("房间已满")
        channel_id = secrets.token_urlsafe(18)
        room.channels[channel_id] = Channel(channel_id, websocket)
        room.last_activity = time.monotonic()
        await self._send(room.host, envelope("GUEST_JOINED", room_code=code, channel_id=channel_id))
        await self._send(websocket, envelope("ROOM_JOINED", room_code=code, channel_id=channel_id))
        try:
            async for raw in websocket:
                payload = decode(raw)
                room.last_activity = time.monotonic()
                if payload["type"] == "CHANNEL_DATA":
                    if str(payload.get("channel_id", "")) != channel_id:
                        raise RelayProtocolError("logical channel mismatch")
                    if room.host is None:
                        raise RelayProtocolError("房主正在重连")
                    await self._send(room.host, envelope(
                        "CHANNEL_DATA", channel_id=channel_id, payload=payload.get("payload")
                    ))
                elif payload["type"] == "PING":
                    await self._send(websocket, envelope("PONG"))
                else:
                    raise RelayProtocolError("unexpected guest relay message")
        finally:
            existing = room.channels.get(channel_id)
            if existing is not None and existing.guest is websocket:
                room.channels.pop(channel_id, None)
                if room.host is not None:
                    try:
                        await self._send(room.host, envelope("CHANNEL_CLOSED", channel_id=channel_id))
                    except Exception:
                        pass

    async def _close_room(self, room: Room, reason: str) -> None:
        if self.rooms.pop(room.code, None) is None:
            return
        for channel in list(room.channels.values()):
            await self._error(channel.guest, reason)
            try:
                await channel.guest.close()
            except Exception:
                pass
        room.channels.clear()
        LOG.info("room closed code=%s reason=%s", room.code, reason)

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(1)
            now = time.monotonic()
            for room in list(self.rooms.values()):
                if room.host_deadline is not None and now >= room.host_deadline:
                    await self._close_room(room, "host reconnect grace expired")
                elif now - room.last_activity >= self.config.room_ttl:
                    await self._close_room(room, "room expired")

    @staticmethod
    def _token_tag(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:10]


async def run_server() -> None:
    config = RelayConfig.from_env()
    logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
    server = RelayServer(config)
    await server.start()
    LOG.info("relay listening on %s:%s", config.host, config.port)
    try:
        await asyncio.Event().wait()
    finally:
        await server.close()


def main() -> None:
    asyncio.run(run_server())

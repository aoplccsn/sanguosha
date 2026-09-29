from __future__ import annotations

import asyncio
from typing import Any

try:
    from websockets.asyncio.client import connect
except ImportError:
    from websockets.client import connect

from sanguosha.multiplayer.protocol import ProtocolError, decode as game_decode
from sanguosha.multiplayer.protocol import encode as game_encode
from sanguosha.multiplayer.protocol import envelope as game_envelope

from .protocol import RelayProtocolError, decode, encode, envelope


class HostRelayTransport:
    def __init__(self, relay_url: str, local_host: str, local_port: int, *,
                 room_code: str | None = None, host_token: str | None = None):
        self.relay_url = relay_url
        self.local_host = local_host
        self.local_port = local_port
        self.room_code = room_code
        self.host_token = host_token
        self.websocket = None
        self._send_lock = asyncio.Lock()
        self._receiver = None
        self._channels = {}

    async def start(self):
        self.websocket = await connect(
            self.relay_url, max_size=300_000, ping_interval=20, ping_timeout=20, close_timeout=5
        )
        await self._send(envelope(
            "CREATE_ROOM", room_code=self.room_code, host_token=self.host_token, state="LOBBY"
        ))
        response = decode(await self.websocket.recv())
        if response["type"] == "ERROR":
            raise RelayProtocolError(response.get("message", "relay rejected room"))
        if response["type"] != "ROOM_CREATED":
            raise RelayProtocolError("ROOM_CREATED required")
        self.room_code = response["room_code"]
        self.host_token = response["host_token"]
        self._receiver = asyncio.create_task(self._receive_loop())
        return self.room_code, self.host_token

    async def _send(self, payload: dict) -> None:
        if self.websocket is None:
            raise ConnectionError("relay is not connected")
        async with self._send_lock:
            await self.websocket.send(encode(payload))

    async def _receive_loop(self) -> None:
        async for raw in self.websocket:
            payload = decode(raw)
            kind = payload["type"]
            channel_id = str(payload.get("channel_id", ""))
            if kind == "GUEST_JOINED":
                reader, writer = await asyncio.open_connection(self.local_host, self.local_port)
                task = asyncio.create_task(self._local_to_relay(channel_id, reader))
                self._channels[channel_id] = (writer, task)
            elif kind == "CHANNEL_DATA":
                channel = self._channels.get(channel_id)
                if channel is None:
                    await self._send(envelope("CHANNEL_CLOSED", channel_id=channel_id))
                    continue
                channel[0].write(game_encode(payload.get("payload")))
                await channel[0].drain()
            elif kind == "CHANNEL_CLOSED":
                await self._close_channel(channel_id)
            elif kind == "PING":
                await self._send(envelope("PONG"))
            elif kind == "ERROR":
                raise RelayProtocolError(payload.get("message", "relay error"))

    async def _local_to_relay(self, channel_id: str, reader: asyncio.StreamReader) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                await self._send(envelope(
                    "CHANNEL_DATA", channel_id=channel_id, payload=game_decode(line)
                ))
        finally:
            try:
                await self._send(envelope("CHANNEL_CLOSED", channel_id=channel_id))
            except Exception:
                pass

    async def set_room_state(self, state: str) -> None:
        await self._send(envelope("ROOM_STATE", state=state))

    async def _close_channel(self, channel_id: str) -> None:
        channel = self._channels.pop(channel_id, None)
        if channel:
            writer, task = channel
            if task is not asyncio.current_task():
                task.cancel()
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def close(self, *, close_room: bool = True) -> None:
        if close_room and self.websocket and self.host_token:
            try:
                await self._send(envelope("CLOSE_ROOM", host_token=self.host_token))
            except Exception:
                pass
        for channel_id in list(self._channels):
            await self._close_channel(channel_id)
        if self._receiver:
            self._receiver.cancel()
            try:
                await self._receiver
            except BaseException:
                pass
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


class RelayGameClient:
    def __init__(self, relay_url: str, room_code: str):
        self.relay_url = relay_url
        self.room_code = room_code.strip().upper()
        self.websocket = None
        self.channel_id = None
        self._send_lock = asyncio.Lock()

    async def connect(self, name: str, *, token: str | None = None) -> None:
        self.websocket = await connect(
            self.relay_url, max_size=300_000, ping_interval=20, ping_timeout=20, close_timeout=5
        )
        await self._relay_send(envelope("JOIN_ROOM", room_code=self.room_code))
        response = decode(await self.websocket.recv())
        if response["type"] == "ERROR":
            raise ProtocolError(response.get("message", "relay rejected connection"))
        if response["type"] != "ROOM_JOINED":
            raise ProtocolError("ROOM_JOINED required")
        self.channel_id = response["channel_id"]
        await self.send("HELLO")
        welcome = await self.receive()
        if welcome["type"] != "WELCOME":
            raise ProtocolError(welcome.get("message", "server rejected connection"))
        await self.send("JOIN_ROOM", name=name, token=token)

    async def _relay_send(self, payload: dict) -> None:
        if self.websocket is None:
            raise ConnectionError("relay client is not connected")
        async with self._send_lock:
            await self.websocket.send(encode(payload))

    async def send(self, kind: str, **fields: Any) -> None:
        if self.channel_id is None:
            raise ConnectionError("relay channel is not ready")
        await self._relay_send(envelope(
            "CHANNEL_DATA", channel_id=self.channel_id, payload=game_envelope(kind, **fields)
        ))

    async def receive(self):
        if self.websocket is None:
            raise ConnectionError("relay client is not connected")
        while True:
            payload = decode(await self.websocket.recv())
            kind = payload["type"]
            if kind == "CHANNEL_DATA":
                if payload.get("channel_id") != self.channel_id:
                    raise ProtocolError("relay logical channel mismatch")
                game_message = payload.get("payload")
                if not isinstance(game_message, dict):
                    raise ProtocolError("invalid relayed game message")
                return game_message
            if kind == "HOST_RECONNECTING":
                raise ConnectionError("房主正在重新连接")
            if kind == "ERROR":
                raise ProtocolError(payload.get("message", "relay error"))
            if kind == "PING":
                await self._relay_send(envelope("PONG"))

    async def close(self) -> None:
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.channel_id = None

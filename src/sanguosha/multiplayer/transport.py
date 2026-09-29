"""Reliable ordered TCP transport for one authoritative room."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sanguosha.model.ids import PlayerId
from sanguosha.engine.errors import InvalidDecision

from .protocol import (DEFAULT_GAME_PORT, MAX_MESSAGE_BYTES, PROTOCOL_VERSION,
                       ProtocolError, decision_from_wire, decode, encode, envelope)
from .room import MultiplayerRoom, RoomError

LOG = logging.getLogger(__name__)


class GameServer:
    def __init__(self, *, host: str = "0.0.0.0", port: int = DEFAULT_GAME_PORT,
                 seed: int | None = None, timeout_seconds: float = 30.0):
        self.host, self.port = host, port
        self.room = MultiplayerRoom(seed=seed, timeout_seconds=timeout_seconds)
        self._server: asyncio.Server | None = None
        self._poll_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self.host, self.port,
                                                  limit=MAX_MESSAGE_BYTES + 1)
        self.port = self._server.sockets[0].getsockname()[1]
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def close(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(0.05)
            try:
                self.room.poll()
            except Exception:
                LOG.exception("room timer failed")

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        pid: PlayerId | None = None
        def send(message: dict) -> None:
            if not writer.is_closing():
                writer.write(encode(message))

        try:
            hello = await self._read(reader)
            if hello["type"] != "HELLO":
                raise ProtocolError("HELLO required")
            send(envelope("WELCOME", protocol_version=PROTOCOL_VERSION))
            while True:
                try:
                    message = await self._read(reader)
                    kind = message["type"]
                    if kind == "JOIN_ROOM":
                        if pid is not None:
                            raise RoomError("already joined")
                        pid, token = self.room.join(message.get("name"), send, token=message.get("token"))
                        send(envelope("WELCOME", seat_id=str(pid), reconnect_token=token,
                                      host_id=self.room.host_id))
                        self.room._send_current(pid)
                    elif kind == "PING":
                        send(envelope("PONG"))
                    elif pid is None:
                        raise RoomError("join room first")
                    elif kind == "READY":
                        self.room.ready(pid, message.get("ready"))
                    elif kind == "START_GAME":
                        self.room.start(pid)
                    elif kind == "SUBMIT_DECISION":
                        self.room.submit(pid, decision_from_wire(message.get("decision"), pid))
                    elif kind == "TAKEOVER_AI":
                        self.room.takeover_ai(pid, PlayerId(message.get("seat_id", "")))
                    else:
                        raise ProtocolError("unexpected client message")
                except (ProtocolError, RoomError, InvalidDecision, ValueError) as exc:
                    LOG.info("client request rejected: %s", exc)
                    send(envelope("ERROR", message=str(exc)))
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
            pass
        except (ProtocolError, RoomError, ValueError) as exc:
            try:
                send(envelope("ERROR", message=str(exc)))
                await writer.drain()
            except (ConnectionError, RuntimeError):
                pass
            LOG.info("client request rejected: %s", exc)
        except Exception:
            LOG.exception("unexpected client error")
            try:
                send(envelope("ERROR", message="server error"))
                await writer.drain()
            except (ConnectionError, RuntimeError):
                pass
        finally:
            if pid is not None and self.room.seats[pid].send is send:
                self.room.disconnect(pid)
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    @staticmethod
    async def _read(reader: asyncio.StreamReader) -> dict[str, Any]:
        line = await reader.readline()
        if not line:
            raise asyncio.IncompleteReadError(b"", 1)
        return decode(line)


class GameClient:
    """Socket client used by guests and by the host over loopback."""

    def __init__(self, host: str, port: int = DEFAULT_GAME_PORT):
        self.host, self.port = host, port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def connect(self, name: str, *, token: str | None = None) -> None:
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        await self.send("HELLO")
        welcome = await self.receive()
        if welcome["type"] != "WELCOME":
            raise ProtocolError(welcome.get("message", "server rejected connection"))
        await self.send("JOIN_ROOM", name=name, token=token)

    async def send(self, kind: str, **fields: Any) -> None:
        if self.writer is None:
            raise ConnectionError("client is not connected")
        self.writer.write(encode(envelope(kind, **fields)))
        await self.writer.drain()

    async def receive(self) -> dict[str, Any]:
        if self.reader is None:
            raise ConnectionError("client is not connected")
        line = await self.reader.readline()
        if not line:
            raise ConnectionError("server disconnected")
        return decode(line)

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

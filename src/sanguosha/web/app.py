"""FastAPI application exposing HTTP metadata and browser WebSockets."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from sanguosha.engine.errors import InvalidDecision
from sanguosha.content.characters.standard import ALL_GENERAL_POOL, ALL_SKILL_CATALOGUE
from sanguosha.model.ids import PlayerId
from sanguosha.multiplayer.protocol import (
    MAX_MESSAGE_BYTES, PROTOCOL_VERSION, ProtocolError, check_message,
    decision_from_wire, envelope,
)
from sanguosha.multiplayer.room import RoomError
from sanguosha.version import APP_VERSION, BUILD_COMMIT

from .config import WebConfig
from .rooms import ManagedRoom, RoomManager

LOG = logging.getLogger(__name__)


class HostHeaderDiagnosticMiddleware:
    """Log only proxy host headers before TrustedHost can reject HTTP."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            def value(name: bytes) -> str | None:
                raw = headers.get(name)
                return raw.decode("latin-1") if raw is not None else None
            LOG.info("http ingress host=%r x_forwarded_host=%r x_forwarded_proto=%r",
                     value(b"host"), value(b"x-forwarded-host"), value(b"x-forwarded-proto"))
        await self.app(scope, receive, send)


class BrowserConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.outgoing: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=512)
        self.managed: ManagedRoom | None = None
        self.player_id: PlayerId | None = None

    def send_nowait(self, message: dict[str, Any]) -> None:
        try:
            self.outgoing.put_nowait(message)
        except asyncio.QueueFull:
            LOG.warning("closing slow WebSocket client")
            asyncio.create_task(self.websocket.close(code=1013))

    async def sender(self) -> None:
        while True:
            await self.websocket.send_json(await self.outgoing.get())

    def detach(self) -> None:
        if self.managed is not None and self.player_id is not None:
            seat = self.managed.game.seats[self.player_id]
            if seat.connected and seat.send == self.send_nowait:
                self.managed.game.disconnect(self.player_id)
            self.managed.touch()
        self.managed = None
        self.player_id = None


async def _receive_message(websocket: WebSocket, limit: int) -> dict[str, Any]:
    raw = await websocket.receive_text()
    if len(raw.encode("utf-8")) > limit:
        raise ProtocolError("message is too large")
    try:
        message = json.loads(raw)
    except ValueError as exc:
        raise ProtocolError("malformed JSON") from exc
    check_message(message)
    return message


def create_app(config: WebConfig | None = None) -> FastAPI:
    config = config or WebConfig.from_env()
    config.validate_production()
    if config.production:
        package_logger = logging.getLogger("sanguosha")
        package_logger.setLevel(config.log_level.upper())
        if not package_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
            package_logger.addHandler(handler)
    manager = RoomManager(max_rooms=config.max_rooms, room_ttl=config.room_ttl,
                          reconnect_grace=config.reconnect_grace, ai_presentation=config.ai_presentation)
    active_connections: set[BrowserConnection] = set()
    creations: dict[str, deque[float]] = defaultdict(deque)
    shutting_down = False

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        nonlocal shutting_down
        LOG.info("web server starting version=%s commit=%s", APP_VERSION, BUILD_COMMIT)
        async def poll_rooms() -> None:
            while True:
                await asyncio.sleep(0.05)
                try:
                    manager.poll()
                except Exception:
                    LOG.exception("web room poll failed")
        task = asyncio.create_task(poll_rooms())
        try:
            yield
        finally:
            shutting_down = True
            LOG.info("web server stopping; %d in-memory rooms will end", len(manager.rooms))
            await asyncio.gather(*(connection.websocket.close(code=1001) for connection in tuple(active_connections)), return_exceptions=True)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="Sanguosha Web Edition", version=APP_VERSION, lifespan=lifespan)
    if config.production:
        app.add_middleware(TrustedHostMiddleware,
                           allowed_hosts=list(dict.fromkeys((config.domain, *config.trusted_hosts))))
        # Starlette inserts the last added middleware outermost.
        app.add_middleware(HostHeaderDiagnosticMiddleware)
    app.state.room_manager = manager
    app.state.web_config = config

    @app.websocket("/api/network/ws")
    async def network_probe(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                payload = await websocket.receive_text()
                if len(payload) > 256:
                    await websocket.close(code=1009)
                    break
                try:
                    if json.loads(payload).get("type") == "PING":
                        await websocket.send_json({"type": "PONG"})
                except (ValueError, TypeError, AttributeError):
                    pass
        except WebSocketDisconnect:
            pass

    @app.get("/health")
    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        if shutting_down:
            return JSONResponse({"status": "stopping"}, status_code=503)
        return {"status": "ok", "rooms": len(manager.rooms),
                "websockets": len(active_connections)}

    @app.get("/api/version")
    async def version() -> dict[str, Any]:
        return {"app_version": APP_VERSION, "build_commit": BUILD_COMMIT,
                "protocol_version": PROTOCOL_VERSION}

    @app.get("/api/catalog/generals")
    async def general_catalog() -> list[dict[str, Any]]:
        manifest_path = dist / "assets" / "manifest.json"
        asset_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        skills = {str(skill.id): skill for skill in ALL_SKILL_CATALOGUE}
        return [
            {
                "id": str(character.id), "name": character.name,
                "kingdom": character.kingdom.value, "max_hp": character.max_hp,
                "gender": character.gender.value,
                "pack": character.metadata.get("pack", "standard"),
                "implemented": character.metadata.get("implemented", True),
                "playable": character.metadata.get("playable", True),
                "portrait_mode": character.metadata.get("portrait_mode", "static"),
                "portrait": "/assets/" + asset_manifest.get("general." + str(character.id),
                    f"generals/{character.kingdom.value}/{character.id}.png"),
                "skills": [
                    {"id": str(skill_id), "name": skills[str(skill_id)].name,
                     "description": skills[str(skill_id)].description,
                     "type": skills[str(skill_id)].skill_type.value}
                    for skill_id in character.skill_ids
                ],
            }
            for character in ALL_GENERAL_POOL
        ]

    def authorized_test_cookie(value: str | None) -> bool:
        if not value or not config.test_access_code:
            return False
        try:
            timestamp, signature = value.split('.', 1)
            issued = int(timestamp)
        except (ValueError, AttributeError):
            return False
        if not 0 <= time.time() - issued <= 3600:
            return False
        expected = hmac.new(config.secret_key.encode(),
            f'test-room:{config.test_access_code}:{timestamp}'.encode(), hashlib.sha256).hexdigest()
        return len(signature) == 64 and signature.isascii() and hmac.compare_digest(signature, expected)

    @app.post('/api/test-mode/authorize')
    async def authorize_test_mode(request: Request):
        try:
            payload = await request.json()
            code = payload.get('code') if isinstance(payload, dict) else None
        except (ValueError, TypeError):
            code = None
        if (not config.test_access_code or not isinstance(code, str) or len(code) > 256
                or not hmac.compare_digest(code.encode('utf-8'), config.test_access_code.encode('utf-8'))):
            return JSONResponse({'error': 'invalid test access code'}, status_code=403)
        timestamp = str(int(time.time()))
        signature = hmac.new(config.secret_key.encode(),
            f'test-room:{config.test_access_code}:{timestamp}'.encode(), hashlib.sha256).hexdigest()
        response = JSONResponse({'authorized': True})
        response.set_cookie('sanguosha_test', timestamp + '.' + signature,
            max_age=3600, httponly=True, secure=config.production, samesite='strict', path='/')
        return response

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        if shutting_down:
            await websocket.close(code=1013)
            return
        if config.production and websocket.headers.get("origin") != config.public_origin:
            LOG.warning("rejected WebSocket origin")
            await websocket.close(code=1008)
            return
        if len(active_connections) >= config.max_websockets:
            await websocket.close(code=1013)
            return
        await websocket.accept()
        connection = BrowserConnection(websocket)
        active_connections.add(connection)
        sender = asyncio.create_task(connection.sender())
        try:
            hello = await _receive_message(websocket, config.message_size_limit)
            if hello["type"] != "HELLO":
                raise ProtocolError("HELLO required")
            connection.send_nowait(envelope(
                "WELCOME", app_version=APP_VERSION, build_commit=BUILD_COMMIT,
                protocol_version=PROTOCOL_VERSION,
            ))
            while True:
                message = await _receive_message(websocket, config.message_size_limit)
                kind = message["type"]
                try:
                    if kind == "CREATE_ROOM":
                        if connection.managed is not None:
                            raise RoomError("already joined")
                        if config.production:
                            address = websocket.client.host if websocket.client else "unknown"
                            recent = creations[address]
                            now = time.monotonic()
                            while recent and now - recent[0] >= 60:
                                recent.popleft()
                            if len(recent) >= config.room_creations_per_minute:
                                raise RoomError("room creation rate limit reached")
                            recent.append(now)
                        test_room = message.get('test_room') is True
                        if test_room and not authorized_test_cookie(websocket.cookies.get('sanguosha_test')):
                            raise RoomError('test authorization required')
                        review_god_lvbu = message.get('review_god_lvbu') is True and not config.production
                        managed = manager.create(seed=message.get("seed"),
                            review_god_lvbu=review_god_lvbu,
                            mode_id=message.get('mode_id', 'military-five'),
                            allow_gods=message.get('allow_gods', False),
                            test_room=test_room)
                        connection.managed = managed
                        connection.send_nowait(envelope("ROOM_CREATED", room_code=managed.code))
                        pid, token = managed.game.join(message.get("name"), connection.send_nowait)
                        connection.player_id = pid
                        LOG.info("room join code=%s", managed.code)
                        connection.send_nowait(envelope(
                            "WELCOME", room_code=managed.code, seat_id=str(pid),
                            reconnect_token=token, host_id=str(managed.game.host_id),
                            app_version=APP_VERSION, build_commit=BUILD_COMMIT,
                            protocol_version=PROTOCOL_VERSION,
                        ))
                        managed.game._send_current(pid)
                        if message.get("single_player") is True:
                            managed.game.start(pid)
                    elif kind in ("JOIN_ROOM", "RECONNECT"):
                        if connection.managed is not None:
                            raise RoomError("already joined")
                        managed = manager.get(message.get("room_code", ""))
                        connection.managed = managed
                        pid, token = managed.game.join(
                            message.get("name", "玩家"), connection.send_nowait,
                            token=message.get("token"),
                        )
                        connection.player_id = pid
                        LOG.info("room %s code=%s", "reconnect" if kind == "RECONNECT" else "join", managed.code)
                        connection.send_nowait(envelope(
                            "WELCOME", room_code=managed.code, seat_id=str(pid),
                            reconnect_token=token, host_id=str(managed.game.host_id),
                            app_version=APP_VERSION, build_commit=BUILD_COMMIT,
                            protocol_version=PROTOCOL_VERSION,
                        ))
                        managed.game._send_current(pid)
                    elif kind == "PING":
                        connection.send_nowait(envelope("PONG"))
                    elif kind == "LEAVE_ROOM":
                        LOG.info("room leave code=%s", connection.managed.code if connection.managed else "none")
                        if connection.managed is not None and connection.player_id is not None:
                            connection.managed.game.leave(connection.player_id)
                        connection.detach()
                    elif connection.managed is None or connection.player_id is None:
                        raise RoomError("join room first")
                    elif connection.managed.game.seats[connection.player_id].send != connection.send_nowait:
                        raise RoomError("seat reconnected elsewhere")
                    elif kind == "READY":
                        connection.managed.game.ready(connection.player_id, message.get("ready"))
                    elif kind == 'PRESENTATION_SPEED':
                        connection.managed.game.set_presentation_speed(connection.player_id, message.get('speed'))
                    elif kind == 'CONFIGURE_ROOM':
                        connection.managed.game.configure(connection.player_id,
                            mode_id=message.get('mode_id'), allow_gods=message.get('allow_gods'))
                    elif kind == 'KICK_PLAYER':
                        connection.managed.game.kick(connection.player_id,
                            PlayerId(message.get('seat_id', '')))
                    elif kind == "START_GAME":
                        connection.managed.game.start(connection.player_id)
                        LOG.info("game start code=%s", connection.managed.code)
                    elif kind == "SUBMIT_DECISION":
                        decision = decision_from_wire(message.get("decision"), connection.player_id)
                        connection.managed.game.submit(connection.player_id, decision)
                    elif kind == "TAKEOVER_AI":
                        connection.managed.game.takeover_ai(
                            connection.player_id, PlayerId(message.get("seat_id", "")))
                    else:
                        raise ProtocolError("unexpected client message")
                    if connection.managed is not None:
                        connection.managed.touch()
                except (ProtocolError, RoomError, InvalidDecision, ValueError) as exc:
                    LOG.info("browser request rejected: %s", exc)
                    connection.send_nowait(envelope("ERROR", message=str(exc)))
        except WebSocketDisconnect:
            pass
        except (ProtocolError, RoomError, ValueError) as exc:
            connection.send_nowait(envelope("ERROR", message=str(exc)))
            await asyncio.sleep(0)
        except Exception:
            LOG.exception("unexpected browser client error")
            connection.send_nowait(envelope("ERROR", message="server error"))
            await asyncio.sleep(0)
        finally:
            connection.detach()
            active_connections.discard(connection)
            sender.cancel()
            with suppress(asyncio.CancelledError, RuntimeError):
                await sender

    dist = Path(os.getenv("WEB_DIST_DIR", Path(__file__).resolve().parents[3] / "web" / "dist"))
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}")
        async def spa(path: str):
            candidate = dist / path
            if path and candidate.is_file() and dist in candidate.resolve().parents:
                return FileResponse(candidate)
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
    else:
        @app.get("/")
        async def development_root():
            return JSONResponse({"message": "Run the Vite development server on http://localhost:5173"})

    return app


app = create_app()



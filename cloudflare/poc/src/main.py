import json
import uuid
from urllib.parse import urlparse

from fastapi import FastAPI
from js import WebSocketPair
from workers import DurableObject, Response, WorkerEntrypoint, asgi


app = FastAPI()


@app.get("/fastapi")
async def fastapi_check():
    return {"fastapi": True}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(request.url).path
        if path == "/health":
            return Response.json({"python_worker": True})
        if path == "/fastapi":
            return await asgi.fetch(app, request, self.env)
        if path.startswith("/room/"):
            room_code = path.split("/")[2]
            return await self.env.ROOM.getByName(room_code).fetch(request)
        return await self.env.ASSETS.fetch(request)


class Room(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.instance_id = str(uuid.uuid4())
        self.sockets = {}
        for ws in self.ctx.getWebSockets():
            attachment = ws.deserializeAttachment()
            if attachment:
                self.sockets[attachment] = ws

    async def fetch(self, request):
        if request.headers.get("Upgrade") == "websocket":
            client, server = WebSocketPair.new().object_values()
            self.ctx.acceptWebSocket(server)
            server.serializeAttachment("poc-player")
            self.sockets["poc-player"] = server
            return Response(None, status=101, web_socket=client)
        old = await self.ctx.storage.get("counter") or 0
        value = old + 1
        await self.ctx.storage.put("counter", value)
        sql_result = self.ctx.storage.sql.exec("SELECT 1 AS sqlite_ok").one()
        return Response.json({"counter": value, "sqlite_ok": sql_result.sqlite_ok})

    async def webSocketMessage(self, ws, message):
        player = ws.deserializeAttachment()
        old = await self.ctx.storage.get("messages") or 0
        await self.ctx.storage.put("messages", old + 1)
        ws.send(json.dumps({"player": player, "message": message, "messages": old + 1, "instance_id": self.instance_id}))

    async def webSocketClose(self, ws, code, reason, was_clean):
        self.sockets.pop(ws.deserializeAttachment(), None)

    async def webSocketError(self, ws, error):
        self.sockets.pop(ws.deserializeAttachment(), None)

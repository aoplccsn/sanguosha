"""Smoke a deployed HTTPS site, including two independent WSS players."""
import argparse
import asyncio
import json
import urllib.request
from urllib.parse import urlparse

from websockets.asyncio.client import connect


async def receive_type(socket, wanted):
    for _ in range(20):
        message = json.loads(await asyncio.wait_for(socket.recv(), timeout=10))
        if message.get("type") == "ERROR":
            raise RuntimeError(message.get("message", "server error"))
        if message.get("type") == wanted:
            return message
    raise RuntimeError(f"No {wanted} received")


async def main(origin):
    parsed = urlparse(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        raise ValueError("Pass an HTTPS origin, for example https://game.example.com")
    for path in ("/", "/health", "/api/version"):
        with urllib.request.urlopen(origin + path, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError(f"{path}: HTTP {response.status}")
            body = response.read()
            if path == "/health" and json.loads(body)["status"] != "ok":
                raise RuntimeError("Health response is not ready")
            if path == "/api/version":
                version = json.loads(body)
                for key in ("app_version", "build_commit", "protocol_version"):
                    if not version.get(key):
                        raise RuntimeError(f"Missing version field: {key}")
                protocol = version["protocol_version"]
    uri = f"wss://{parsed.netloc}/ws"
    async with connect(uri, origin=origin, max_size=512_000) as host:
        await host.send(json.dumps({"type": "HELLO", "version": protocol}))
        await receive_type(host, "WELCOME")
        await host.send(json.dumps({"type": "CREATE_ROOM", "version": protocol, "name": "部署验收房主"}))
        code = (await receive_type(host, "ROOM_CREATED"))["room_code"]
        await receive_type(host, "WELCOME")
        async with connect(uri, origin=origin, max_size=512_000) as guest:
            await guest.send(json.dumps({"type": "HELLO", "version": protocol}))
            await receive_type(guest, "WELCOME")
            await guest.send(json.dumps({"type": "JOIN_ROOM", "version": protocol, "name": "部署验收来宾", "room_code": code}))
            joined = await receive_type(guest, "WELCOME")
            if joined["room_code"] != code:
                raise RuntimeError("Guest joined a different room")
    print(f"PASS: HTTPS, health, version, WSS create/join room {code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("origin", help="HTTPS site origin")
    args = parser.parse_args()
    asyncio.run(main(args.origin.rstrip("/")))

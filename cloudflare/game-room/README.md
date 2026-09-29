# Cloudflare GameRoom Worker

This is the production-shaped local Cloudflare Workers adapter for the existing authoritative `MultiplayerRoom` and `GameSession`. Each six-character room code maps deterministically to one SQLite-backed `GameRoomDurableObject`.

## Local preparation

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\sync_cloudflare_game_room.py
$env:CLOUDFLARE_ROOMS='1'
Push-Location web
npm run build
Pop-Location
```

Start the local runtime with the project Workers environment:

```powershell
Push-Location cloudflare\game-room
pywrangler dev --port 8793
```

In another terminal:

```powershell
node cloudflare\game-room\test_runtime.mjs
```

The runtime smoke test creates a room through the Worker, connects two hibernating WebSockets to the same Durable Object, starts the authoritative game, verifies private general drafts, reconnects a player to the same seat, restores the player projection, and checks the persisted room phase.

No Cloudflare login or public deployment is required for these checks.

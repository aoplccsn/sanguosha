# T9.2 Cloudflare capability POC

Run `npm run build` in `web/`, then from this directory run `uv run pywrangler dev --port 8790`. In another terminal set `POC_URL=http://127.0.0.1:8790` and run `node test_poc.mjs`. Use `node test_poc.mjs --wake` to wait 155 seconds and verify that a connected WebSocket survives DO hibernation and its attachment is available after reconstruction. On PowerShell, set `$env:POC_URL` instead.

The POC deliberately contains no Sanguosha game rules. It checks the platform gates before migrating `GameSession`.

On Windows on 2026-09-29, Wrangler 4.143.0 and pywrangler successfully exercised:

- Python Worker and FastAPI ASGI routes.
- Python Durable Object with `new_sqlite_classes`, storage reads/writes, and SQL execution.
- Python DO WebSocket with `ctx.acceptWebSocket`, message/close/error handlers, and serialized attachment.
- SQLite-backed storage surviving a Wrangler process restart (`counter` advanced from 2 to 4).
- One live WebSocket remaining connected after 155 seconds idle; the next message retained the attachment and changed the DO constructor instance ID.
- The existing React/Vite production `index.html` and hashed JavaScript asset through the Worker assets binding.

The official Cloudflare Vitest plugin currently fails to load this Python Worker module on this Windows setup before running any tests (`No such module ... main.py?mf_vitest_force=PythonModule`). The direct Wrangler runtime test above passes. A repeatable forced-eviction runtime test remains necessary in the production adapter test suite.

Official references: [Python Workers](https://developers.cloudflare.com/workers/languages/python/), [FastAPI](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/), [Python WebSocket hibernation example](https://developers.cloudflare.com/durable-objects/examples/websocket-hibernation-server/), [Durable Objects Free limits](https://developers.cloudflare.com/durable-objects/platform/limits/), [Static Assets](https://developers.cloudflare.com/workers/static-assets/).

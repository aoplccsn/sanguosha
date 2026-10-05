# CN deployment container PoC

This is a deployment recipe only. It does not deploy the service or change Cloudflare Workers.

## Reused service

- FastAPI app: `sanguosha.web.app:app` (`src/sanguosha/web/app.py`).
- Container command: `sh /app/start_production_web.sh`. With `PORT` set, the script runs `python -m sanguosha.web`, which starts one Uvicorn worker on `0.0.0.0:$PORT` (default 8000).
- FastAPI serves `/api/*`, `/ws`, `/health`, and `/api/health`; it also serves the Vite `web/dist` SPA and `/assets/*` on the same origin. The image sets internal `WEB_DIST_DIR=/app/web/dist` because the installed Python package lives under site-packages.
- Browser HTTP calls use relative `/api/*` URLs. `websocketUrl()` builds `ws://` or `wss://` from the page protocol and host. The existing `CLOUDFLARE_ROOMS=1` build switch and Cloudflare room routes remain separate and unchanged.
- Rooms and reconnect state live in one Python process. Run one replica for this PoC. Restarting or replacing that replica ends active rooms.

## Sealos form

| Field | Value |
| --- | --- |
| Region | China mainland region chosen for the PoC |
| Source/build | This repository root, Dockerfile at `Dockerfile` |
| Service type | Container/Web service with HTTP and WebSocket support |
| Build context | Repository root `.` |
| Start command | Image default: `sh /app/start_production_web.sh` |
| Container port | `8000` by default; if Sealos assigns another port, set `PORT` to that port |
| Public access | One HTTPS hostname routed to this single service |
| Replica count | 1 |
| Health check | TCP on container port, or HTTPS `https://<hostname>/api/health` (200 JSON with `status: ok`) |
| Persistent volume/database | None for this PoC |

Set these environment variables in Sealos, not in the repository:

| Variable | Value |
| --- | --- |
| `DOMAIN` | Exact public DNS hostname, without scheme or port |
| `PUBLIC_ORIGIN` | `https://` followed by that exact hostname |
| `SECRET_KEY` | Unique random secret of at least 32 characters |
| `PORT` | Container listening port, normally `8000`; set explicitly for the port-aware startup path |

The image already sets `APP_ENV=production` and internal `WEB_DIST_DIR=/app/web/dist`; Sealos does not need to override them. `PUBLIC_BASE_URL` belongs to the separate relay and is not used by this Web service. No frontend API or WebSocket base URL variable is needed. Set the hostname variables after obtaining a Sealos hostname and before starting the service. Production startup rejects mismatched host, Origin, or weak secrets.

## Local verification

Docker was unavailable on the development machine, so an image build/run remains unverified. The equivalent source path was checked with the project's Python environment and a fresh Vite production build served by the FastAPI app at one local origin. The focused Python test also checks the explicit dist directory that the installed package uses in the image. The container image still needs a real Docker build and smoke run before any deployment.

Local checks: 89 Python Web/multiplayer tests, TypeScript, 26 relevant Vitest tests, fresh Vite build, and the CN two-browser Playwright smoke test passed. HTTP checks returned 200 for all 76 portrait URLs, all 18 files for nine dynamic portraits, and a Slash card asset. Two older Playwright cases use outdated assumptions: one expects automatic reconnect on reload, while the current UI offers an explicit continue action; another expects T18A.3 stage copy instead of the current T18A.8 text. The CN smoke test covers the current reconnect and Slash/Dodge interaction.

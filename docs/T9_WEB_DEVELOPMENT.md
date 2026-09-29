# T9 Web Development Validation

Validation date: 2026-09-29

## Vite HMR

HMR RESULT: PASS

The Playwright test web/e2e/hmr.spec.ts started the real Vite development server, changed a harmless attribute in HomePage.tsx, observed the marker in the already open browser, and verified a window sentinel survived the update. The browser stayed open and did not perform a full reload. The source file was restored by the test.

## Development command

Run .\scripts\dev_web.ps1 from C:\Sanguosha. It starts the FastAPI backend and Vite frontend and prints both local URLs.

## Backend reload

The development backend uses Uvicorn reload. A source change causes the backend process to restart and the health endpoint remains available. The script intentionally warns that reload clears in-memory rooms; this is expected for local development and is not the production update mechanism.

## Version display

The browser fetches /api/version, shows the protocol number in the home footer, and displays a non-blocking new-version notice when the server semantic version is newer than the frontend build. During a game the notice is reduced to a small HUD label and never forces a refresh.

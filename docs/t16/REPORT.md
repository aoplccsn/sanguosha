# T16 — Production UI, Match Pacing, Skill UX & Network Accessibility

Date: 2026-10-04 (Asia/Shanghai). Baseline: `bb9abbf426bf97153aec9a2fcad3715193c91619`.

## 1–7. UI implementation and visual acceptance

Original assets retained. Lacquer/wood, double bronze borders, parchment controls and vertical Chinese general names replace the prototype treatment. Opponent portrait space is enlarged; metadata, HP, equipment, judgments and skills have reserved layout slots. Current turn, legal target, selected target, response badges and Canvas beams remain. Portrait media retain `pointer-events: none`.

Five seats use a top arc plus right seat and full-width local dock. Eight seats use three upper seats and two seats per side, with a narrower central local dock. Portraits are 104 × 176 px in five-seat panels and 90 × 151 px in eight-seat panels. Desktop board reserves 1000 px height; short windows scroll rather than squeeze seats. Narrow screens use two columns, a scrollable hand and fixed response controls. Screenshots: `five.png`, `eight.png`, `eight-mobile.png`.

The local dock groups portrait, HP, identity, skills, hand and operation controls. The decision panel sits above the dock, with final Confirm/Cancel, end phase and response actions preserved. HUD speed and quality retain accessible native selects with unified bronze styling. Central semantic events use a light ornament and short-lived presentation. Acting seats receive an action badge. Hand hover/selection moves only the image inside a fixed button hitbox.

OFFICIAL-STYLE UI / PLAYER PANEL / BOTTOM OPERATION AREA / TOP HUD / CENTRAL PRESENTATION: local implementation and visual checks PASS; aesthetic sign-off remains human review.

## 8–9. Frontend pacing

Central configuration in `web/src/presentation/pacing.ts`:

| Speed | Ordinary | Card use | Damage / skill / judgment | Turn |
| --- | ---: | ---: | ---: | ---: |
| 慢 | 1050 ms | 1450 ms | 1550 ms | 1050 ms |
| 正常 (default) | 725 ms | 1025 ms | 1100 ms | 725 ms |
| 快 | 300 ms | 475 ms | 550 ms | 300 ms |

Browser-observed card-use intervals are in `pacing-metrics.json` (approximately 1461 / 1020 / 474 ms). Intake no longer restarts the dwell timer when events arrive. Only semantic public events enter the presentation queue. Projection, WebSocket and ACK delivery are never delayed. A HUMAN PendingRequest immediately clears accumulated presentation and renders authoritative response controls/timer. Queue playback survives rolling event history. Current projection remains authoritative; playback is an event narration/VFX layer.

Added public turn, discard-count, dying, judgment-result and already-recorded skill-event facts to the existing projection allowlist. No engine sleeps or gameplay rule changes. Discard event IDs are opaque hashes so card instance IDs cannot leak through action-derived IDs. Worker engine module is synchronized with authoritative source.

AI SLOW/NORMAL/FAST / HUMAN RESPONSE NOT DELAYED: PASS in deterministic browser event sequences and unit regressions.

## 10–12. Skill information

`SkillTooltip` and `optionMetadata` resolve incarnation `general:skill`, general choices, direct skill choices and virtual/active skills from `/api/catalog/generals`, which uses `ALL_65_GENERAL_POOL` and `ALL_SKILL_CATALOGUE`. No duplicate description table was introduced. All 119 referenced skills across 65 generals have descriptions. Zuoci/Huashen rules and Xinsheng rules are unchanged.

Candidates show Chinese general/skill names. Popover shows faction, HP and full registry description. Hover and keyboard focus show it; an info button opens it on touch; Escape closes it. Detail renders in a fixed portal away from bottom confirm controls and never moves the option hitbox. Choice wire values stay unchanged and invisible to players. Skill bar supports the same detail component.

ZUOCI SKILL DESCRIPTION / SKILL TOOLTIP / PLAYER-FACING CHINESE (new UI): PASS.

## 13–19. Network findings and domain readiness

`/network-diagnostics` is linked from home and failed-connection UI. It probes `/health`, an exact static marker, `/api/network/ws`, ping/pong, RTT and 15 seconds of heartbeat continuity. Copy exports only allowlisted booleans, timing, disconnect count, browser agent and timestamp. No reconnect tokens, room data, hidden hand/identity, IP or location are collected/exported.

Cloudflare probe uses a dedicated named GameRoomDurableObject attachment. It does not load a room, join a seat, submit a decision, or create a room-index reservation. Existing room/DO routing and fast ACK path remain intact. FastAPI has the same local probe route.

Local Worker diagnostics: HTTP PASS; Asset PASS; WS handshake PASS; Pong PASS; continuity PASS; RTT approximately 2 ms; disconnect count 0. Evidence: `network-local-8793.txt` and `network.png`. These are LOCAL results only.

No runtime hardcoded workers.dev hostname found in `web/src` or Vite config. HTTP/assets use relative URLs. `websocketUrl` derives `https → wss`, `http → ws`, host/port from current page; room routes preserve the same origin. ASSETS binding and both existing DO bindings remain configured in `wrangler.jsonc`. Application code is ready for a custom domain without changing HTTP, assets or WS URLs. The custom domain has NOT been bound.

Transport improvements: stalled handshake gets an 8-second timeout; unanswered heartbeat closes the stale socket; after six failed reconnect attempts the UI stops looping and offers explicit retry and diagnostics. Local code has no evidence explaining regional/VPN-dependent initial-entry failure. Before this patch, a stuck handshake and unbounded reconnect UI were identifiable application UX weaknesses; fixing those does not establish regional accessibility.

If HTML cannot load, no client diagnostic can run: distinguish DNS/TLS/initial Worker reachability externally. If HTML loads, Asset/HTTP/WS/Pong/continuity distinguish the failing application layer. Worker timeouts, deployed DO faults and regional filtering need deployed evidence and affected-user diagnostic reports. A custom domain is a sensible next comparative test but is not guaranteed to resolve regional restrictions.

NETWORK DIAGNOSTICS / CUSTOM DOMAIN READY: local PASS.
HARDCODED WORKERS.DEV (runtime): NONE.
MAINLAND NETWORK ACCESS / MAINLAND / NON-VPN CONNECTIVITY: UNVERIFIED.
Deployment status was not inferred. No public deployment, DNS/account edits, domain purchase or workers.dev removal performed.

## 20–23. Validation

- Vitest: 67 passed, 14 files. Covers existing room UI/decisions, same-origin WS, three-tier pacing, incoming-event timer stability, human flush, registry lookup, hover/focus/info interaction, sanitized diagnostics and reconnect limit/timeout.
- Playwright: 19 production room/ACK/reconnect tests passed against local Worker; 5 T16/dynamic interaction tests passed on Vite; standalone 15-second Worker diagnostics test passed. T15 0/1/3/5 video first target clicks and final card/response confirms remain passing. Five/eight/mobile screenshots were inspected and overlap corrections rechecked in Chromium.
- Actual local Worker runtime smoke passed: catalog, room admission, private drafts, 60-second human timer, ACK ordering, SQLite room state and same-seat reconnect. Send-to-ACK approximately 10–11 ms; ACK-to-projection approximately 34 ms in this local run.
- Python full suite: 754 passed, 1 failed. Remaining failure is existing T10 V3 portrait hash expectation for `wind_zhang_jiao`: expected `74d220…`, current T15 asset `8ef770…`. Artwork and old readiness file are unchanged by T16; do not revert T15 to satisfy the obsolete hash test. New semantic-event privacy/worker-isolation tests and all affected full-game/ACK regressions pass.
- TypeScript and production Vite build: PASS using existing `.venv` Python/Pillow and `CLOUDFLARE_ROOMS=1`. No new dependency installation.
- `git diff --check`: PASS.

## 24–25. Checkpoint and worktree

Local checkpoint commit is identified in the final handoff. Only T16 implementation, tests and evidence are included. Original six untracked `docs/t11/god_art` directories remain untouched and excluded. Await human visual/gameplay review; do not deploy automatically.

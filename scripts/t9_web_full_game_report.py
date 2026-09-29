"""Reproduce the 20 FastAPI WebSocket smoke matches and write their summary."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_t9_web_validation import play_web_match, start_server  # noqa: E402


async def main() -> None:
    app, server, task, url = await start_server()
    rows = []
    try:
        for humans in range(1, 6):
            for seed in range(4):
                code, seen = await play_web_match(url, humans, seed)
                room = app.state.room_manager.rooms[code].game
                session = room.session
                assert session is not None and session.state.victory is not None
                generals = ", ".join(f"{pid}:{general}" for pid, general in room.pregame.generals.items())
                rows.append((humans, seed, session.state.victory.label, session.state.turn_number, generals, sum(map(len, seen))))
    finally:
        server.should_exit = True
        await task
    lines = [
        "# T9 Web Full-Game Smoke",
        "",
        "Run date: 2026-09-29",
        "",
        "Each match used real FastAPI /ws clients, server projections, pending requests and JSON decisions.",
        "The automated test also checked winner, FINISHED phase, empty request and resolution stack, processing-zone cleanup and card uniqueness.",
        "",
        "| Human WebSocket clients | Seed | Winner | Turns | General assignment | Human requests |",
        "| ---: | ---: | --- | ---: | --- | ---: |",
    ]
    lines.extend(f"| {humans} | {seed} | {winner} | {turns} | {generals} | {requests} |"
                 for humans, seed, winner, turns, generals, requests in rows)
    lines.extend(["", f"Total: {len(rows)} completed games.", ""])
    target = ROOT / "docs" / "T9_WEB_FULL_GAMES.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    asyncio.run(main())

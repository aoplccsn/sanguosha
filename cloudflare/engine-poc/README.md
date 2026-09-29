# Engine-only Cloudflare verification

This fixture intentionally has no Static Assets binding. It bundles the existing engine modules plus the generated `cloudflare_deck_data.py` fallback and exposes `/engine/military`.

Verified with `uv run pywrangler dev --port 8792` and Wrangler 4.143.1:

`GET /engine/military` -> HTTP 200 `{"cards":160,"players":5,"ruleset":"classic-military"}`.

This confirms full military `GameSession.new_game(seed=6, military=True, five_generals=True)` initializes in the real local Python Workers/Pyodide runtime. It does not claim GameRoom Durable Object integration.

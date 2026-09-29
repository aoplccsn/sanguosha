# T9 Web Privacy Validation

Validation date: 2026-09-29

The automated audit uses real FastAPI WebSocket connections and inspects the raw JSON messages delivered to each client. It does not rely only on rendered DOM state.

## Hand privacy — PASS

- Opponent projections contain hand counts only and do not contain an opponent hand collection.
- The audit reads the authoritative server state, obtains the opponent's private physical card IDs, and confirms those IDs do not occur in the other client's raw payload transcript.
- Card details for the viewing player's own hand remain available in that player's private projection.

## Identity privacy — PASS

- The lord remains public.
- A living non-lord opponent is represented as 未知 in another player's projection.
- The audit compares the projected label with the authoritative identity held by the server.

## General candidate privacy — PASS

- Each DRAFT_REQUEST is sent only to its owning WebSocket connection.
- One player's draft request ID and private candidate message are absent from the other player's transcript.

## Deck privacy — PASS

- Client payloads expose aggregate deck count only.
- No deck order or draw-pile card list is serialized to browser clients.

## Private request privacy — PASS

- PENDING_REQUEST is delivered only to the request owner.
- Other clients receive viewer-safe projections and allowlisted public events without the owner's legal candidate lists.

## Automated coverage

- tests/test_t9_web_validation.py::test_fastapi_websocket_privacy_payload
- tests/test_t9_web_validation.py::test_fastapi_websocket_full_game_smoke
- 1H through 5H, four deterministic seeds each, for 20 WebSocket full games.

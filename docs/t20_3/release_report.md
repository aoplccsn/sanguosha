# T20.3

The local HUD allocates separate grid cells to skills, equipment/judgments, hand cards, operations and portrait. Hand overlap is calculated from container width and card count. The portrait uses the existing shared dynamic/static viewport and remains larger than the previous local panel. Equipment material buttons use the same selected card IDs as the hand, with pressed state, gold borders and cancellation.

Physical Iron Chain now exposes 使用 / 重铸 / 取消. Use requires one or two projected legal targets; recast explicitly submits an empty target list to the existing authoritative CardMoveService/draw flow. The baseline minimal three-survivor loyalist scenario already passes rules and projection; no identity filter bug was reproduced and no engine rules were changed. Real browser/server decisions cover self plus rebel targets and zero-target recast.

Private identity guesses live only in localStorage, scoped to room/local/target. Unknown other roles offer 忠？ / 反？ / 内？ / clear. Public identities and deaths suppress the note. No server, AI or rule state is changed.

Game and draft screens use an orientation prompt in narrow portrait view and the same desktop table DOM in landscape. CSS uses dynamic viewport height and safe-area insets. User start gestures attempt fullscreen/orientation lock with failure swallowed. Rotation leaves the room, socket, selection and portrait instance intact. The existing music controls are repositioned away from skills; audio code and resources are unchanged.

Validation: targeted Python 14, Vitest 134, Playwright 17, TypeScript, fresh Vite build, production HTTP assets (108 portraits / 44 cards). Reviewed rendered desktop, landscape 5/8-player large-hand/response, draft, dynamic and fallback screenshots. Full pytest was not run; shared engine rules were not modified.

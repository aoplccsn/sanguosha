# T21.3 final frontend polish and production readiness

Accepted baseline: 39baa6a, branch t21-frontend-refactor.

- Preserve god Zhuge Liang home hero/theme, hall_v1.webp, battle_v2.webp, seat maps and local HUD.
- Home: quieter nickname/mode fields, stronger nickname hierarchy, subdued debug/version entries and a muted cinnabar/plum primary button.
- Phone landscape: contain the prompt in the hand column, tighten prompt/button type and seat labels. 844x390 and 915x412 reviewed; portrait remains playable.
- God portraits: retain default 1.32 scale. Only god Gan Ning and god Zhou Yu use top transform origin to retain their head ornaments. God Zhuge Liang and god Lu Bu remain unchanged.
- Build: npm sync launcher prefers project .venv, supports explicit PYTHON for worktrees/CI and gives an actionable Pillow dependency error. Uses existing .[web-build] extra; no global Pillow or PATH workaround required. Docker keeps its existing isolated Pillow asset stage.
- Playwright environment: fix T21 default interpreter escaping and explicitly use the current worktree source for T20.3, avoiding shared editable-install imports from the AI worktree.

Validation:

- TypeScript passed.
- Vitest: 20 files / 133 tests passed.
- Full npm production build including asset sync passed.
- T21 Playwright: 19 passed.
- T20.3 Playwright: 17 passed, explicitly using T21 source.
- Existing production/server Python smoke: 46 passed.
- Production dist browser smoke: 5/8 seats, two human browsers, create/join/draft, refresh reconnect, animated home and static fallback passed; no asset 404, console or runtime errors.
- All production manifest resources and registered dynamic media verified over HTTP (see production-assets.log).
- Screenshots reviewed: 1440x900 home, 5/8 desktop tables, local/top/side god portraits, 844x390 and 915x412 landscape.

The older cn-deployment combat smoke assumes a unique initial Slash and the host acting first; current draft can produce multiple disabled Slash cards. Its create/join/draft/reconnect steps passed, but the obsolete combat selector failed. The focused production smoke above validates this release scope without changing engine, rules or AI.

Production integration target: t19-overpowered-generals (existing GHCR workflow). Its original C:/Sanguosha worktree contains unfinished AI edits and is left untouched; integration uses an independent clean checkout and fast-forward only.

Deployment state is recorded separately after push/image verification. Current public health is 200 but version reports development; this does not count as T21.3 online acceptance. Sealos browser control timed out; no local kubeconfig is available. Keep existing sanguosha-cn / Beijing / 1 replica / 8000 / domain / environment variables.

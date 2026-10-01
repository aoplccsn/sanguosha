# T11 Canvas VFX performance smoke

Measured in headless Chromium on 2026-10-01, medium quality, synthetic two-player Canvas fixture. Each scenario ran for 1.2 seconds. Values are requestAnimationFrame cadence, not GPU paint or a full match trace. Raw measurements: [performance_final.json](performance_final.json).

| Size | Idle | Beam | Slash | Dodge | Damage | Simultaneous |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1366×768 | 60.0 | 60.0 | 60.0 | 60.0 | 60.0 | 60.0 |
| 1600×900 | 60.0 | 60.0 | 60.0 | 60.0 | 60.0 | 60.0 |
| 1920×1080 | 60.0 | 59.2 | 60.0 | 60.0 | 60.0 | 60.0 |

All p95 frame intervals were 16.7–16.8 ms; the browser reported zero long tasks in these samples. The pre-change FPS baseline was not captured, so this does not prove a numeric improvement. Real device profiling remains necessary, especially for layered god portraits and future cinematic effects.

The previous full-game E2E script is brittle after the T10 roster expansion: its seed no longer guarantees Sun Quan/Zhang Liao and its fixed opening hand sequence. A separate T11 browser smoke test validates the Canvas layer, resize behavior and persisted quality setting in a real game.

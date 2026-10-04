# T15.1 Dynamic Portrait Performance Hardening

Checkpoint: T15.1 (working tree from `7cc59961082e8f8432e76b9330262703e77fcb15`)

## Result

9/9 dynamic portraits remain integrated. Runtime detail videos are 720x1280, H.264/yuv420p, 24 fps, no audio, faststart. PlayerPanel uses a registered 180x320 panel variant; GeneralDetail keeps the full detail asset. Original masters were hash-checked unchanged.

The performance result is **PARTIAL** for 3/5 concurrent videos. Optimizing displayed pixels reduced transfer and compositor upload work, but Chromium still schedules the page near 30 fps with three or five simultaneously playing native videos.

## Asset evidence

- Previous 9 full runtimes: 53,270,072 bytes.
- New 9 detail runtimes: 38,283,176 bytes (28.1% smaller).
- New 9 panel runtimes: 6,691,987 bytes; detail + panel total 44,975,163 bytes.
- Production `web/dist`: 56,780,226 bytes (includes both variants and optimized raster assets).
- All nine detail SSIM values are approximately 0.9903–0.9919; panel SSIM values are approximately 0.9854–0.9904. Visual contact sheets cover first and mid-sequence frames, face, hair, weapon edges, armor texture, gradients, and smoke/background transitions; no visible blocking or face collapse was observed.

## Measured performance

| Dynamic videos | UI FPS | Long tasks | Software frame upload |
|---:|---:|---:|---:|
| 0 | 60.17 | 0 | — |
| 1 | 60.07 | 0 | 22.06 ms |
| 3 | 31.78 | 0 | 62.69 ms |
| 5 | 31.82 | 0 | 92.77 ms |

The native-video isolation test, with no React, game CSS, or VFX, measured 60.2 / 60.1 / 30.6 / 30.0 fps for 0/1/3/5 videos. Trace events show `VideoResourceUpdater::CreateForSoftwareFrame` and `VideoFrameSubmitter::SubmitFrame` rising with video count, while JS/script/layout work stayed low. This identifies the browser video upload/compositor scheduling path as the evidence-backed bottleneck; exact GPU-driver versus decoder attribution is not available from these metrics.

Ordinary projection update kept video nodes stable, with zero src/poster/child mutations and no repeated play calls. First target click latency was 3.1–9.8 ms across 0/1/3/5 videos. Card and response actions still require one final confirmation. Home and character selection video requests remain zero.

## Lifecycle and regressions

Automated hidden/resume behavior passed: all mounted videos pause, currentTime remains stable during a 15-second hidden hold, and only videos still eligible after viewport restoration resume. Native desktop tab/window visibility is not exposed reliably by this Edge automation environment; **MANUAL DESKTOP ACCEPTANCE REQUIRED** for a real minimize/tab-switch check. Steps: open a five-player game, verify five videos playing, switch to another tab or minimize for 15–20 seconds, restore, and confirm only mounted/in-viewport/high-quality portraits resume without restart or console errors.

Passed: Vitest 59, asset pipeline pytest 6, T11 VFX pytest 23, TypeScript/Vite production build, and 16 Chromium Playwright tests covering nine MP4s, first click, detail fallback, VFX compatibility, hidden/resume, sizing at DPR 1/2, interaction at 0/1/3/5, native isolation, and no preload on home/selection.

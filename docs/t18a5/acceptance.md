# T18A.5 final acceptance — COMPLETE

Starting checkpoint: 4b6cd08 (preserved). Baseline: d951fb8.
No public deployment, no T17C, no AI strategy expansion, no master/media changes.

## Six originally reported failures

Exact IDs:
- tests/test_t5_match.py::test_ai_response_play_discard_and_dying_decisions_are_legal
- tests/test_t85_relay.py::test_relay_full_game_smoke[2-4]
- tests/test_t8_multiplayer.py::test_20_full_game_smoke[2-4]
- tests/test_t8_multiplayer.py::test_tcp_full_game_smoke[2-4]
- tests/test_t9_2_cloudflare_game_room.py::test_worker_engine_bundle_matches_authoritative_source
- tests/test_t9_web_validation.py::test_fastapi_websocket_full_game_smoke[2-4]

Isolated d951fb8, explicit PYTHONPATH and checked imported module path: 6 passed (baseline-six.txt).
Isolated unmodified 4b6cd08: 4 failed, 2 passed (partial-six-tracebacks.txt contains full tracebacks).
The response legality and Worker mirror tests already passed at 4b6cd08. The four multiplayer seed2/humans4 cases all produce:
`ResolutionError: duplicate or empty action id: 'frame-867-play-0:use:effect:target:1:damage:kuanggu:0'`.

Path: room.submit / AI progression → engine.submit_decision → run_until_blocked → MilitaryDamageHandler step8 → HpRecoverAction → engine._new_frame.
Nominal action.amount=1, actual frame.local['amount']=2 after amplification. Old index action.amount-remaining computes 0 twice. New index actual_amount-remaining yields 0 and 1. AI changes expose this existing arithmetic defect on a new deterministic path; relative to d951fb8 this is a T18A.5 regression, not an excused pre-existing failing test. No duplicate AI submit, thinking reentry or mirror divergence caused it. Minimal one-expression fix mirrored to Worker; no ResolutionStack/Action refactor.

40-game acceptance additionally exposed self-damage Fankui moving a hand card to the same hand. Only identical source/destination movement is skipped; self equipment can still enter hand. Two targeted regression tests cover both cases.

## Final checks

- Pillow OK using C:/Sanguosha/.venv/Scripts first on PATH.
- full pytest: 1059 passed, 0 failed, 90.29 seconds (pytest-final.txt).
- Military Five seeds0..19 and Military Eight seeds0..19, current 76-general pool, current AI, actual room presentation scheduling with virtual clock: 40/40 finished; illegal actions0, duplicate requests0, stalls0, exceptions0. Separate snapshot/reentry test PASS (ai-40-games.txt:41 passed).
- TypeScript npx tsc --noEmit and tsc -b PASS.
- fresh Vite7.3.6 PASS, 55 modules, 785ms; newly generated index-BQ2pF4md.js. Production asset sync ran after Pillow verification; no old dist deployment.
- Vitest73 passed in14 files (vitest-final.txt).
- installed Edge Playwright10 passed (playwright-final.txt): real local Slash/Dodge multiplayer, default god draft, all9 MP4/decode/detail, fallback, quality, offscreen/hidden pause/resume, native loop/performance, thinking/action/human priority. Additional new screenshots/fallback actual image-load checks3 passed (portrait-thinking-final.txt).

## Behavior spot check

Four fixed games: both modes seed0 and19 (ai-behavior-sample.json). 141 multi-target selections; generic target prompts never chose a negative-relation target while positive candidates existed;19 selected 1HP targets. No sampled end-play choice while a usable physical Slash option remained. 15 lowHP card selections:0 Peaches selected;2 Dodge selections occurred when required to give multiple cards, not blanket avoidance of costs. Five seed19:1HP XiahouYuan discarded ThunderSlash and kept Dodge. ShenSu A/B accepted/refused with hand/HP context; Eight seed19 refused A at2HP and accepted at3HP. GodGuanYu Five seed0 selected p5 with HP2/score86 over HP3-4/score83 and spared the publicly known lord. No clear purposeless skill use in these samples. Hidden identity allies cannot all be known; this small audit does not prove expert tactics or perfect kills.

## Thinking actual experience

Real local single-player seed3: human completes play+discard → GuoJia frame highlights → GuoJia thinking → GuoJia uses Slash on LvBu → action banner and actor/target distinction. real-game-thinking.png / real-game.txt.
Normal durations: simple1.5s, ordinary2.4s, complex3.6s. Browser ordinary measured2403.7ms; human prompt23ms (thinking-timing.json). Controlled visible CaoCao→LiuBei sequence includes exact names/action, one thinker, gold actor/cyan target, clearing and immediate human response. Actual pending AI decision now waits using existing room.poll/Worker alarm. Snapshot stores the waiting request and deadline, ensuring exactly one submit after restore. Human requests have no presentation delay and can retain a concurrent fresh action banner. No new protocol envelope or blocking sleeps.

## Nine-person visual audit

Actual native videos,360×640 PlayerPanel screenshots and static fallback compared individually; existing actual table and all9 detail playback verified. Files `{character}-comparison.png` and `{character}-detail.png`.

The `{character}-dynamic.png` capture now pauses the panel video on its first painted frame. The fallback is only on screen before playback starts, so the static/dynamic handoff can only be judged against that frame; the ten 10s masters are camera moves, and a live mid-loop capture is not a comparable state. Only the audit screenshot timing changed — no video, static fallback of the other eight, roster, CSS or mask was touched.

| General | Background/person/weapon and crop | Edges / readability / fallback |
|---|---|---|
| 神吕布 | Red moon, full figure, halberd visible; source framing retained | No abnormal halo/black edge; armor clear; slight cloak movement |
| 神赵云 | Clouds/dragon, airborne figure, long spear visible | No abnormal edge; face/armor clear; fallback equals the video's first painted frame |
| 神周瑜 | Burning city, figure, guqin continuous; source edge framing retained | No cutout halo; hands/instrument clear; subtle sleeve movement |
| 神诸葛亮 | Star chart, robe, feather fan continuous | No black contour; fan and face clear; minor ribbon/light shift |
| 神曹操 | Mountains/tower, standing figure, sword retained | No halo; face/armor clear; mild cloak variation |
| 神司马懿 | Tower, figure, armillary instrument continuous | No black outline; face/hands clear; subtle ambient movement |
| 神关羽 | Dragon/city, figure, crescent blade continuous | No halo; face/beard/weapon clear; mild cloth movement |
| 神吕蒙 | Harbor, figure, sword/scrolls continuous | No abnormal crop/outline; face/weapon clear; slight scroll motion |
| 张角 | Ritual circle, figure, staff/talismans retained | No black contour; face/staff clear; minor talisman/glow shift |

The original illustration may intentionally extend beyond its frame; audit means no new CSS/mask loss, not reconstructing unseen source artwork. Table thumbnails retain cover framing. No CSS/material edit was required. Every dynamic/static pair now measures at or above the matched-pair range of the other eight (神赵云 0.991).

### 神赵云 fallback and handoff

The fallback is the first frame of the registered master `dynamic_portrait_sources/god_zhaoyun_idle.mp4`, which is the video's starting state; no second poster system was introduced.

- Decoded first frame of the master and the shipped runtime `assets/generals/qun/mountain_god_zhaoyun.png` are pixel-identical (SSIM 1.000000, inf).
- Runtime MP4 `assets/portraits/idle/mountain_god_zhaoyun.mp4` is a re-encode of the same master; its first frame is 0.994 against the fallback.
- Live headless Edge, same DynamicPortrait markup and CSS: the video is painted at `currentTime = 0.000345s`; the panel before the video mounts and the panel at that instant are 0.971 identical, i.e. no visible pose jump.
- The same panel 2.8s into the 10s loop measures 0.474 against the fallback. The master is a camera push-in (the other eight are near-static), which is why a live mid-loop capture previously looked like a pose difference. 神赵云 now captures at the handoff frame as well.

Evidence: `mountain_god_zhaoyun-handoff.png` (static fallback | first visible video frame at 0.0003s | 2.8s reference) and `mountain_god_zhaoyun-comparison.png`.

## Remaining issues

None. T18A.5 is COMPLETE.

Design notes, not defects: the fixed normal server wait is shared by local/Worker, and the speed selector changes client playback dwell, not the authoritative wait. No public rollout occurred.

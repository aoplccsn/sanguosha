# T18A.11 Judgment / delayed trick system audit

2026-10-07. Entry checkpoints: code 8d449b4 / report 877815a. Code checkpoints: b9558ef (shared fixes) and 07d6bcb (transfer reconnect evidence). This is a partial system audit, not release candidate approval.

## Scope and outcome

The matrix dependency scan selected **28 BLOCKED rows / 27 unique skills**, including direct judgment consumers/retrial skills and explicitly marked indirect phase, draw-top, field and response dependencies. This broad dependency inventory does not assert that all 27 are judgment skills, or that shared regression proves every clause of every skill. See judgment_scope.json for individual exit status and remaining work.

**5 real baseline shared product roots repaired (R49-R53); 1 defensive stale-action contract (H02), counted separately.** One row closed FIXED: Hongyan. Newly closed PASS: 0. Matrix now **168 BLOCKED / 20 FIXED / 4 PASS**, 192 rows, 189 unique registered skills, 103 generals. Cumulative baseline product roots: **55**, from previous 50. Already-fixed mechanics are evidence, not additional bugs.

## Locked rule sources

Project authority remains docs/t17/final_version_lock.md, docs/t17/version_matrix.md and the accepted classic character catalogue. Historical community engine evidence is pinned to Mogara/QSanguosha-v2 revision e8768851bd8054db9fd1b63cd6f1feca813590d7; it is an independently pinned semantic reference, not a publisher ruling. judgment_source_notes.md records the previous retrial check; judgment_system_sources.json stores URLs, SHA256 and relevant excerpts for this batch.

- wind.cpp Hongyan: contextual spade-to-heart filter. Do not import later hand-only/draw variants. Physical card identity/rank/name remains unchanged.
- mountain.cpp Tuntian: non-heart successful final judgment enters field if still available in the judgment processing area; it must not first enter ordinary discard and trigger Luoying.
- standard-generals.cpp Tiandu: optional FinishJudge acquisition. Declining does not cancel an independent successful-judgment destination.
- thicket.cpp Songwei: FinishJudge skill, Wei judged player and final black face; optional draw for an effective other lord-skill holder. The FinishJudge window precedes default cleanup.
- standard.cpp delayed tricks and room.cpp judge/retrial: final card semantics; reversed placed delayed order, retrial seat order/exchange, legal lightning transfer. Classic Guicai is hand-only (NosGuicai reference in prior source notes); do not use modern equipment Guicai.

## Root ledger and minimal reproductions

| ID | Classification | Before | Shared correction | Evidence |
| --- | --- | --- | --- | --- |
| R49 | Real product bug | Successful Tuntian club judgment discarded, opened Luoying, then parent tried to reclaim it | JudgmentAction supports inverted complete pattern and independent success_destination; route PROCESSING directly to field, preserve Tiandu decline fallback | judgment_system_reproduction.log; successful field/no false discard or Luoying; heart failure; existing field/movement tests |
| R50 | Real product bug | Hongyan result was heart but public card showed physical spade; Guidao AI preferences evaluated material for actor rather than judged player | Reveal/retrial/final facts include judged player and effective suit/color; freeze final face before disposition; public cards and AI preference share judged-player context; preserve physical card | judgment_system_reproduction.log; judgment_ai_context_reproduction.log; final retrial/restore and four suits/three owned areas/disable |
| R51 | Real product presentation gap | No explicit Chinese delayed consequence; public-card UI overwrote match result; judgment/retrial AI steps lacked dedicated dwell | Public delayed_result fact describes skip/safe/hit/transfer/no-target/nullified; Web renders final result and restored history; scoped essential queue and room dwell; desktop reveal/retrial/final effective face plus next-AI-step 2500ms dwell | Three delayed outcomes failed before event existed; GamePage/pacing regression; desktop event-consumer and scheduling regression |
| R52 | Real product reconnect gap | Refresh during first retrial lost public revealed judgment; replaced/final and delayed consequences absent from reconnect history | Projection public history includes initial/replaced/final judgment and delayed outcome, with frozen effective faces | judgment_restore_reproduction.log; initial retrial restore, changed final card waiting Tiandu, transfer waiting FinishJudge then refresh |
| R53 | Real product bug | Default judgment discard opened Luoying request before Songwei FinishJudge | Shared judgment finish offers Songwei before card disposition; saved destination survives Songwei child request | judgment_finish_order_reproduction.log; restore while card still processing, decline Songwei then Luoying |
| H02 | Defensive contract; not counted as a proven reachable baseline defect | Directly constructed stale ResolveDelayed for dead target or relocated card could create ordinary counter/judgment | Reject stale entry before window; preserve cleanup after resolution has already started, no effect/transfer for dead recipient | judgment_restore_reproduction.log constructs invalid action; no naturally reachable gameplay path proved |

The initial public reproduction has 5 failures (R49/R50 and 3 delayed outcomes under one R51). Restore reproduction has 3 failures (2 constructed stale-action H02 cases and one R52). The AI context and finish-order logs each have one failure. Case counts are not root counts.

## Classification of non-product findings

- **Already implemented correctly:** final pattern uses final physical card rank and contextual suit/color; classic Guicai hand and Guidao black hand/equipment; Guidao returns old card to actor; multiple actors have separate optional retrial windows; active/inactive current seat ordering; limitations on retrial hand materials; Tiandu decline with independent gain_on_match; delayed virtual definition, same-name transfer exclusion, Weimu and processing-card retention through lightning damage. These were previously repaired/tested; not recounted here.
- **Version differences:** classic hand-only Guicai differs from a newer equipment-capable implementation; project Hongyan is the classic contextual spade-to-heart modifier. These are lock choices, not fresh bugs. Old incorrect Guidao discard expectations were corrected in the earlier audit and are not counted again.
- **Test issues:** four new equipment-face cases omitted mandatory EquipmentSlot.WEAPON / registered equipment definition; transfer-restore fixture initially failed to pass legitimate earlier nullification windows. See judgment_fixture_notes.md. No scenario was deleted.
- **Development regression:** the first H02 guard also returned early after lethal nonterminal lightning, leaving its delayed card in PROCESSING. judgment_development_guard.log preserves failure; corrected guard permits cleanup while preventing a new effect/transfer. New test proves death without victory and empty processing. This was introduced and repaired during this batch, not a baseline root.

## Public lifecycle / delayed boundary evidence

Creation records before_judgment, shared CardMove reveals one draw card into PROCESSING, and public initial face is available while retrial is pending. Actor windows can decline; accepted material movement preserves one authoritative zone. Final result freezes judged-player effective suit/color and uses the final card rank. Physical card definition/name is preserved (no virtual judgment card is fabricated); delayed virtual definition describes the delayed effect, not the judgment card. Destination is resolved by shared finish, with independent success destination and optional acquisition.

Indulgence heart and Supply Shortage club success do not set skip marks; failures set skip_play/skip_draw and emit explicit Chinese consequence. Lightning spade rank 2-9 hits for 3 thunder with no source, other ranks/miss transfer through legal recipients; no-next target discards. Judgment phase resolves last-placed delayed first. Existing effective-duplicate and Weimu transfer checks are in test_t18a11_judgment.py. This batch does not certify every placement/TargetConfirming combination: delayed consumer skills retain BLOCKED where those full clauses are missing.

Dead/moved targets are rejected at stale entry. Already-started dead-recipient resolution cleans its processing delayed card without a new effect/transfer. Lethal lightning cleanup is tested with game still ongoing. FINISHED engine gate rejects a new delayed action; existing terminal gate is reused, not expanded into another damage audit.

## Reconnect and presentation

- Initial card revealed, first retrial pending: restore keeps request, processing card and public face.
- Accepted retrial, final card before cleanup (Tiandu request): restore keeps replacement, final judged-player context and destination.
- Lightning waiting in processing during FinishJudge: original and restored sessions decline the same request, transfer the same physical instance to p3, and expose the same delayed-result target in projection history. There is no separate fabricated "transfer choice" request.
- Web refresh with no live events still displays delayed consequence from projection history.
- Room AI accepted decision creates dedicated judgment dwell; Web essential event pacing and human-request identity are preserved. Desktop event consumer includes reveal/replacement/final effective face and delays the next AI step for 2500ms in ordinary speed. Fast/test mode retains existing explicit bypass.

These are deterministic/scoped presentation and restore tests, not fresh-browser human visual approval or final PySide smoke. No claim of final visual gate completion is made.

## Remaining skill closures

Hongyan FIXED is justified by pinned source, contextual suit service, existing owned-hand projection/judgment/Tianxiang and restriction tests, four physical suits in hand/equipment/judgment, explicit other-player context, disabled skill, unchanged physical definition/rank, snapshot restoration, public final face and AI preference context. This closes its locked modifier contract; it does not claim unrelated Tianxiang or Guidao complete.

Same-owner multiple retrial skills are still hard ordered rather than independently verified for player-selected order. Same-owner multiple FinishJudge skills (Tiandu/Tuntian/Luoshen/Songwei) are not completely audited. R53 fixes Songwei before default cleanup but does not establish every pairwise skill ordering. Therefore Guicai, Guidao, Tiandu, Tuntian, Luoshen, Songwei and Jilue remain BLOCKED. Other consumers and indirect dependencies retain precise missing clauses below.

| General | Skill | Exit | Evidence limit / remaining work |
| --- | --- | --- | --- |
| simayi | guicai | BLOCKED | Same-owner multiple retrial skill choice order remains unverified. |
| xiahou_dun | ganglie | BLOCKED | Judgment dependency checked; full damage trigger, cost and death boundaries remain unverified. |
| guojia | tiandu | BLOCKED | Same-owner FinishJudge ordering with Tuntian/Songwei/Luoshen remains unverified. |
| zhenji | luoshen | BLOCKED | Repeated Start/FinishJudge ordering with Tiandu remains unverified. |
| zhugeliang | guanxing | BLOCKED | Indirect draw-top dependency only; full reorder/phase skill audit outstanding. |
| machao | tieqi | BLOCKED | Shared judgment dependency checked; target-confirmation and response restriction closure outstanding. |
| wind_xiahou_yuan | shensu | BLOCKED | Indirect judgment-phase skip dependency; complete phase/target/cost audit outstanding. |
| wind_xiao_qiao | hongyan | FIXED | Closed contextual suit and public judgment semantics |
| wind_zhang_jiao | leiji | BLOCKED | Final suit/rank dependency checked; full response timing and damage combinations remain unverified. |
| wind_zhang_jiao | guidao | BLOCKED | Same-owner multiple retrial skill choice order remains unverified. |
| wind_zhang_jiao | huangtian | BLOCKED | Indirect supplied-response dependency; full lord donation lifecycle outside this batch. |
| wind_god_guanyu | wuhun | BLOCKED | Shared judgment dependency checked; death-skill targeting and terminal exception closure outstanding. |
| fire_wolong | bazhen | BLOCKED | Shared judgment evidence does not close virtual response/quota/armor suppression combinations. |
| fire_yan_liang_wen_chou | shuangxiong | BLOCKED | Judgment dependency checked; phase replacement and Duel ViewAs closure remain outstanding. |
| forest_caopi | songwei | BLOCKED | FinishJudge now precedes default cleanup, but same-owner ordering with Tiandu remains unverified. |
| forest_xuhuang | duanliang | BLOCKED | Supply Shortage shared resolution checked; complete ViewAs material, range and placement audit outstanding. |
| forest_dong_zhuo | baonue | BLOCKED | Shared black/spade judgment evidence does not close all lord recovery and damage timing boundaries. |
| mountain_zhang_he | qiaobian | BLOCKED | Delayed-card relocation dependency only; full phase replacement and moving-target legality audit outstanding. |
| mountain_deng_ai | tuntian | BLOCKED | Same-owner FinishJudge priority/choice with Tiandu remains unverified; field distance is outside this batch. |
| mountain_deng_ai | zaoxian | BLOCKED | Field-count dependency only; awakening qualification/lifetime audit outstanding. |
| mountain_jiang_wei | guanxing | BLOCKED | Indirect draw-top dependency only; full reorder/phase skill audit outstanding. |
| mountain_zhang_zhaozhang | guzheng | BLOCKED | Final judgment SYSTEM move must not be conflated with discard-phase cost; full discard-phase audit outstanding. |
| mountain_cai_wenji | beige | BLOCKED | Shared final suit semantics checked; discard cost, four effects and damage timing require full source closure. |
| mountain_god_zhaoyun | juejing | BLOCKED | Judgment/draw-phase adjacency is indirect; full locked version/draw boundary audit outstanding. |
| yj2011_cao_zhi | luoying | BLOCKED | Field judgment no longer creates false discard window; complete movement-type and multiple-event qualification outstanding. |
| yj2012_ma_dai | qianxi | BLOCKED | Judgment/retrial material color restriction tested; phase and limitation lifetime closure outstanding. |
| 动态授予/附属 | jixi | BLOCKED | Field destination now authoritative; full special-pile ViewAs target/material/consumption audit outstanding. |
| 动态授予/附属 | jilue | BLOCKED | Same-owner retrial choice order and other Jilue branches remain unverified. |

## Verification and checkpoints

- judgment_system_targeted.log: **299 passed in 5.29s**, 11 selected Python test files, including 40 new shared-system cases and one desktop presentation case. This replaces narrower intermediate totals; do not add the runs together.
- judgment_web_targeted.log: **46 passed**, 2 selected Vitest files (GamePage and pacing). Existing jsdom canvas warnings did not fail tests. Invoked vitest directly, no asset-generation pretest.
- Four changed worker engine/server mirror files byte-identical to main copies. This is changed-file synchronization only; the final Worker mirror acceptance gate has not started.
- git diff --check passed before checkpoints. Code b9558ef / 07d6bcb. Report checkpoint is the commit containing this document.
- No Huashen 795 suite, full pytest, final seven acceptance gates, roster/art changes or deployment. One row closed, below the requested 30-50 closure cadence; changes are localized judgment/delayed semantics and consumers, covered by relevant regressions. RC not issued.

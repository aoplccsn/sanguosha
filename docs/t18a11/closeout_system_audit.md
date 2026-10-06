# T18A.11 shared closeout systems audit

Baseline code c388d7b / report 2cf8720 / 163 BLOCKED. Code checkpoint **974bc0c**. Selected **79 existing BLOCKED rows** by Pindian, AOE/multitarget/counters, phase/turn/skip, extra phase/turn, awakening/limited and temporary grant dependencies; selection is explicit in closeout_system_scope.json. This batch closes **7 PASS / 3 FIXED**; resulting **153 BLOCKED / 24 FIXED / 15 PASS**.

## Independent sources and version locks

The pinned revision remains e8768851bd8054db9fd1b63cd6f1feca813590d7. Source URLs, full-file hashes and inspected symbols are in closeout_system_sources.json. Existing T17 classic catalogue locks override different later package versions; no replacement by modern Zishou, Fuhun or Zhang Liao. Source bodies were read only, not copied into implementation. Pindian publicly commits both cards and strictly compares ranks; Zongshih obtains a still-table card before cleanup. serverplayer gainAnExtraTurn nests synchronously and returns to the former current player. Fangquan pays at NotActive, after Finish. Mountain awakening marks precede max HP payment, and Zhiji reward follows payment. YJ2012 Dangxian adds Play before normal phases; Fuli consumes a once-only mark before recovery/turnover.

## Confirmed real baseline roots

| Root | Actual baseline discrepancy | Minimal reproduction and correction |
| --- | --- | --- |
| R62 | Pindian public event dropped by room; reconnect history omitted both faces/ownership | Both chosen cards/tie remain private until reveal; then publish anonymized faces with original owner IDs, retain history, display owner per card. One shared event adapter/UI repair. |
| R63 | Already skipped Draw/Play/Discard still invokes replacement skill before scheduler checks skip | Six cases: schedule or skip mark with Shelie/Fangquan/Qiaobian. Shared TurnAction checks existing skip before before_phase; replacement may still create a new skip on available phase. |
| R64 | Zhiji reward/choice occurs before max HP payment | HP3/max4 incorrectly offers recover before max drops to3; max1 gives reward before death. Pay through existing LoseMaxHp child before choice, stop dead owner, acquire Guanxing after reward. |
| R65 | Nested extra turn runs after older pending extra turns | p1 queues p3/p4; p3 grants p5; baseline chooses p4 before p5. Shared scheduler inserts newly nested batch before pending batch, preserves within-batch FIFO and original seat anchor; snapshot persists prefix. |
| R66 | Fangquan cost request occurs inside Finish and disappears if Finish skipped | Real TurnAction skips Play via Fangquan, then normal/skipped Finish; both reproduce wrong turn-end window. Move cost offer to shared TurnAction completion, after phase end and before extra-turn end offers; living/effective owner checks remain. |

Five real roots; no new defensive invariant or architecture strengthening. Cumulative real baseline roots: **68** (previous 63). Existing indirect skill evidence does not automatically close a row.

## Required boundaries and already-correct mechanisms

- Pindian: two private choices; public faces after both commit; processing origin retained; strict ties lose for initiating boolean and have no winner/loser; Zongshi own-card tie acquisition precedes remaining-card discard and respects current processing ownership. Existing source/opponent win/loss/tie and dual-holder restore cases pass. Start/payment validators and effective/living acquisition check are already present. An interrupted/terminal game uses existing engine gate and transient cleanup; no speculative concurrent mutation tests were added. Composite Pindian consumers remain BLOCKED where their independent aftermath/death windows are incomplete.
- AOE: Savage Assault/Archery traverse authoritative target cursor independently, counter cancellation affects that target alone. NullificationWindow freezes target_id throughout parity rounds and snapshot restore. Existing one-target counters, 0–4 parity chains, virtual/material damage, source-death attribution, immune and Zhenlie cases pass.
- Multi-target counter skip: test_t18a7_flow root pass is scoped to the current parent trick across targets and nested counters, persists restore, then clears so the next trick in the same turn can ask again. test_root_skip_scope rejects single-target tricks. Existing _combat_context uses active Window target while countering; current-target display Web case passes. No new counter tests were needed.
- Phase skips: consumed skip marks emit skip facts without body; both schedule and mark skip now precede replacement offer. Shensu and delayed-phase skipping existing cases pass; turn/phase completion guards stop ordinary requests after game finish.
- Extra phases/turns: Dangxian extra Play precedes Preparation/normal Play, separate usage; flipped-over skipped turns have no phases. Dead extra-turn recipients are skipped. Nested turns now precede older pending batches; original normal seat resumes through saved anchor. Fangquan end offer survives skipped Finish and reconnect.
- Awakening: once-only durable marks, effective/living checks, independent threshold and max-HP/payment gates checked in source and code. Zaoxian, Ruoyu, Hunzi, Baiyin, Zili already correct; Zhiji fixed. Project baoyin/jilue IDs map to historical Baiyin/Jilve. Existing YJSkillHandler already stops dead Zili reward; no new guard or test retained.
- Limited: Fuli spent mark and frame persist data-only snapshot. Other limited consumers have existing payment/restore cases but retain BLOCKED until their full independent ordering/target clauses close. Generic PlayerState marks are encoded/restored as dataclass fields; no new reconnect architecture needed.
- Temporary grants: source-scoped skill_grants remove only exact source; native skills live in catalogue independently. Fuhun real turn-end expiry, earlier permanent grant retention, Duorui target-end/death/source-death distinction and overlapping grant restore all pass. Whole Fuhun/Duorui stay BLOCKED for remaining conversion/borrowability compound clauses.

## Validation and exclusions

284 main targeted Python passed (11 deselected); 49 independent closure selections passed (292 deselected); after the Fangquan change, 209 relevant turn/awakening/grant/death Python passed (1 deselected). These sets overlap and **must not be added as distinct coverage**. 3 scoped GamePage Web passed (34 skipped), including Pindian ownership and authoritative AOE/current target. Diff whitespace check passed.

The final added regression file contains **12 cases**, all tied to the five confirmed roots. Initial R62–R64 reproduction: 9 failures. R65: 1 failure. R66: 2 failures. The first post-fix public-face assertion used numeric rank rather than the existing public string contract; corrected fixture, not a product bug. An initial Shelie probe used an invalid character ID; corrected to wind_god_lvmeng before recorded reproduction. Exploratory Keji converted-Slash and fatal Zili paths were correct; their new test/guard proposals were removed. No future/regression-only tests were retained. Existing correct cases were reused.

No full pytest, Zuoci 795, expanded roster, art, deployment or unrelated refactor. No final release gates/RC requested or executed.

## Per-row disposition

| General | Skill | Result | Remaining independent closure or closed scope |
| --- | --- | --- | --- |
| caocao | jianxiong | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| caocao | hujia | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| liubei | jijiang | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| lvbu | wushuang | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| zhangliao | tuxi | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| xuchu | luoyi | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| zhenji | luoshen | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| zhugeliang | guanxing | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| zhaoyun | longdan | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| huangyueying | jizhi | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| lvmeng | keji | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| zhouyu | yingzi | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| diaochan | biyue | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| wind_xiahou_yuan | shensu | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| wind_cao_ren | jushou | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| wind_yuji | guhuo | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| wind_god_lvmeng | shelie | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| fire_xun_yu | quhu | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| fire_pang_tong | niepan | BLOCKED | Spent state snapshot checked; full independent cost/target, casualty and effect-order contract remains unclosed. |
| fire_taishi_ci | tianyi | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| fire_yan_liang_wen_chou | shuangxiong | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| fire_god_zhouyu | qinyin | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| fire_god_zhouyu | yeyan | BLOCKED | Spent state snapshot checked; full independent cost/target, casualty and effect-order contract remains unclosed. |
| fire_god_zhugeliang | qixing | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| fire_god_zhugeliang | kuangfeng | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| fire_god_zhugeliang | dawu | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| forest_caopi | fangzhu | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| forest_menghuo | zaiqi | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| forest_zhurong | lieren | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| forest_sunjian | yinghun | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| forest_lusu | haoshi | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| forest_jia_xu | luanwu | BLOCKED | Spent state snapshot checked; full independent cost/target, casualty and effect-order contract remains unclosed. |
| forest_dong_zhuo | roulin | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| forest_dong_zhuo | benghuai | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| forest_god_lvbu | wumou | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| mountain_zhang_he | qiaobian | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| mountain_deng_ai | zaoxian | PASS | Complete locked clause, source/code/restore evidence recorded in matrix; PASS. |
| mountain_liushan | fangquan | FIXED | Complete locked clause, source/code/restore evidence recorded in matrix; FIXED. |
| mountain_liushan | ruoyu | PASS | Complete locked clause, source/code/restore evidence recorded in matrix; PASS. |
| mountain_jiang_wei | zhiji | FIXED | Complete locked clause, source/code/restore evidence recorded in matrix; FIXED. |
| mountain_jiang_wei | guanxing | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| mountain_sunce | hunzi | PASS | Complete locked clause, source/code/restore evidence recorded in matrix; PASS. |
| mountain_sunce | zhiba | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| mountain_zhang_zhaozhang | guzheng | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| mountain_cai_wenji | duanchang | BLOCKED | Shared source-specific acquire/expiry checked; whole conversion/borrowability or detach aftermath clauses remain unclosed. |
| mountain_god_zhaoyun | juejing | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| mountain_god_simayi | renjie | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| mountain_god_simayi | baoyin | PASS | Complete locked clause, source/code/restore evidence recorded in matrix; PASS. |
| mountain_god_simayi | lianpo | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2011_gao_shun | xianzhen | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| yj2012_wang_yi | miji | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2012_cao_zhang | jiangchi | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2012_zhong_hui | zili | PASS | Complete locked clause, source/code/restore evidence recorded in matrix; PASS. |
| yj2012_liao_hua | dangxian | PASS | Complete locked clause, source/code/restore evidence recorded in matrix; PASS. |
| yj2012_liao_hua | fuli | PASS | Complete locked clause, source/code/restore evidence recorded in matrix; PASS. |
| yj2012_guan_xing_zhang_bao | fuhun | BLOCKED | Shared source-specific acquire/expiry checked; whole conversion/borrowability or detach aftermath clauses remain unclosed. |
| yj2012_cheng_pu | lihuo | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| yj2012_cheng_pu | chunlao | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2012_han_dang | jiefan | BLOCKED | Spent state snapshot checked; full independent cost/target, casualty and effect-order contract remains unclosed. |
| yj2012_liu_biao | zishou | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2013_guo_huai | jingce | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2013_jian_yong | qiaoshui | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| yj2013_jian_yong | zongshi_jianyong | FIXED | Complete locked clause, source/code/restore evidence recorded in matrix; FIXED. |
| yj2013_yu_fan | zhiyan | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2013_fu_huanghou | zhuikong | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| yj2013_fu_huanghou | qiuyuan | BLOCKED | Shared target/counter cursor checked; whole skill response/material/trigger clauses remain unclosed. |
| yj2013_li_ru | juece | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| yj2013_li_ru | fencheng | BLOCKED | Spent state snapshot checked; full independent cost/target, casualty and effect-order contract remains unclosed. |
| shadow_god_liubei | longnu | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| shadow_god_liubei | jieying_liubei | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| shadow_god_luxun | cuike | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| shadow_god_luxun | zhanhuo | BLOCKED | Spent state snapshot checked; full independent cost/target, casualty and effect-order contract remains unclosed. |
| thunder_god_ganning | poxi | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| thunder_god_ganning | jieying_ganning | BLOCKED | Shared phase/turn scheduling and terminal gates checked; independent skill choices, costs or compound timing remain unclosed. |
| thunder_god_zhangliao | duorui | BLOCKED | Shared source-specific acquire/expiry checked; whole conversion/borrowability or detach aftermath clauses remain unclosed. |
| thunder_god_zhangliao | zhiti | BLOCKED | Shared Pindian fixed/checked; own effect eligibility, complete target and aftermath/death windows remain unclosed. |
| 动态授予/附属 | jixi | BLOCKED | Shared source-specific acquire/expiry checked; whole conversion/borrowability or detach aftermath clauses remain unclosed. |
| 动态授予/附属 | jilue | BLOCKED | Shared source-specific acquire/expiry checked; whole conversion/borrowability or detach aftermath clauses remain unclosed. |
| 动态授予/附属 | paiyi | BLOCKED | Shared source-specific acquire/expiry checked; whole conversion/borrowability or detach aftermath clauses remain unclosed. |

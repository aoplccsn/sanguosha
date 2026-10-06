# T18A.11 shared damage / HP / dying / death audit

Base b4964e1 / report 383056c; code checkpoint 1f3f2bb. This is a completed regression batch within an ongoing system audit, not RC approval.

## Scope and locked sources

Entry: 175 BLOCKED. The dependency queue includes direct damage, HP loss, recovery, rescue, death, damage counters, awakening HP changes, damage prevention/transfer, chained packets, and consumers of those facts. It does not imply every skill in the queue is fully audited.

Project lock: docs/t17/final_version_lock.md, docs/t17/version_matrix.md, current authoritative registry and subsequent accepted roster/version decisions. The old lock's 65 roster count is historical; current production is 103. Classic Luoyi uses NosLuoyi, not the modern reveal version. Classic Anjian adds damage automatically in its historical clause (NotCompulsory frequency is not an optional invocation in that implementation).

Independent community archive: Mogara/QSanguosha-v2 revision e8768851bd8054db9fd1b63cd6f1feca813590d7. Read server/room.cpp getAllPlayers / recover / loseHp / loseMaxHp, server/gamerule.cpp AskForPeaches / DamageDone, package/nostalgia.cpp NosLuoyiBuff, package/wind.cpp Tianxiang / Kuanggu, package/fire.cpp Jieming, and clauses in damage_source_evidence.json. That file records pinned URLs, content hashes and inspected skill excerpts. No external implementation copied. This archive is auxiliary historical evidence, not an official publisher card archive. Project accepted versions override differing archive clauses.

## Classification and public changes

| Category | Finding |
| --- | --- |
| Previously correct, unverified | Zhuiyi death-owner request, excludes killer, source-less beneficiary set, optional decline, draw then recover; PASS |
| Version differences | Modern Luoyi/Buqu variants are not a reason to change accepted project versions. Kuanggu archive recovers damage amount at once; current project emits per-point recovery. This event-granularity and timing difference remains BLOCKED pending lock/source reconciliation |
| Test problems | Fatal Zhichi fixture assumed target-first rescue. Source-death cleanup fixture killed the lord then illegally started another turn. New fixtures initially used None instead of PASS_RESPONSE, assumed 4 rather than 5 seats, and introduced two lords. These are not product bugs |
| Real baseline bugs | R37-R44 below; 8 shared roots, not one defect per failed test |
| Development correction | Terminal gate first draft omitted cleanup when last frame ended game; corrected within R42. Base DamageAction lacks military extension fields; use getattr compatibility. Neither is an additional baseline defect |

R37 current-seat rescue order (inactive current rotates last); R38 same rescuer may repeatedly Peach until HP positive or pass; R39 full/dead recovery silently no-ops; R40 zero max HP dies directly without Peach; R41 dead damage source normalized to None; R42 engine-wide terminal gate and transient public card cleanup; R43 source bonuses freeze before target transfer, exclude chain/transfer reapplication; R44 Jiuyuan checks Wu rescuer, not matching factions.

Damage and LoseHP retain separate event paths: LoseHP causes no DamageDealt or damage counters, fatal loss enters source-less rescue/death. Recover clamps actual restored amount. Ordinary rescue cursor and repeat request IDs survive snapshots. Self Wine cannot rescue another player. Active/living/effective Wansha restricts the ordinary Peach route; no blanket prohibition on unrelated Recover actions.

Terminal gate rejects top-level actions after FINISHED and stops parents, reactions and later chained/AOE targets. Death skill exceptions resolve while the game is still active; Zhuiyi and dead-owner Wuhun tie choice are tested before final victory. Cleanup discards PROCESSING and ownerless SPECIAL public pools through CardMove. Restored terminal state has no pending request/stack. Per-player private piles retain their ordinary death rules.

## Evidence and closures

37 new deterministic cases in tests/test_t18a11_damage_system.py. Existing AOE source-death/target-skip, suppression, Cheng Pu, Wind, Gods, death lease/cleanup and fatal Zhichi consumers are included in damage_dependencies_targeted.log: 302 passed in 4.28s. Snapshot restoration is exercised at rescue, transfer, dead-owner exception and terminal boundaries. This count is a single latest run, not a sum of repeated runs.

Saved failing evidence: damage_system_reproduction.log (R37-R42), damage_transfer_modifier_reproduction.log (R43), jiuyuan_reproduction.log (R44: two faction failures; four other failures in that log are explicitly fixture errors above).

Closed: Jiuyuan / Wansha / Anjian FIXED; Zhuiyi PASS. All full clauses for these four are recorded in the matrix. No claim that all HP/death consumers or every terminal invariant have passed.

Still BLOCKED examples: Jueqing source-modifier priority; Luoyi full draw/turn lifecycle; Kuanggu recovery granularity and post-dying timing; Tianxiang full chained recipient/armor/draw clause audit; Wuhun complete judgment definition/death cleanup audit; damage-trigger skill ordering, revival/limited/awakening costs, equipment and private-pile side effects, terminal skill cleanup. Existing green tests do not settle independent locked-rule evidence for these.

No full pytest, Huashen 795 suite, final seven gates, art generation, roster expansion or deployment. Changed-file mirrors were compared as a local edit sanity check, not the final Worker mirror acceptance gate.

## Dependency queue at entry

| general_id | skill_id | disposition |
| --- | --- | --- |
| caocao | jianxiong | BLOCKED: shared dependency checked; remaining full skill clauses required |
| liubei | rende | BLOCKED: shared dependency checked; remaining full skill clauses required |
| sunquan | jiuyuan | FIXED |
| simayi | fankui | BLOCKED: shared dependency checked; remaining full skill clauses required |
| xiahou_dun | ganglie | BLOCKED: shared dependency checked; remaining full skill clauses required |
| xuchu | luoyi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| guojia | yiji | BLOCKED: shared dependency checked; remaining full skill clauses required |
| huanggai | kurou | BLOCKED: shared dependency checked; remaining full skill clauses required |
| sunshangxiang | jieyin | BLOCKED: shared dependency checked; remaining full skill clauses required |
| huatuo | qingnang | BLOCKED: shared dependency checked; remaining full skill clauses required |
| wind_huang_zhong | liegong | BLOCKED: shared dependency checked; remaining full skill clauses required |
| wind_wei_yan | kuanggu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| wind_xiao_qiao | tianxiang | BLOCKED: shared dependency checked; remaining full skill clauses required |
| wind_zhou_tai | buqu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| wind_zhang_jiao | leiji | BLOCKED: shared dependency checked; remaining full skill clauses required |
| wind_yuji | guhuo | BLOCKED: shared dependency checked; remaining full skill clauses required |
| wind_god_guanyu | wuhun | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_dian_wei | qiangxi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_xun_yu | quhu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_xun_yu | jieming | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_pang_tong | niepan | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_god_zhouyu | qinyin | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_god_zhouyu | yeyan | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_god_zhugeliang | kuangfeng | BLOCKED: shared dependency checked; remaining full skill clauses required |
| fire_god_zhugeliang | dawu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_caopi | xingshang | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_caopi | fangzhu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_menghuo | zaiqi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_zhurong | lieren | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_sunjian | yinghun | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_jia_xu | wansha | FIXED |
| forest_jia_xu | luanwu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_dong_zhuo | jiuchi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_dong_zhuo | benghuai | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_dong_zhuo | baonue | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_god_caocao | guixin | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_god_lvbu | kuangbao | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_god_lvbu | wumou | BLOCKED: shared dependency checked; remaining full skill clauses required |
| forest_god_lvbu | shenfen | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_deng_ai | zaoxian | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_liushan | ruoyu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_jiang_wei | zhiji | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_sunce | hunzi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_zuoci | xinsheng | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_cai_wenji | beige | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_cai_wenji | duanchang | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_god_zhaoyun | juejing | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_god_zhaoyun | longhun | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_god_simayi | renjie | BLOCKED: shared dependency checked; remaining full skill clauses required |
| mountain_god_simayi | baoyin | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_zhang_chunhua | jueqing | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_zhang_chunhua | shangshi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_cao_zhi | jiushi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_fa_zheng | enyuan | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_ma_su | xinzhan | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_ma_su | huilei | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_xu_shu | jujian | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_xu_sheng | pojun | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_wu_guotai | ganlu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2011_wu_guotai | buyi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_xun_you | zhiyu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_wang_yi | miji | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_zhong_hui | quanji | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_zhong_hui | zili | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_liao_hua | fuli | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_guan_xing_zhang_bao | fuhun | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_bu_lianshi | zhuiyi | PASS |
| yj2012_cheng_pu | lihuo | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_cheng_pu | chunlao | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2012_hua_xiong | shiyong | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_cao_chong | chengxiang | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_cao_chong | renxin | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_guo_huai | jingce | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_man_chong | yuce | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_pan_zhang_ma_zhong | duodao | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_pan_zhang_ma_zhong | anjian | FIXED |
| yj2013_yu_fan | zhiyan | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_zhu_ran | danshou | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_fu_huanghou | zhuikong | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_li_ru | juece | BLOCKED: shared dependency checked; remaining full skill clauses required |
| yj2013_li_ru | fencheng | BLOCKED: shared dependency checked; remaining full skill clauses required |
| shadow_god_liubei | longnu | BLOCKED: shared dependency checked; remaining full skill clauses required |
| shadow_god_luxun | junlve | BLOCKED: shared dependency checked; remaining full skill clauses required |
| shadow_god_luxun | cuike | BLOCKED: shared dependency checked; remaining full skill clauses required |
| shadow_god_luxun | zhanhuo | BLOCKED: shared dependency checked; remaining full skill clauses required |
| thunder_god_ganning | poxi | BLOCKED: shared dependency checked; remaining full skill clauses required |
| thunder_god_zhangliao | duorui | BLOCKED: shared dependency checked; remaining full skill clauses required |
| thunder_god_zhangliao | zhiti | BLOCKED: shared dependency checked; remaining full skill clauses required |
| 动态授予/附属 | jilue | BLOCKED: shared dependency checked; remaining full skill clauses required |
| 动态授予/附属 | paiyi | BLOCKED: shared dependency checked; remaining full skill clauses required |

| zhouyu | fanjian | BLOCKED: damage clause missing from abbreviated catalogue; independent source/implementation audit required |

Entry dependent rows: 91. Current matrix: {'BLOCKED': 171, 'FIXED': 17, 'PASS': 4}.

Description regex is only a first-pass aid: Heart-suit mentions can falsely match Peach, and Fanjian omits damage in its abbreviated description. Fanjian was explicitly added after implementation-scope review. Ordinary Slash/ViewAs producers remain covered by the earlier use/response queue; this queue prioritizes direct HP/death clauses and observers.

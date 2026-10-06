# T18A.11 shared CardMove / acquisition / discard / equipment / piles audit

Base code 1f3f2bb / report 9d680c6; new code 8d449b4. Ongoing conformance audit, not RC approval.

## Dependency scope

Entry 171 BLOCKED. Screened description clauses for drawing, obtaining, discard, hand/equipment, judgment/pindian, deck placement and piles; explicitly added removal/ViewAs material consumers missed by abbreviated descriptions (Fankui, Wusheng, Longdan, Wushen, Longhun, Jixi). Result: 144 dependent rows / 143 unique skills. card_move_scope.json preserves the entry list, including shared Guanxing rows. This is deliberately a dependency queue, not 144 full skill approvals. Ordinary card costs make many skills consumers; complete independent trigger/version/limits evidence remains required.

## Sources and locked versions

Project current 103 registry, docs/t17/final_version_lock.md, version_matrix.md, roster.md and subsequent accepted decisions govern. Fixed community archive Mogara/QSanguosha-v2 e8768851bd8054db9fd1b63cd6f1feca813590d7 supplies auxiliary clauses; pinned URLs, SHA256 and inspected excerpts in card_move_source_evidence.json. No external implementation copied; archive is not an official publisher card record.

Quanji: accepted single-awakening Zhong Hui frozen text is the damage-per-point/public-power version, matched by yjcm.cpp Quanji. NostalgiaPackage.lua nosquanji instead means an early promotional pindian skill; the shared name/prefix is not enough to choose that alternate. Classic Lianying uses NosLianying drawing one, not modern multi-recipient Lianying. Xingshang archive obtains hand + equipment, not judgment/private piles. Tuntian NotActive and own hand/equipment transfer exemption independently checked in mountain.cpp. Zongxuan BeforeCardsMove diverts selected cards to draw top publicly before ordinary discard consequences.

## Classification

| Category | Finding / disposition |
| --- | --- |
| Implementation already correct | Sole physical ownership in GameState.zones; direct live cross-zone mutations are centralized. Draw/recycle, equipment replacement/loss, pile privacy, counter storage, camp hand transfer, private snatch/public dismantle, snapshot and AI fixtures passed related checks |
| Version difference | Modern Lianying differs from classic; nostalgia nosquanji is another Zhong Hui version. Do not upgrade accepted clauses. Tuntian currently obtains successful judgment from discard after FinishJudge; priority/final-card destination differs from archive and remains BLOCKED pending full judgment combination audit |
| Test issue | Legacy Forest test incorrectly expected Xingshang to gain judgment. Corrected using independent clause and new failing reproduction. Initial new tests referenced nonexistent PlayerView.visible_hand / ResolutionStack.frames and incorrect Xuanfeng owner field; corrected to real APIs; not bugs |
| Real product bugs | R45 Tuntian qualifies internal hand/equipment relocation and misses inactive current loss; R46 redundant power count stale after shared moves/death; R47 Zongxuan reservation publishes premature/duplicate equipment reactions and final-discard public logs; R48 Xingshang illegally acquires judgment |
| Defensive contract improvements | H01 obtain_cards preflights duplicate occurrences across the entire batch before any mutation. Reproduction intentionally constructs corrupt state rejected by normal snapshot validation; not a demonstrated normal-game baseline bug. C01 Xingshang routes cross-zone cards through shared acquisition summary. Dead source cannot receive Enyuan gratitude, so omitted summary is not counted as a reachable extra Enyuan gameplay defect |

Six shared root/contract corrections, of which four are baseline product bugs and two are defensive/consistency improvements. Previous 46 baseline roots -> 50. Failed assertions, source differences and incomplete verification are not added to defect count.

## Public implementation

CardMoveService.move checks distinct known cards, unique current location, player refs, equipment capacity/abolished slots and commits both areas before events. obtain_cards now checks every occurrence before first grouped move. Invalid batch test asserts no zone/event mutation. EquipmentExchangeTransaction retains its prevalidated atomic per-slot path and departure batch event.

Power pile count is derived on shared entry/exit, including death cleanup; actual hand-limit calculation reads zone size, never a corrupted redundant mark. Rule-trigger events and public logs now exclude internal reservation commits via default-compatible CardMove/CardMovedEvent.triggers_rules. Zongxuan publishes original-source semantic moves once after its choice, plus public top-card reveals. Physical events remain in authoritative snapshot history for reconciliation; internal event field is not exposed in product flows. Old snapshots omit the field and get the default true.

Xingshang uses hand/equipment eligibility helper and shared obtain_cards, combining all zones from one victim into one acquisition summary. Judgment/private piles remain for ordinary death cleanup. Multi-owner order/decline/disabled holder and source-less/nonempty-zone cases are tested.

## Location writer inventory

Production live cross-zone writes: engine/card_moves.py move and equipment exchange. Other rg matches were checked: skills.py Guanxing same-deck permutation; MilitarySlashSequence/Wusheng/Danshou distance-cost probes use copied state/zones; session and pregame initialization; snapshot restoration; explicit local review fixture in multiplayer/room.py. No new live skill append/remove bypass established. Existing card_move_path_audit.md links this new evidence; old simulation evidence is historical and was not rerun. Mark dictionaries store quantities/links rather than a second entity-card owner.

## Piles and visibility

| Key | Storage / face rule | Result |
| --- | --- | --- |
| quan | SPECIAL owner; accepted public power faces; redundant count synchronized | CardMove conservation/restore/death verified; full Quanji FIXED |
| counter (inverse / ni) | SPECIAL owner; public; hand/equipment removal into pile; two counters pay virtual Slash | related Xiansi tests; full skill remains BLOCKED for remaining use/target clauses |
| tian | SPECIAL owner; public; distance reads pile size | own relocation/inactive loss fixed; judgment disposition still BLOCKED |
| wine | SPECIAL owner; public stored Slash for Chunlao | storage/restore/death and related consumers verified; full skill remains BLOCKED |
| buqu | SPECIAL owner; public | storage/restore/death checked; accepted variant full clauses remain BLOCKED |
| star | SPECIAL owner; owner-private; others only count/anonymous backs | entry/projection/restore/death checked; Qixing full exchange/cost clauses remain BLOCKED |
| committed:* | SPECIAL owner; private unless revealed_committed | Guhuo/Xinzhan/Zongxuan temporary storage; reservation must not create normal movement consequences early |
| ownerless SPECIAL | Public temporary pools (Amazing Grace etc.) | authoritative shared-card projection and ordinary CardMove cleanup; previous terminal evidence reused, not rerun damage audit |
| camp (ying) | Player mark + camp_sources owner link, not an entity-card pile | entity cards stay in current hand; accepted end-turn whole-hand obtain uses shared acquisition; camp tests passed |
| rage/ren/nightmare/junlve and other counters | Integer marks, no stored card IDs | not a parallel physical card location |

Public discard reveals anonymous face data. Before choosing opponent hand, labels remain backs; private hand-to-hand obtain does not publish cards. Equipment/judgment are public. Private stars and committed cards remain concealed to other viewers. The tests cover state projection and room public event paths; this is not final browser/PySide acceptance.

## Evidence / closure

New tests/test_t18a11_card_move_system.py: 29 deterministic cases. Failing reproduction logs: card_move_system_reproduction.log (R45/R46 + H01/C01), card_move_reservation_reproduction.log (R47), card_move_inherit_reproduction.log (R48).

Latest related run: card_move_dependencies_targeted.log 354 passed in 7.17s, including Forest/Mountain, Quanji/Paiyi, equipment, camp, Xiansi, Zongxuan, network request privacy, snapshots, judgment, pindian, Duodao and Mieji consumers. Separate small selections: card_move_ai_targeted.log 2 passed / 15 deselected; card_move_privacy_targeted.log 3 passed / 206 deselected. These are 359 non-overlapping cases in final selected runs; earlier narrower passes are not added.

Closed Quanji and Xingshang FIXED. No PASS row newly closed. Remaining dependencies retain BLOCKED explicitly: full trigger priority, acquisition batching across other skills, Tuntian final judgment destination, Zongxuan interruption/skill-loss and complete multi-zone discard transaction boundaries, armour invalidation, whole-skill phase/limit clauses and event-consumer combinations. Passing move-service tests alone cannot close them.

No Huashen 795 suite, full pytest, final seven gates, art, roster expansion or deployment. The scoped hidden-info selection deselects all 206 roster cases. Changed-file mirrors compared only as an edit sanity check, not final Worker gate. Only 2 rows closed; no 30-50-row full-pytest interval reached.

## Entry dependent rows

| general_id | skill_id | disposition |
| --- | --- | --- |
| caocao | jianxiong | BLOCKED: dependency evidence; full clauses outstanding |
| liubei | rende | BLOCKED: dependency evidence; full clauses outstanding |
| sunquan | zhiheng | BLOCKED: dependency evidence; full clauses outstanding |
| guanyu | wusheng | BLOCKED: dependency evidence; full clauses outstanding |
| simayi | fankui | BLOCKED: dependency evidence; full clauses outstanding |
| simayi | guicai | BLOCKED: dependency evidence; full clauses outstanding |
| xiahou_dun | ganglie | BLOCKED: dependency evidence; full clauses outstanding |
| zhangliao | tuxi | BLOCKED: dependency evidence; full clauses outstanding |
| xuchu | luoyi | BLOCKED: dependency evidence; full clauses outstanding |
| guojia | tiandu | BLOCKED: dependency evidence; full clauses outstanding |
| guojia | yiji | BLOCKED: dependency evidence; full clauses outstanding |
| zhenji | luoshen | BLOCKED: dependency evidence; full clauses outstanding |
| zhugeliang | guanxing | BLOCKED: dependency evidence; full clauses outstanding |
| zhugeliang | kongcheng | BLOCKED: dependency evidence; full clauses outstanding |
| zhaoyun | longdan | BLOCKED: dependency evidence; full clauses outstanding |
| machao | tieqi | BLOCKED: dependency evidence; full clauses outstanding |
| huangyueying | jizhi | BLOCKED: dependency evidence; full clauses outstanding |
| lvmeng | keji | BLOCKED: dependency evidence; full clauses outstanding |
| huanggai | kurou | BLOCKED: dependency evidence; full clauses outstanding |
| zhouyu | yingzi | BLOCKED: dependency evidence; full clauses outstanding |
| daqiao | liuli | BLOCKED: dependency evidence; full clauses outstanding |
| luxun | lianying | BLOCKED: dependency evidence; full clauses outstanding |
| sunshangxiang | jieyin | BLOCKED: dependency evidence; full clauses outstanding |
| sunshangxiang | xiaoji | BLOCKED: dependency evidence; full clauses outstanding |
| huatuo | qingnang | BLOCKED: dependency evidence; full clauses outstanding |
| diaochan | lijian | BLOCKED: dependency evidence; full clauses outstanding |
| diaochan | biyue | BLOCKED: dependency evidence; full clauses outstanding |
| wind_xiahou_yuan | shensu | BLOCKED: dependency evidence; full clauses outstanding |
| wind_cao_ren | jushou | BLOCKED: dependency evidence; full clauses outstanding |
| wind_huang_zhong | liegong | BLOCKED: dependency evidence; full clauses outstanding |
| wind_xiao_qiao | tianxiang | BLOCKED: dependency evidence; full clauses outstanding |
| wind_zhou_tai | buqu | BLOCKED: dependency evidence; full clauses outstanding |
| wind_zhang_jiao | leiji | BLOCKED: dependency evidence; full clauses outstanding |
| wind_zhang_jiao | guidao | BLOCKED: dependency evidence; full clauses outstanding |
| wind_yuji | guhuo | BLOCKED: dependency evidence; full clauses outstanding |
| wind_god_guanyu | wushen | BLOCKED: dependency evidence; full clauses outstanding |
| wind_god_guanyu | wuhun | BLOCKED: dependency evidence; full clauses outstanding |
| wind_god_lvmeng | shelie | BLOCKED: dependency evidence; full clauses outstanding |
| wind_god_lvmeng | gongxin | BLOCKED: dependency evidence; full clauses outstanding |
| fire_dian_wei | qiangxi | BLOCKED: dependency evidence; full clauses outstanding |
| fire_xun_yu | quhu | BLOCKED: dependency evidence; full clauses outstanding |
| fire_xun_yu | jieming | BLOCKED: dependency evidence; full clauses outstanding |
| fire_pang_tong | niepan | BLOCKED: dependency evidence; full clauses outstanding |
| fire_wolong | bazhen | BLOCKED: dependency evidence; full clauses outstanding |
| fire_taishi_ci | tianyi | BLOCKED: dependency evidence; full clauses outstanding |
| fire_pang_de | mengjin | BLOCKED: dependency evidence; full clauses outstanding |
| fire_yan_liang_wen_chou | shuangxiong | BLOCKED: dependency evidence; full clauses outstanding |
| fire_yuan_shao | xueyi | BLOCKED: dependency evidence; full clauses outstanding |
| fire_god_zhouyu | qinyin | BLOCKED: dependency evidence; full clauses outstanding |
| fire_god_zhouyu | yeyan | BLOCKED: dependency evidence; full clauses outstanding |
| fire_god_zhugeliang | qixing | BLOCKED: dependency evidence; full clauses outstanding |
| fire_god_zhugeliang | kuangfeng | BLOCKED: dependency evidence; full clauses outstanding |
| fire_god_zhugeliang | dawu | BLOCKED: dependency evidence; full clauses outstanding |
| forest_caopi | xingshang | FIXED |
| forest_caopi | fangzhu | BLOCKED: dependency evidence; full clauses outstanding |
| forest_caopi | songwei | BLOCKED: dependency evidence; full clauses outstanding |
| forest_xuhuang | duanliang | BLOCKED: dependency evidence; full clauses outstanding |
| forest_menghuo | zaiqi | BLOCKED: dependency evidence; full clauses outstanding |
| forest_zhurong | lieren | BLOCKED: dependency evidence; full clauses outstanding |
| forest_sunjian | yinghun | BLOCKED: dependency evidence; full clauses outstanding |
| forest_lusu | haoshi | BLOCKED: dependency evidence; full clauses outstanding |
| forest_lusu | dimeng | BLOCKED: dependency evidence; full clauses outstanding |
| forest_dong_zhuo | jiuchi | BLOCKED: dependency evidence; full clauses outstanding |
| forest_dong_zhuo | baonue | BLOCKED: dependency evidence; full clauses outstanding |
| forest_god_caocao | guixin | BLOCKED: dependency evidence; full clauses outstanding |
| forest_god_lvbu | kuangbao | BLOCKED: dependency evidence; full clauses outstanding |
| forest_god_lvbu | wumou | BLOCKED: dependency evidence; full clauses outstanding |
| forest_god_lvbu | wuwei | BLOCKED: dependency evidence; full clauses outstanding |
| forest_god_lvbu | shenfen | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_zhang_he | qiaobian | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_deng_ai | tuntian | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_deng_ai | zaoxian | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_liushan | xiangle | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_liushan | fangquan | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_liushan | ruoyu | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_jiang_wei | tiaoxin | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_jiang_wei | zhiji | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_jiang_wei | guanxing | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_sunce | jiang | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_sunce | hunzi | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_sunce | zhiba | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_zhang_zhaozhang | zhijian | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_zhang_zhaozhang | guzheng | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_zuoci | xinsheng | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_cai_wenji | beige | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_god_zhaoyun | juejing | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_god_zhaoyun | longhun | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_god_simayi | renjie | BLOCKED: dependency evidence; full clauses outstanding |
| mountain_god_simayi | baoyin | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_zhang_chunhua | shangshi | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_yu_jin | yizhong | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_cao_zhi | luoying | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_fa_zheng | enyuan | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_fa_zheng | xuanhuo | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_ma_su | xinzhan | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_ma_su | huilei | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_xu_shu | jujian | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_ling_tong | xuanfeng | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_xu_sheng | pojun | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_wu_guotai | ganlu | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_wu_guotai | buyi | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_chen_gong | mingce | BLOCKED: dependency evidence; full clauses outstanding |
| yj2011_gao_shun | xianzhen | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_xun_you | zhiyu | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_wang_yi | miji | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_cao_zhang | jiangchi | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_zhong_hui | quanji | FIXED |
| yj2012_zhong_hui | zili | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_guan_xing_zhang_bao | fuhun | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_ma_dai | qianxi | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_bu_lianshi | anxu | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_cheng_pu | chunlao | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_han_dang | gongqi | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_han_dang | jiefan | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_liu_biao | zishou | BLOCKED: dependency evidence; full clauses outstanding |
| yj2012_liu_biao | zongshi | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_cao_chong | chengxiang | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_cao_chong | renxin | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_guo_huai | jingce | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_man_chong | junxing | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_man_chong | yuce | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_guan_ping | longyin | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_jian_yong | qiaoshui | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_jian_yong | zongshi_jianyong | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_liu_feng | xiansi | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_pan_zhang_ma_zhong | duodao | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_yu_fan | zongxuan | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_yu_fan | zhiyan | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_zhu_ran | danshou | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_fu_huanghou | zhuikong | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_li_ru | juece | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_li_ru | mieji | BLOCKED: dependency evidence; full clauses outstanding |
| yj2013_li_ru | fencheng | BLOCKED: dependency evidence; full clauses outstanding |
| shadow_god_liubei | longnu | BLOCKED: dependency evidence; full clauses outstanding |
| shadow_god_liubei | jieying_liubei | BLOCKED: dependency evidence; full clauses outstanding |
| shadow_god_luxun | cuike | BLOCKED: dependency evidence; full clauses outstanding |
| shadow_god_luxun | zhanhuo | BLOCKED: dependency evidence; full clauses outstanding |
| thunder_god_ganning | poxi | BLOCKED: dependency evidence; full clauses outstanding |
| thunder_god_ganning | jieying_ganning | BLOCKED: dependency evidence; full clauses outstanding |
| thunder_god_zhangliao | duorui | BLOCKED: dependency evidence; full clauses outstanding |
| thunder_god_zhangliao | zhiti | BLOCKED: dependency evidence; full clauses outstanding |
| 动态授予/附属 | jixi | BLOCKED: dependency evidence; full clauses outstanding |
| 动态授予/附属 | jilue | BLOCKED: dependency evidence; full clauses outstanding |
| 动态授予/附属 | paiyi | BLOCKED: dependency evidence; full clauses outstanding |

Current matrix: {'BLOCKED': 169, 'FIXED': 19, 'PASS': 4}.

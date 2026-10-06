# T18A.11 Equipment / distance audit

2026-10-07. Entry: code 07d6bcb, report 0984e8c, 168 BLOCKED. Code checkpoint **c388d7b**. This records a scoped shared-system batch; final acceptance and RC approval have not started.

## Outcome and scope

Matrix inventory: **57 dependent BLOCKED rows / 55 unique skills**, from equipment/weapon/armor/horse/distance/range descriptions and explicit shared cost, ViewAs, equipment-move and borrowed-skill consumers. Indirect costs/movement dependencies are included; that does not imply a full independent judgment/damage/phase audit of each skill. Individual outcomes and remaining clauses are in equipment_distance_scope.json and the table below.

**8 real baseline public roots repaired (R54-R61), 8 product bugs; 1 defensive state invariant (H03); 1 explicit equipment replacement contract adjustment (C02).** Product bugs are counted by common cause, not number of failing parametrized cases. Cumulative real baseline roots **63**, previously 55. H03 and C02 are not counted in that number.

Closed **4 PASS rows**: the three native Mashu owners and Feiying, already implemented correctly with new independent evidence. Closed **1 FIXED row**: Qicai. Matrix now **163 BLOCKED / 21 FIXED / 8 PASS**, still 192 rows / 189 unique skills / 103 generals. No other dependency is closed from shared test success alone.

## Rule authority and versions

Project authority remains docs/t17/final_version_lock.md, version_matrix.md, accepted classic general catalogue and current formal card definitions. Historical community semantic references are pinned, not presented as official publisher rulings. equipment_distance_sources.json stores exact URLs, SHA256 and excerpts.

QSanguosha-v2 revision e8768851bd8054db9fd1b63cd6f1feca813590d7: standard-cards.cpp (all Standard/EX weapons/armor, Snatch), maneuvering.cpp (Ancient Blade/Fan/Vine/Silver Lion), standard-generals.cpp (Mashu/Qicai), god.cpp (Feiying), core/player.cpp (living-seat geometry/range), standard.cpp (equipment replacement). No third-party implementation copied into engine files.

God Zhang Liao stays on the project locked **classic drlt_duorui / drlt_zhiti** lease/disable-slot version, from Noname revision e18a8256e01ab1357e4c7472349dceb3d0aa1a3a, character/extra/skill.js. The initial substring lookup hit OL entries; final evidence uses exact drlt keys. OL suppression/end-play and OL Zhiti extra draw/random abolition variants are explicitly excluded. Project retains its current play-phase trigger restriction and formal native-skill exclusions; source turn-vs-play wording/compound eligibility are not silently rewritten.

Current formal deck: **11 weapons, 4 armors, 7 horses**; four equipment slots (weapon/armor/offensive horse/defensive horse). **No treasure card or treasure slot is registered.** Historical drlt archives may support a fifth slot; this is a current project/deck boundary, not a reason to expand cards or fabricate an unavailable treasure action. Four-slot abolition and all-slots-abolished behavior are tested.

## Product roots and reproductions

| ID | Before | Shared root correction | Minimal evidence |
| --- | --- | --- | --- |
| R54 | Axe could discard its own equipped physical card, even offering with only Axe plus one other card | Shared axe_materials excludes equipped weapon, drives offer/request/submit validation | equipment_distance_reproduction.log, two Axe cases |
| R55 | Kylin Bow queried after HP loss/death; lethal target lost the legal horse window | DamageCaused-side shared damage frame offers before target defenses, transfer and HP loss; original user Slash only, no chain/transfer repetition | Same log: normal and lethal timing failures; restore and actual horse discard |
| R56 | Ice Sword selected both cards from the initial state and moved them before first-loss reactions | Shared weapon discard action chooses/moves one at a time, yields to reactions and queries fresh second candidates | Same log: armor loss / Xiaoji draw creates new second-discard candidates; snapshot at second choice |
| R57 | Qicai ignored Snatch distance but not Supply Shortage | Delayed distance restriction uses same effective Qicai exemption while preserving duplicate/target checks | equipment_qicai_reproduction.log after correcting fixture; disabled/restore/Slash separation counterexamples |
| R58 | Qiangxi weapon cost hard reset attack range to 1, dropping independent Gongqi modifier | Detached cost probe calls shared live DistanceSystem; no live equipment preview mutation | equipment_distance_modifiers_reproduction.log Qiangxi true failure; ordinary existing cost regression |
| R59 | First target stole Qinggang Sword; later already-specified targets regained armor | Freeze Qinggang applicability on Slash use sequence and carry it into target packets; keep current gear authority for later uses | equipment_qinggang_reproduction.log: first Fankui obtains sword, second Vine target still takes Slash damage |
| R60 | Hand horse projection omitted slot type; card face could not show signed modifier; PySide equipped token omitted sign | Publish definition slot on hand/public CardView and use common desktop signed label in card, preview and equipment token; existing Web labels consume it | equipment_horse_projection_reproduction.log two slot failures; desktop +/- tests and Web face/abolished-slot test |
| R61 | Green Dragon follow-up paid a response and discarded materials before damage, with no CardUsed event; new empty Kongcheng remained selectable | Shared response provider has explicit use_card mode, passes through allied providers and keeps materials in processing; parent records one uncounted use, normal Slash sequence, cleanup after effects; ordinary and weapon Slash share target prohibitions | equipment_green_dragon_reproduction.log physical/Wusheng; equipment_green_target_reproduction.log empty Kongcheng; physical/virtual/Jijiang pending Jianxiong and restore regressions |

R61 does not patch each ViewAs skill: one shared movement adapter changes reason/cleanup only for the explicit use-card mode. Ordinary response defaults remain unchanged. A provider's material owner can differ from the actual user (Jijiang); recorded use belongs to the weapon wielder. Follow-up does not add the normal Slash history count, ignores geometric distance per fixed Blade source, still checks prohibitions, and allows damage/material reactions to finish before discarding remaining supplied cards. Terminal stack cleanup is reused.

## Defensive and explicit project contract changes

**H03: snapshot/state invariant.** CardMove already rejected second equipment and entry into abolished slots. GameState construction/restore now also rejects a slot containing two cards or a nonempty abolished slot. Tests construct invalid states deliberately; no natural reachable baseline corrupt-state bug is claimed. Card uniqueness validation remains existing authority.

**C02: replacement contract.** The user explicitly requires old equipment departure and reactions before new installation. Equipment handler now has two resolution steps: move old through CardMove; allow leave reactions and snapshot while new stays PROCESSING; then install. The pinned historical EquipCard::use uses atomic exchange, so this is documented as the requested project contract/variant adjustment, not counted as an independently proved classic baseline product bug. The old direct handler unit test was updated to step twice and assert the intermediate state, not removed. Silver Lion/Xiaoji replacement regression passes.

## Geometry and permission evidence

All distinct living-seat pairs checked in five- and eight-player modes, then after a dead seat is removed from geometry. Horse effects and effective Mashu/Feiying compose on **distance**, clamped to at least 1; they do not increase **attack range**. All 11 physical weapons have their registered radius verified and range immediately returns to 1 after departure, including restore. Fixed Zhuikong distance overrides horse/skill deltas; the existing scoped Xianzhen exception remains separate.

Native Mashu roster parameters come from the authoritative registry, not a stale hand list: each owner reduces outgoing distance, preserves reverse distance, responds to lease suppression/expiration and permanent disabling. Multiple grants do not double the modifier. Feiying increases incoming distance and respects disable/restore. Qicai bypasses Snatch and Supply Shortage distance, retains duplicate delayed prohibition, stops when disabled and does not grant long-range Slash.

Crossbow's limit is a live gear query. A used Slash plus equipped Crossbow permits further use; losing the physical Crossbow restores ordinary limit. Native Paoxiao remains effective after departure. Existing Wusheng detached equipment-cost preview and ViewAs quota regressions pass, so consuming an equipped weapon/horse uses post-cost geometry/permission rather than old gear. Qiangxi now uses that same principle and preserves independent range modifiers.

## Weapon-by-weapon comparison

These are scoped evidence entries, not blanket card PASS/RC approval; unresolved composite timing remains explicit.

| Weapon | Radius | Clause compared / evidence | Limits of this batch |
| --- | --- | --- | --- |
| Crossbow | 1 | Live unlimited Slash quota; departure resets, native Paoxiao survives | All temporary permission/extra-phase combinations not certified |
| Double Sword | 2 | Optional opposite-gender offer; target hand discard or owner draw; real action regression | Full TargetSpecified/redirect/multi-trigger ordering not closed |
| Qinggang Sword | 2 | Target-bound armor bypass survives loss during this use (R59) | Broader TargetSpecified/redirect pair ordering remains partial |
| Green Dragon Blade | 3 | SlashMissed optional follow-up; use event/table lifetime/free history/target prohibition (R61) | All dynamically supplied/compound skill variants not certified |
| Serpent Spear | 3 | Exactly two hand cards; virtual suit/color; active quota; response; own equipment excluded; color restrictions and restore | Existing UI cancellation/acquired-context tests reused, no 795 rerun |
| Axe | 3 | Optional after miss; exactly two costs excluding weapon; submit revalidation (R54) | All triggered-skill simultaneous cost ordering remains partial |
| Halberd | 4 | Last-hand Slash extra targets and wine consumed once; registered radius | All virtual multi-material last-hand/extra-target modifiers not certified |
| Kylin Bow | 5 | Optional horse discard before HP at DamageCaused, including lethal hit (R55) | Full simultaneous DamageCaused skill priority not closed |
| Ice Sword | 2 | Optional replace damage; target hand/equipment up to two sequential discards (R56) | All simultaneous replacement modifiers not certified |
| Ancient Blade | 2 | Empty-hand direct Slash damage bonus; actual hit regression | Transfer/chain/source-modifier combinations remain partial |
| Vermilion Fan | 4 | Optional normal Slash to fire; nature against Vine regression | Full virtual-source/Fan trigger ordering remains partial |

## Armor / departure / public card ownership

Eight Trigrams response and virtual dodge; Renwang black/normal and elemental counterexamples; Vine normal Slash and AOE immunity/fire increase; Silver Lion damage cap and departure recovery are backed by existing actual effect and related regressions. Silver Lion leaves through MilitaryMoveService and schedules ordinary RecoverAction, so full-HP/dead behavior comes from the previously audited recovery service, not a direct HP mutation.

Replacement, Snatch/Dismantlement, skill discard, Duodao, Zhiyan and death use the authoritative CardMove zones. Existing card-move regression checks single ownership, public discard/private acquisition, equipment exchange and departure facts. No direct equipment dictionary overwrite introduced. Special discard reservations remain under the prior CardMove contract; this batch does not claim all equipment-nullification/Silver Lion multi-trigger priorities are closed.

## P0 God Zhang Liao and skill sources

For each of four actual slots, real Duorui action pays that slot, moves current gear through CardMove, publishes abolished state and immediately loses weapon range/horse modifier. Abolished use is rejected before consuming new hand equipment. Snapshot retains abolished set and borrowed request; every viewer projects the same public equipment/slots. Restore slot then equip succeeds with exactly one authoritative instance.

Existing Zhang Liao regressions included: target turn end; non-repeat during active lease; all-slots-abolished no-cost branch; Silver Lion loss recovery; target death; borrower death and victim suppression lifetime; permanent suppression not restored by expiry; earlier/Fuhun grant sources survive lease removal; native/lord/limited/awakening/special eligibility; Zhiti wounded opponent and actual range; pindian victory vs tie; Duel result from either side; range-based hand penalty and legacy projection default.

Runtime skill sources are distinct: native catalogue, grant_sources, active transformation, lease suppression, and **implicit equipment source by current physical zone**. Equipment effects/quota/range are dispatched from the equipped instance; they are not installed into granted_skills and their departure never deletes native or temporary same-purpose grants. Crossbow departure preserving native Paoxiao is demonstrated. A general-purpose grant for an arbitrary equipment skill ID is not currently an implemented registry feature; no fake source entries or unrelated ownership framework were introduced.

Duorui and Zhiti remain BLOCKED for the complete borrowing classification/compound-skill lifecycle and simultaneous trigger-order closure. Four-slot P0 mechanics passing is not a reason to approve the whole skill.

## AI, UI and reconnect

AI receives authoritative legal play targets/options; test forbids the abolished weapon and only permits adjacent Slash targets with no weapon. Horse-dependent reach changes weapon value, existing superior weapon prevents low-value replacement, armor has a positive survival value. These are deterministic targeted checks, not a new large AI stress run.

Web GamePage regression shows hand offensive horse -1, equipped defensive horse +1, and authoritative abolished weapon slot. Desktop uses the same signed label for card face, hover preview and compact equipped token; empty slots explicitly show +1/-1. No artwork regenerated. Projection defines public gear by authoritative zone; all viewers agree after abolition. Save/restore tests cover replacement departure request, second Ice Sword choice, Axe/weapon geometry, abolition/restore, Crossbow source authority, Green Dragon processing/borrowed material, and distance changes. Existing submit validation checks skill discard costs; no new UI-only permission state.

## Classification and verification

Test issues: initial Qicai test accessed nonexistent GameSession.rules; corrected to real MilitaryTrickRule and re-ran the OLD code path to preserve a true rule failure (equipment_qicai_reproduction.log). The combined modifiers log retains the fixture failure separately from true Qiangxi failure. Native Pang De was first guessed with the wrong ID, corrected to authoritative roster-derived Mashu parameters. These are not product bugs. Development temporarily missed CardUsedEvent import for R61; repaired before checkpoint and not counted as baseline defect. Old Kylin test name said "after_damage" but checked only final horse/HP; minimal timing tests now provide the actual timing evidence.

Final equipment_distance_targeted.log: **385 passed in 3.23s**, 17 selected Python files; includes 44 new shared-system cases plus 2 desktop presentation cases, and 2 new scoped AI cases within the 44. Do not sum intermediate 48/71/228/384 or 99 counts. equipment_distance_web.log: **36 passed**, one GamePage Vitest file. The extra nonexistent interaction.test.ts filter selected no file; it is not counted as passed. Existing jsdom canvas warnings did not fail tests.

Nine changed worker engine/model/projection mirrors byte-identical; scoped synchronization only, not the final Worker mirror gate. git diff --check passed before code checkpoint. No Zuo Ci Huashen 795 suite, full pytest, final seven gates, roster/art expansion or deployment. Only five BLOCKED rows closed, below 30-50 cadence; public changes remain localized equipment consumers and explicit provider mode with broad related regression, so no mid-audit full pytest required this batch. No RC issued.

## Dependency exit ledger

| General | Skill | Exit | Remaining boundary |
| --- | --- | --- | --- |
| guanyu | wusheng | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| zhaoyun | longdan | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| machao | mashu | PASS | Closed continuous modifier contract |
| huangyueying | qicai | FIXED | Closed continuous modifier contract |
| daqiao | liuli | BLOCKED | Shared post-cost geometry tested; full TargetSpecified/TargetConfirming combinations remain unverified. |
| luxun | lianying | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| sunshangxiang | xiaoji | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| wind_xiahou_yuan | shensu | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| wind_huang_zhong | liegong | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| wind_wei_yan | kuanggu | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| wind_zhang_jiao | guidao | BLOCKED | Equipment material movement checked; same-owner retrial order remains BLOCKED. |
| wind_god_guanyu | wushen | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| wind_god_guanyu | wuhun | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| fire_dian_wei | qiangxi | BLOCKED | Post-weapon-cost independent range fixed; full active cost/HP/damage/phase boundary closure remains unverified. |
| fire_xun_yu | quhu | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| fire_wolong | bazhen | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| fire_taishi_ci | tianyi | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| fire_pang_de | mashu | PASS | Closed continuous modifier contract |
| forest_xuhuang | duanliang | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| forest_jia_xu | luanwu | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| forest_god_caocao | feiying | PASS | Closed continuous modifier contract |
| forest_god_lvbu | wuwei | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| forest_god_lvbu | shenfen | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_zhang_he | qiaobian | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_deng_ai | tuntian | BLOCKED | Field movement and distance dependency checked; multiple FinishJudge ordering remains BLOCKED. |
| mountain_jiang_wei | tiaoxin | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_sunce | jiang | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_zhang_zhaozhang | zhijian | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_zuoci | xinsheng | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_cai_wenji | beige | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_god_zhaoyun | juejing | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| mountain_god_zhaoyun | longhun | BLOCKED | Shared response provider regression passes; full dynamic HP/material count and ownership lifecycle closure outstanding. |
| yj2011_yu_jin | yizhong | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2011_fa_zheng | xuanhuo | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2011_ling_tong | xuanfeng | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2011_wu_guotai | ganlu | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2011_chen_gong | mingce | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2011_gao_shun | xianzhen | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2012_cao_zhang | jiangchi | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2012_ma_dai | mashu | PASS | Closed continuous modifier contract |
| yj2012_ma_dai | qianxi | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2012_han_dang | gongqi | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2012_han_dang | jiefan | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_cao_chong | renxin | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_jian_yong | qiaoshui | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_liu_feng | xiansi | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_pan_zhang_ma_zhong | duodao | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_yu_fan | zongxuan | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_yu_fan | zhiyan | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_zhu_ran | danshou | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_fu_huanghou | zhuikong | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| yj2013_fu_huanghou | qiuyuan | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| shadow_god_liubei | longnu | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| shadow_god_luxun | zhanhuo | BLOCKED | Shared equipment/cost/range dependency evidence only; full independent skill clauses outstanding. |
| thunder_god_zhangliao | duorui | BLOCKED | Four-slot cost, geometry, rejection, restore, source-scoped lease and death baseline regressions pass; complete native/compound borrowability and overlapping turn/death/source effects remain unverified. |
| thunder_god_zhangliao | zhiti | BLOCKED | Range-based hand penalty and three restore events have existing regressions; complete ordering with equipment departure and other simultaneous damage/pindian/duel triggers remains unverified. |
| 动态授予/附属 | jixi | BLOCKED | Shared distance after field cost checked in existing consumers; complete ViewAs/target and simultaneous trigger closure outstanding. |

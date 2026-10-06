# T18A.11 shared use / response / ViewAs audit

Checkpoint base: 1e81f90. This is a system audit in progress, not release approval.

## Scope and source

Blocked ViewAs rows at entry: wusheng, qingguo, longdan, qixi, guose, jijiu, guhuo, wushen, lianhuan, huoji, shuangxiong, duanliang, jiuchi, longhun, fuhun, lihuo, jixi (17).
Other blocked consumers of use/response events and legality: hujia, jijiang, wushuang, paoxiao, tieqi, liegong, jizhi, wumou, keji, jinjiu, jiangchi, longyin, qiaoshui, jingce, shensu, luanwu, qiuyuan. These remain in the system queue; auditing one dependency does not close every consumer.

Project locks: docs/t17/final_version_lock.md, version_matrix.md, current character catalogue. Auxiliary historical source: Mogara/QSanguosha-v2 revision e8768851bd8054db9fd1b63cd6f1feca813590d7.
Source URLs:
- https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/src/package/standard-generals.cpp
- https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/src/package/nostalgia.cpp
- https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/src/package/fire.cpp
- https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/src/package/thicket.cpp
- https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/src/server/room.cpp

Hashes are recorded in existing sources/aoe/judgment source notes. The historical repository is community evidence, not an official publisher card archive. Only read source clauses; no external implementation copied.

## Classification

| Category | Evidence / disposition |
| --- | --- |
| Correct implementation, previously unverified | Qingguo black hand only, Jink pattern, suppression, numbered responses, cost cleanup and snapshot restore; close PASS |
| Version difference | Modern Guose in standard-generals.cpp adds a draw; project classic uses NosGuose in nostalgia.cpp without it. Do not upgrade. Wushen filter versus project optional representation still requires full version/identity audit; do not silently change or close |
| Test problems | Initial missing LonghunUseAction import and reversed LonghunUse arguments were fixture errors, not bugs. Corrected Longhun fixture independently rerun against 1e81f90 and failed for the real limit bypass |
| Product bug | R32 ViewAs use-limit bypass; R33 elemental Slash omitted from Longdan; R34 response-number defaults; R35 two materials emitted as two responses; R36 Longdan stale target submission failed to recheck skill |
| Still unverified | Multi-target view-as Slash, full Guhuo declarations/challenges, Longhun source and HP cardinality, delayed-transform lifecycle, Shuangxiong judgment stage, Jixi private pile/distance, Lihuo HP cost and event consumers |

## Public implementation

card_limits.validate_view_as_limits validates living actor, owner play phase, usage owner/turn, effective skill, final-card Qiaoshui and Qianxi limits before costs. It is called by standard, Fire, Forest and God view-as actions. Recast retains its separate exception.
response.longdan_materials normalizes all effective Slash prints for both actual response and method-none dodge gifts.
MilitaryResponseHandler._record_material_response propagates current response_number/response_total consistently across material response paths.
Spear/Fuhun validate both materials before a batch HAND -> PROCESSING -> DISCARD response payment and emit one response for the virtual Slash.

## Evidence and current closures

tests/test_t18a11_view_as_system.py: 40 deterministic audit cases. Each affected root has a failing reproduction log before repair (Longhun and Lianhuan corrected cases independently rerun against the original checkpoint).
view_as_system_targeted.log: 279 passed, including existing response, Qianxi, Fuhuanghou, standard modifiers, recast, Fire/Forest/God tests. Earlier narrower 220/107/113 batches are not added to this count.
Closed: Qixi, Guose, Jijiu, Huoji, Lianhuan FIXED; Qingguo PASS.
Wusheng/Longdan keep BLOCKED for multi-target/cost-range limits despite shared repairs. Other listed consumers still require remaining source and boundary checks.

No Huashen 795 suite, final full gates, artwork, roster expansion or deployment. This clears 6 of 181 blocked rows, below the requested 30–50-row full-pytest checkpoint interval.

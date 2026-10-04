# T17B 当前开发 checkpoint（未完成）

日期：2026-10-04。T17A.1 checkpoint：8ce827d。最终版本38/38 LOCKED、未解决武将版本0；来源仍为固定revision社区档案，官方卡面未验证。

**T17B YJ2011 尚未完成。当前仅Tier 1/Tier 2五将接入并专项验证；不是11/11 PASS，不是production 76，不是T17B complete checkpoint。**

## 最终版本锁定

- 张春华：经典OL/身份局绝情、伤逝，伤逝补至全部已损失体力，无2张上限。
- 钟会：2012经典权计、自立、排异，单觉醒。
- 刘表：修订经典自守、宗室，势力数多摸牌、本回合出牌阶段不能指定其他角色。
- 神刘备：经典6 HP龙怒、结营。
- 神陆逊：经典军略、摧克、绽火。
- 神甘宁：经典魄袭、劫营，初始3/max6，营体系。
- 神张辽：经典夺技能夺锐、止啼，废装备栏、临时获得与原主失效；排除后期OL仅失效版。

## 当前逐将状态

| General ID | 武将 | HP / 势力 | 技能 | 引擎专项状态 | AI | Multiplayer / Reconnect | Tests |
| --- | --- | --- | --- | --- | --- | --- | --- |
| yj2011_zhang_chunhua | 张春华 | 3 / wei | 绝情、伤逝 | 已实现、targeted PASS（最终验收仍待） | 通用AI/专项heuristic，40局当前阵容通过 | 当前快照/相关私有请求已测，完整双真人验收未完成 | tier1/tier2/integration |
| yj2011_yu_jin | 于禁 | 4 / wei | 毅重 | 已实现、targeted PASS（最终验收仍待） | 通用AI/专项heuristic，40局当前阵容通过 | 当前快照/相关私有请求已测，完整双真人验收未完成 | tier1/tier2/integration |
| yj2011_cao_zhi | 曹植 | 3 / wei | 落英、酒诗 | 仅开发metadata，技能未实现 | 未完成 | 未完成 | 仅metadata/fallback验证，无技能规则测试 |
| yj2011_fa_zheng | 法正 | 3 / shu | 恩怨、眩惑 | 仅开发metadata，技能未实现 | 未完成 | 未完成 | 仅metadata/fallback验证，无技能规则测试 |
| yj2011_ma_su | 马谡 | 3 / shu | 心战、挥泪 | 仅开发metadata，技能未实现 | 未完成 | 未完成 | 仅metadata/fallback验证，无技能规则测试 |
| yj2011_xu_shu | 徐庶 | 3 / shu | 无言、举荐 | 已实现、targeted PASS（最终验收仍待） | 通用AI/专项heuristic，40局当前阵容通过 | 当前快照/相关私有请求已测，完整双真人验收未完成 | tier1/tier2/integration |
| yj2011_ling_tong | 凌统 | 4 / wu | 旋风 | 已实现、targeted PASS（最终验收仍待） | 通用AI/专项heuristic，40局当前阵容通过 | 当前快照/相关私有请求已测，完整双真人验收未完成 | tier1/tier2/integration |
| yj2011_xu_sheng | 徐盛 | 4 / wu | 破军 | 已实现、targeted PASS（最终验收仍待） | 通用AI/专项heuristic，40局当前阵容通过 | 当前快照/相关私有请求已测，完整双真人验收未完成 | tier1/tier2/integration |
| yj2011_wu_guotai | 吴国太 | 3 / wu | 甘露、补益 | 仅开发metadata，技能未实现 | 未完成 | 未完成 | 仅metadata/fallback验证，无技能规则测试 |
| yj2011_chen_gong | 陈宫 | 3 / qun | 明策、智迟 | 仅开发metadata，技能未实现 | 未完成 | 未完成 | 仅metadata/fallback验证，无技能规则测试 |
| yj2011_gao_shun | 高顺 | 4 / qun | 陷阵、禁酒 | 仅开发metadata，技能未实现 | 未完成 | 未完成 | 仅metadata/fallback验证，无技能规则测试 |

## 实现与原语审计

未新增engine primitive。原有LoseHpAction已能完整表达绝情的体力流失和无来源dying/death，所以只在伤害开始前接入集中技能处理，不以amount=0再伪造伤害。无言也是伤害前取消。集中逻辑位于engine/yj2011.py；未在Web写规则。

复用ResolutionStack、PendingRequest/Decision、CardMoveService、DrawCardsAction、LoseHpAction、RecoverAction、TurnoverAction、现有Damage/Dying/Death、snapshot编码及Projection。没有加入新temporary zone、equipment transaction、ownership或pindian modifier；这些仍是后续Tier3工作。

- 绝情：父damage返回0（未造成伤害），先推LoseHpAction；其后不进入任何damage触发、伤害防具、横置解除或铁索传播。行动审计事件保留原source与amount，LoseHpAction的dying source为None，不产生伤害击杀奖励。火/雷/普通、濒死重连与反贼奖励均有测试。
- 伤逝：手牌/HP/maxHP事件后仅检查受影响拥有者；补至maxHP-HP，无封顶；自身补牌后重检、不递归。lost HP 0/1/2/3/4及不同手牌数有参数化测试。
- 毅重：效果无效而非目标非法；无防具黑色普通/火/雷杀免疫，红色和虚拟无色杀正常；青釭不能禁掉技能，有实际防具则不免疫。
- 破军：严格使用锁定的伤害后摸X再翻面版，X=min(当前HP,5)，濒死完成后目标仍活才询问；非杀、传导伤害不错误触发。不实现其他版本的扣置区。
- 无言/举荐：防止锦囊伤害，包括所锁定原文覆盖的延时锦囊；结束阶段弃非基本牌、选择其他角色，再由受益者选择摸2/回复1/解除横置并翻正；成本与翻面复用通用动作。
- 旋风：实际CardMovedEvent的装备离开触发，覆盖全部移动reason与弃牌/他人获得；弃牌阶段按精确阶段批次累计至少2张。两次弃牌选择逐次通过PendingRequest；隐私使用现有room opaque hand mapping。
- 初始化反应游标：发牌及初始星区完成后将事件游标移至当前，避免后来HP变化把旧初始发牌事实重新当作新技能窗口。

## AI、Projection、重连和客户端

AI集中在decisions/yj2011.py。伤逝需要补牌就发动；破军按公开HP/朝向与公开身份估计翻面收益；举荐按队友受伤/朝向选目标和收益；旋风选择敌对目标、优先公开装备，否则按不透明候选位置选手牌。隐藏手牌内容改变后旋风AI Decision不变的测试通过。低复杂度技能复用现有AI。

多人已测：5/8人房间中旋风private card request的opaque payload、mid-request room snapshot恢复、合法timeout；当前engine技能请求与dying中途snapshot恢复。**完整2 human+AI Military Five/Eight、真实断线timeout端到端及六名未实现技能均未验收。** 不把序列化检查描述为全部多人PASS。

PySide：11名开发metadata均能加载并取得可读fallback portrait；技能中文名和完整说明可解析。现有Qt回归在full pytest中执行。新技能的完整人工PySide交互尚未验收。

Web：未更改T16 UI/T15 portrait；生产catalog仍65，不开放新将。核心interaction suite两处旧.player-heading点击定位换成当前已有.portrait-button，原目标/Decision断言不变；不是修改UI行为。完整新将选将与tooltip将在生产gate通过后验收。

## 验证结果

- T17A.1 validate_catalog.py --self-test：PASS，38 LOCKED，0 QUESTION，69技能，10反向变异拒绝；两个备用原文从bd14d40已有档案独立保留在source_excerpt.json，不提升官方证据等级。
- T17B专项：89 passed（tier1 25、tier2 45、integration 19）。
- 当前5名开发武将强制AI完整对局：40局，Military Five/Eight各20；全部victory，最多130回合，40/40在技能请求中途snapshot恢复，无未完成请求。详细结果见ai_current_results.json。该结果不代表11/11验收。
- 完整pytest：843 passed、1 failed，65.34秒。唯一失败test_t10_v3_integration.py::test_all_playable_v3_portraits_are_live_and_readable，wind_zhang_jiao哈希。
- 已直接从git bd14d40取资产及旧验收JSON证明该失败在基线存在：实际8ef77088bb09ef8190a4b6cdb71deb9cc94c060e63d8d9cf3da474886b41850d；旧验收74d22003e5d36227ae4600c50228344c5ee29220e494027ded20aa45439424d2。未修改图片或旧T10验收记录；生产gate如何处理已请求用户裁定。
- Vitest：14 test files / 67 tests PASS。
- TypeScript：npx tsc -b PASS。
- Vite：npx vite build PASS。
- Playwright：核心interaction_reliability最终17/17 PASS（26.2秒）。使用本地CLOUDFLARE_ROOMS=1房间mock；两处旧.player-heading点击定位更新为现有.portrait-button，保留原目标、ACK和单次提交断言。Durable Object诊断用例因无本地DO服务跳过，未将其记为PASS。补充T16.2 fixture曾因上一个套件结束关闭服务而连接拒绝，未将其记为产品失败或通过；无需要的T16视觉snapshot重跑。
- Cloudflare game-room本地副本与authoritative source同步；一致性测试PASS。未执行deploy。

## 剩余工作与生产门槛

1. 按Tier3完成曹植落英/酒诗、法正恩怨/眩惑、马谡心战/挥泪、吴国太甘露/补益、陈宫明策/智迟、高顺陷阵/禁酒。不要把metadata视为已实现。
2. 泛用equipment exchange transaction等原语只有在现有能力无法表达时新增；并完成每将正反例、时序、dying/death、mid-skill reconnect与私有Projection测试。
3. 全部11将专项AI、强制包含随机完整对局、真实双真人5/8人、断线timeout及客户端验收。
4. 全部回归门槛达成、基线美术失败得到裁定后，才一次性production65→76。当前不开放任何2011新将，2012/2013/四神更不开放。

T17B ENGINE TARGETED IMPLEMENTED: 5/11。T17B FINAL ACCEPTANCE: NOT COMPLETE。TOTAL PRODUCTION ROSTER: 65。未创建T17B complete checkpoint。

本checkpoint没有新美术、没有公网部署、没有开始T17C。原6个T11 untracked dirs保持原样。仅提交本任务代码、必要核心测试、本地Worker镜像和T17文档；temp日志、测试产物不提交。

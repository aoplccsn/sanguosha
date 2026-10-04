# T17B complete checkpoint

2026-10-04；基线：6862b75（T17B 五将内部 checkpoint）、8ce827d（T17A.1 FINAL VERSION LOCK）。本报告所在提交为 `T17B complete checkpoint`，最终提交 SHA 在交付消息中报告。

**T17B YJ2011：11/11 PASS。FULL PYTEST：1014 passed，0 failed。PRODUCTION ROSTER：76。**

## 11 将与规则

| 武将 | 技能 | 结果与实现 |
| --- | --- | --- |
| 张春华 | 绝情、伤逝 | PASS；保留已有实现，体力流失替代伤害与已损体力补手专项回归通过。 |
| 于禁 | 毅重 | PASS；保留已有实现，黑杀效果无效与装备条件专项回归通过。 |
| 徐庶 | 无言、举荐 | PASS；保留已有实现，锦囊伤害防止与结束阶段请求回归通过。 |
| 凌统 | 旋风 | PASS；保留已有动作；仅补充原子交换批次适配，多槽交换一次离装批次只触发一次旋风。 |
| 徐盛 | 破军 | PASS；保留已有伤后摸牌与翻面动作，中途恢复回归通过。 |
| 曹植 | 落英、酒诗 | PASS；从正式 CardMovedEvent / 判定事实建立梅花候选，重检仍在弃牌堆；使用/响应和 SYSTEM 死亡清理不触发。酒诗复用 TurnoverAction 和虚拟酒，主动酒次数合法性、自救、扣 HP 前朝向快照及濒死结算后的翻正均验证。 |
| 法正 | 恩怨、眩惑 | PASS；按同一次获得、同一他人来源统计 ≥2，跨手牌/装备来源区不拆成两次；伤害按每点询问。眩惑替代正常摸牌，由法正选受益者和受益者攻击范围内目标；实体杀经 forced UseCardAction，否则依次私选至多两牌后一次获得。 |
| 马谡 | 心战、挥泪 | PASS；手牌 > maxHP 才可一次 PLAY 使用心战；顶三张进入 committed 私有正式区，可取红桃并公开，剩余按选择顺序归顶。挥泪在 death pipeline 中弃合法存活他人杀手的手牌/装备，先于反贼奖励与胜负检查；绝情无伤害来源死亡不触发。 |
| 吴国太 | 甘露、补益 | PASS；依次选择两名合法角色，数量差 ≤ lostHP，所有槽验证后原子交换，移动事实/银狮/枭姬/旋风/屯田复用。补益在 dying pipeline 内逐所有者询问，选一张濒死者背面手牌后只公开此牌；非基本弃置并恢复1，基本仅展示。 |
| 陈宫 | 明策、智迟 | PASS；装备/杀正式交牌，指定受赠者范围内目标，再由受赠者选择虚拟普通杀或摸1；复用完整 SlashSequence。智迟回合外实际受伤后建立本回合效果无效标记，杀/非延时锦囊后续效果无效，回合结束对所有玩家清理。 |
| 高顺 | 陷阵、禁酒 | PASS；正常 Pindian 及私选公开；胜利绑定 source/target/turn，距离、防具、杀次数豁免只对该目标；平局/输绑定禁杀。实体/虚拟杀使用共享记账，豁免目标不占普通额度。禁酒由权威用牌/响应解释酒为普通杀，禁酒不提供酒自救，投影展示合法杀身份而不改物理牌定义。 |

技能文本读取 `roster.md`、`version_matrix.md`、`mechanic_matrix.md`、`request_design.md`、`implementation_order.md`；版本服从 T17A.1 固定修订。未宣称社区档案经过发行方核验。

## 通用能力、AI 与信息边界

- `EquipmentExchangeTransaction` / `CardMoveService.exchange_equipment`：全批验证、整批槽提交后再发布移动事实和离装批次；非法事务不修改牌区、事件或反应队列。
- `CardMoveService.obtain_cards`：跨区但同一来源的获得保留一次获得批次，避免恩怨漏触发或混合来源错误合并。
- `AuthorizedVirtualUse`：技能授权的无实体普通杀，复用攻击范围/目标合法性、CardUsedEvent、SlashSequence、闪响应和伤害管线。
- `record_slash_use` 与 turn-scoped 标记：实体及丈八/武圣/龙胆/激将/武神/龙魂路径共享陷阵目标次数语义；结束回合统一清理。
- 六将 AI 根据自身牌、公开装备、公开血量/朝向、公开敌友收益选择。甘露按装备价值和数量选择正收益交换；陷阵根据己方高点牌和可攻击对象；明策/眩惑选受益者与攻击对象；酒诗/心战具基础使用价值判断。
- 隐藏敌方手牌只按背面候选位置选择；不读取其定义/点数。眩惑与补益的 AI 隐藏牌内容变换不变性专项通过。
- `committed:xinzhan` 只对合法所有者显示内容；眩惑/补益继续通过 room opaque hidden-hand 映射。公开展示事件仅含选中牌的牌名、花色、点数，不广播完整隐藏手牌。
- Snapshot 保留动作、frame、候选、request_id、选择、私有区、暂存反应、turn 标记；落英/酒诗/恩怨/眩惑/心战/甘露/补益/明策/拼点均有中途恢复覆盖。

## 验证与生产 gate

| 项目 | 结果 |
| --- | --- |
| Existing five regression | 89 passed；未重写五将。 |
| 六将专项 | 52 passed，另有共享边界 11 passed。 |
| T17B aggregate | 259 passed（含生产目录、80局AI、房间、PySide）；来自最终 JUnit 实际计数。 |
| 专用 full-game AI | Military Five 40 + Military Eight 40；轮换强制覆盖全部11将；技能请求中恢复后继续，均完成 victory、无残余 PendingRequest/stack/回合标记。 |
| Multiplayer / reconnect | 16 项双真人+AI五人/八人房间用例，token 重连、opaque 候选、request/frame、截止时间、拼点、濒死、装备交换及真实超时；另外 TCP、relay、FastAPI WebSocket 旧整局回归全部通过。 |
| PySide | 六将 load/中文技能描述/通用请求 fallback 6/6 PASS；全量 Qt 回归通过；无 T16 布局改动。 |
| Preproduction full pytest | 1003 passed，0 failed，生产池仍为65。通过后一次开放全部11将。 |
| Final full pytest | 1014 passed，0 failed；包含生产76目录、五人/八人实际 draft 和 AI 选择覆盖。 |
| Vitest | 67 passed。 |
| TypeScript | `npx tsc -b` PASS。 |
| Vite | `npx vite build` PASS。 |
| Playwright core | `interaction_reliability.spec.ts` 17/17 PASS；本地 CLOUDFLARE_ROOMS=1。 |
| Python/Web/Cloudflare | 76 playable/implemented；普通68+神8；19个2011技能；副本一致性回归通过。 |
| Portrait fallback | 全部11将使用既有默认 Web 立绘和 PySide fallback；未生成新美术。 |

扩大选将池后旧固定种子覆盖变化：神将开关测试 seed2 不再在首份候选抽到神将，改为 seed0；四组网络烟测由 `[0,1,2,3]` 改为 `[4,1,2,3]`，保留四种确定性对局及每名真人必须收到玩法请求的原断言。原 seed0 的部分席位可在首次玩法请求前死亡，整局正常完成；没有改产品规则去延缓死亡，没有删减去重/隐私/胜负断言。Web 消息隐私审计对应移动到两真人 seed4。

## 张角 hash 与资源保护

- 失败测试：`tests/test_t10_v3_integration.py::test_all_playable_v3_portraits_are_live_and_readable`。
- 校验文件：`assets/generals/qun/wind_zhang_jiao.png`，为 static Master/fallback PNG；不是 MP4、optimized WebP 或动态资源。
- T10 原期望：`74d22003e5d36227ae4600c50228344c5ee29220e494027ded20aa45439424d2`。
- 当前/T15 SHA：`8ef77088bb09ef8190a4b6cdb71deb9cc94c060e63d8d9cf3da474886b41850d`。
- 根因：T15 `7cc5996` 接入用户动态 Master 时，按 `--static-from-first-frame` 正式生成静态 fallback；该提交的 PNG 字节 SHA 与当前文件、`docs/t15/media_report.json` 完全一致。T16 报告也明确旧 T10 expectation 已过时。
- 修正：保留 T10 原始审计记录及最终历史 hash 一致性断言；测试明确引用 T15 accepted static SHA，并继续验证当前资产 SHA、可解码、资源解析、尺寸与不同立绘唯一性。没有 skip/xfail/删测试或恢复旧资源。
- 全部 assets/portraits MP4 的起止 SHA 相同（数量见 `t17b_complete_results.json` 和 baseline），包括张角 runtime/panel MP4；没有修改、删除、重新编码或移除。
- `git diff -- assets docs/t11 web/src web/e2e` 无差异；原有6个T11未跟踪目录保留。没有 reset、制作新美术、修改动态立绘或 T16 UI。

## 交付与停止边界

生产 roster = 76；历史57/65常量保留供先前美术与包审计。所有当前产品 registry、目录与 multiplayer draft 使用完整生产池；2012/2013与新四神未加入。

本地 checkpoint：`T17B complete checkpoint`。提交仅包含本任务源代码、同步引擎、测试和验收证据；没有提交原有6个未跟踪素材目录、临时素材、源MP4或无关T16变更。提交后 tracked files clean，未跟踪仅原有6个T11目录。

Remaining issues（本轮范围）：0。公网部署未执行；Cloudflare 本轮验证是权威副本一致性、本地共享规则与核心交互，不宣称已部署的公网DO验收。完成T17B后停止，不开始T17C。

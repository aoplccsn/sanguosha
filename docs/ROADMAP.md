# 开发路线图

每阶段只在前置阶段 PASS 后开始。表中“禁提前”指本阶段不得抢做的后续能力；已有基础接口可预留，但不写具体效果。所有阶段都遵循核心无 Qt、状态统一写入、固定 RNG 和 pytest 回归。

| 阶段 | 目标 | 修改范围 | 关键接口 | 测试与 PASS 条件 | 禁提前 |
|---|---|---|---|---|---|
| T1 | 骨架与纯数据 | `pyproject.toml`、`src/sanguosha/model`、fixture | State、Player、CardDefinition/Instance、ZoneRef、RNG 协议 | 固定初态/牌堆、唯一牌位、包可导入 PASS | 结算、卡牌效果、UI |
| T2 | 事件、动作、结算 | `engine`、日志协议 | Command/Action、EventBus、Frame、PendingRequest、Decision、advance/submit | WAIT/恢复/取消/嵌套三种合成场景、重复决定拒绝 PASS | 具体牌与技能 |
| T3 | 回合阶段 | `systems/turn,phase` | PhaseFrame、阶段跳过/额外回合队列 | 阶段顺序、跳过、额外回合和多行动 PASS | 真实卡牌效果 |
| T4 | 基础牌 | `content/cards`、基础响应 | UseCard、RespondCard、基础效果 | 杀闪桃酒及属性杀基本流程、牌位 PASS | 锦囊、完整军争连环 |
| T5 | 单机可玩版：GUI、AI、基础身份局 | `ui/`、`decisions/`、摸弃牌、濒死死亡与身份 | GameSession、Decision、TurnAction、CardMoveService | 五人桌面操作、AI 自动决策、整局终局、GUI smoke PASS | 完整军争牌堆、距离装备与武将技能 |
| T6 | 普通锦囊 | 普通锦囊效果与反制窗口 | TrickTargetFrame、NullificationWindow | 单/多目标、无懈链、借刀/五谷等逐项规则案例 PASS | 延时锦囊、武将技能 |
| T7 | 判定延时锦囊 | `systems/judgment`、延时锦囊 | JudgmentFrame、RetrialRequest | 乐/闪电/兵粮、连续改判与牌归属 PASS | 属性连环、武将技能 |
| T8 | 属性伤害与铁索 | `systems/damage`、军争牌 | DamageContext、chain propagation | 火/雷传播、循环阻断、嵌套濒死接口 PASS | 身份完整终局、技能 |
| T9 | 濒死死亡身份 | `systems/dying,identity` | DyingFrame、DeathFrame、VictoryResult | 求桃嵌套、死亡清理、全部身份奖惩/胜负 PASS | 武将技能、AI |
| T10 | 完整牌堆数据 | `data/`、牌定义清单 | ruleset_id、deck loader | 逐张花色点数/数量与选定版本核对、唯一实例 PASS | 技能、AI |
| T11 | 技能框架 | `systems/skill`、测试技能 | Trigger、Modifier、ViewAs、ActiveSkill | 合成锁定/触发/主动/转化/限制/修正技及顺序 PASS | 正式武将技能 |
| T12 | 魏标准武将 | `content/skills/wei` | 注册处理器 | 七人原版文本逐条场景与回归 PASS | 蜀吴群、AI |
| T13 | 蜀标准武将 | `content/skills/shu` | 同上 | 七人原版文本逐条场景与回归 PASS | 吴群、AI |
| T14 | 吴标准武将 | `content/skills/wu` | 同上 | 八人原版文本逐条场景与回归 PASS | 群、AI |
| T15 | 群标准武将 | `content/skills/qun` | 同上 | 三人原版文本逐条场景与回归 PASS | AI、GUI |
| T16 | 基础 AI | `decisions/ai` | DecisionProvider | 同一请求接口，合法决策、完整无界面局 PASS | GUI 规则逻辑 |
| T17 | PySide6 GUI | `ui/` | StateProjection、RequestView、submit | 真人可完成所有请求、无状态直写/信息泄漏 PASS | Windows 打包 |
| T18 | 五人人机局 | 集成、交互完善 | session lifecycle | 单真人四 AI 多局至合法终局、无悬空帧 PASS | 打包 |
| T19 | 回归与规则补全 | 测试/内容修正 | 规则版本案例库 | 全牌/全将/身份/嵌套场景回归，已知规则差异清零 PASS | 新扩展 |
| T20 | Windows 打包 | 构建配置、资源路径 | EXE 入口 | 干净 Windows 环境启动、完成一局、测试报告 PASS | 风火林山等扩展 |

阶段顺序可因实现依赖调整，但不能降低各 PASS 条件。T0 只交付文档，不执行 T1。

T2：PASS（2026-09-28）。显式帧、统一决策入口、三级嵌套及三类 mock 场景已由 pytest 验证；T3 已完成。


T3：PASS（2026-09-28）。标准六阶段顺序、显式子帧、出牌操作循环、跳过阶段、存活座次查找已通过测试。路线图 T3 行原列出的复杂额外回合队列未在本阶段实现，遵循 T3 任务明确的“暂不实现复杂额外回合”；后续阶段需单独安排该能力。


T4：PASS（2026-09-28）。本次明确范围为普通杀、闪、桃及必要的移动、伤害、回复和响应基础设施。路线图表格早期列出的酒与属性杀留待后续单独阶段；未提前实现 T5 距离和装备。


T5 范围按新需求调整为“单机可玩版：GUI + AI + 完整基础身份局循环”，取代原路线图表格中的“距离装备”目标，并提前整合原 T9/T16–T18 的基础身份、AI 和界面能力。T5 只使用杀、闪、桃临时牌堆；距离、装备、锦囊、军争扩展与技能仍待后续阶段，不据此视为已实现。


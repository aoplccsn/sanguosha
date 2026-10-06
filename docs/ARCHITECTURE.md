# 架构设计

## 依赖方向与目录

预期 `src/sanguosha/`：`model/` 放纯数据与标识；`engine/` 放命令、结算帧、事件、请求、状态协调；`systems/` 放回合、阶段、移动、卡牌、技能、规则、距离、装备、伤害、判定、濒死、身份；`content/cards/`、`content/skills/`、`content/characters/` 放注册定义与效果；`data/` 放牌堆/武将清单；`decisions/` 放 Provider 协议及后续 AI/脚本适配；`ui/` 放 PySide6；`logging/` 放结构化记录。`tests/` 与 `src/` 平级。核心接口由 `model`/`engine` 定义，具体内容依赖核心接口，核心不能 import 具体技能、牌或 UI；在组成根注册内容，避免循环依赖。

`GameEngine` 仅作公开入口与事务协调：接收 Command/Decision、检查状态版本、驱动栈到下一请求或终态、返回只读可见投影与日志增量。它委派独立系统；不含逐张牌/逐个武将的条件分支。`GameState` 是身份、玩家、区域、回合游标、栈、待答请求、随机状态引用、版本的权威数据容器；状态写入只由受控 Effect/系统完成。`TurnManager` 只安排回合/阶段帧，卡牌效果在注册执行器中。

## 核心数据契约

| 类型 | 关键字段/约束 |
|---|---|
| `PlayerState` | id、座次、身份及公开状态、武将 id、体力/上限、存活、横置/翻面、区域引用、回合计数/标记；不持有规则方法 |
| `CardDefinition` | 名称/类别/子类/属性/装备槽/范围/目标及效果注册 key；可由数据加载，复杂效果由代码实现 |
| `CardInstance` | 全局唯一 id、definition id、花色、点数；同名牌互为独立实体。位置只记录在 `GameState.zones`，不在实体牌上重复保存 |
| `CharacterDefinition` | id、阵营、体力上限、技能 id 列表、主公技标识等静态数据 |
| `SkillDefinition` | id、技能类别、订阅事件/窗口、发动条件、优先级、处理器 key；动态使用次数/标记在状态 |
| `ZoneRef` | 区域类型、玩家 id/槽位/特殊区 key；每张实体牌恰好有一个位置 |
| `CardMove` | 移动 id、牌 id 列表、逐张旧/新区、原因、行动者、公开信息；先验证再原子提交并发 `CardMoved` |
| `DamageContext` | 来源可为空、目标、数值、普通/火/雷、牌/技能/动作来源、传播链 id、是否已传播、防止/修正记录 |
| `JudgmentContext` | 发起者、判定用途、翻牌、历次改判与操作者、最终牌/结果、归属 |
| `Command` / `Action` | request id 或玩家、意图与参数；Action 另有 id、父 id、执行状态、效果 key |
| `Event` | 不可变 id、类型、时点、关联动作/玩家/牌、前后摘要、序号；前置可修改窗口使用独立可变 Context |
| `DecisionRequest` | 唯一 id、状态版本、受询玩家、种类、公开提示、合法选项/约束、最小最大数量、可取消性、截止语义、可见性、来源帧 id |
| `Decision` | request id、玩家 id、选择、确认/取消；引擎重新校验合法性，不信任 UI/AI |
| `ResolutionFrame` | id、父帧/Action id、效果 key、程序计数器/步骤、局部 id 与小型上下文、目标游标、子帧返回槽、状态、取消策略 |

绝不把 Python 对象引用、GUI widget、生成器闭包或回调函数存入帧。帧只存稳定 id 与可序列化标量/列表；执行器由 key 查注册表。未来存档可从这些数据恢复；T0/T1 不实现存档。

## Command、事件与触发

入口将玩家意图变成 Command，验证行动权、可见性、费用、次数、目标、距离后创建 Action 帧。前置规则窗口（例如 `BeforeUseCard`、`BeforeDamage`）允许注册的修正器调整上下文或否决；提交状态变化后发布事实 Event（如 `CardUsed`、`Damage`、`CardMoved`）。触发器返回候选触发帧，不直接随意改状态；主动技和转化技先给合法行动生成器提供选择，再转为普通 Command/Action。锁定技自动入队；限制技消耗状态标记；被动修正规则技通过距离、手牌上限、出杀次数等查询接口参与计算。技能只依赖 Context、服务协议和 id，不互相 import。

事件生命周期至少覆盖 GameStart、TurnStart/End、PhaseStart/End、BeforeDraw/AfterDraw、BeforeUseCard/CardUsed、TargetChoosing/Chosen/Confirmed、BeforeRespondCard/CardResponded、BeforeDamage/DamageCaused/DamageInflicted/Damage/AfterDamage、HpLost/HpRecovered、BeforeJudgment/Judgment/AfterJudgment、CardMoved/CardDiscarded/EquipmentChanged、Dying/AskForPeach/RecoveredFromDying/Death、SkillActivated。这里的 `Before*` 是窗口请求，`*ed`/过去式是已提交事实；具体事件 schema 在 T2 固定。伤害数值修改按造成伤害、受到伤害、防止、实际扣血、伤后顺序；每个检查点允许插入触发帧。

同时触发的技能先按固定规则层级/优先级排序，再按当前回合玩家起、沿座次的顺序排序；同一玩家有多个可选技能时发一个有序选择请求，锁定技按规则自动处理。所有顺序与选择写日志。具体官方时点冲突在 T11 用规则集裁决，不能靠 dict 迭代顺序。

## 显式结算栈与暂停协议

采用**显式、数据化栈式状态机**。`advance()` 每次运行至待答请求、终局或本步完成。栈顶帧按 `effect_key + step` 执行一个小步骤，可推入子帧，也可发布请求；此时停机，栈和 `PendingRequest` 保留在 `GameState`。`submit(decision)` 验证 request id/状态版本/玩家/合法选项，原子记录选择，清空待答，把结果写回发问帧的返回槽，然后继续 `advance()`。错误或重复决定不改变状态。取消是请求/行动明示允许的分支；已支付成本或不可取消窗口不能回滚，取消效果与取消动作分别记录。子帧完成后弹出，将结果写入父帧并恢复其下一步骤。一个 Action 只有其自身、所有子帧、后续触发与状态清理、身份/终局检查全部结束，且无未完成请求时才算完成。

栈帧至少保存类型/处理器 key、当前步骤、父 id、动作 id、目标列表及游标、局部 context id、已付费用/已提交效果标志、子结果、取消/异常策略。`PendingRequest` 保存上表字段和来源帧，永远仅有一个当前待答请求；后续请求由栈继续计算。系统命令和触发可嵌套，但设循环防护：相同触发不在同一事件实例无限重复，传播链逐目标至多一次，测试设最大步数诊断而非改变规则。

不采用 `async/await`：它把等待绑定运行时事件循环，难于纯同步 pytest 步进与状态持久化；不采用 Python generator：挂起点藏在不可序列化调用栈中，跨版本恢复困难；不采用纯递归：UI 等待需要保留 Python 调用栈，嵌套深度与中断控制不清晰。显式帧增加步骤状态维护和样板代码，但支持确定性重放、可观察暂停点、无 Qt 测试及未来快照。GUI 可以用 Qt 信号接收 `PendingRequest`，但核心无需异步。

## 三个关键流程（伪代码）

```text
UI 点击杀 -> submit(UseCardCommand(A, 杀, [B]))
验证出牌时机/次数/距离/目标 -> 扣用牌至处理区 -> push UseCardFrame
BeforeUseCard -> CardUsed -> TargetChosen/Confirmed -> push SlashTargetFrame(B)
SlashTargetFrame.step=ask -> push ResponseFrame(B, 闪)
ResponseFrame 发布 PendingRequest；advance 返回 WAIT
真人点击闪 -> submit(Decision(request_id, 闪实例 id))
验证、移牌、BeforeRespondCard/CardResponded -> ResponseFrame 返回 success
SlashTargetFrame 恢复：success 则闪避；否则 push DamageFrame(A,B,1,普通)
伤害及可能的濒死/触发全部返回 -> 处理区卡牌归位 -> Action 完成
```

AI 与真人共享该流程：调度层把同一 `PendingRequest` 的可见投影交给对应 `DecisionProvider`；AI 返回相同 `Decision` 并由同一 `submit` 验证。测试脚本亦然。核心没有 `is_ai` 分支。

```text
push BarbarianFrame(targets=[B,C,D,E], cursor=0)
对 B 推 ResponseFrame(杀)，返回后 cursor=1
对 C 推 ResponseFrame(杀) -> 失败 -> push DamageFrame(C)
DamageFrame 扣血并 push DyingFrame(C)；BarbarianFrame 原游标留在栈中
DyingFrame 按规则座次依次 push PeachRequestFrame；每个请求可 WAIT/submit
求桃成功则恢复；失败则 push DeathFrame、身份奖惩/胜负检查
DyingFrame、DamageFrame 弹出；若终局则清理并停止，否则 BarbarianFrame cursor=2 继续 D、E
```

```text
TrickTargetFrame 准备生效 -> push NullificationWindowFrame(base_effect)
按合法座次询问无懈；C 响应 -> 移牌并 push NullificationWindowFrame(C 的无懈)
若再有无懈，继续推子窗口；最内层无响应时逐层返回并翻转抵消结果
窗口返回 effective/cancelled 给 TrickTargetFrame；依结果生效或取消
每次响应、顺序、目标范围和链上奇偶/实际结果入日志；具体作用范围按牌/规则集定义
```

示例技能接入（不实现技能）：

```text
register_skill(id="huangyueying_jizhi", on=CardUsed,
  predicate=lambda ctx: ctx.actor_has_skill and ctx.card.category == TRICK,
  build_trigger=lambda ctx: DrawAction(ctx.actor, 1))
```

## 专用系统与一致性

`CardMoveSystem` 是唯一实体牌位置写入口，负责原子校验、区域占用、装备替换及移动事件。`DamageSystem` 管来源/性质/修正/防止/扣血；属性伤害用传播链 id 与受害集合推连环子帧，避免循环；扣血后由 `DyingSystem` 插入求桃，`IdentitySystem` 在死亡结算点处理奖惩与胜负。`JudgmentSystem` 管翻牌至处理区、逐次改判请求、最终判定和原/最终判定牌归属。`DistanceSystem` 根据存活座次、马、技能修正、武器范围和无限距离能力计算；目标合法性由 `RuleEngine` 查询。`EquipmentSystem` 处理槽替换、失效和装备触发注册。`PhaseSystem` 维护可跳过阶段与阶段内行动请求，`TurnManager` 排队额外回合。卡牌和技能只调用这些系统暴露的能力，不直接改手牌/体力。

T1 的区域表示为 `GameState.zones: dict[ZoneRef, CardZone]`。`PlayerState` 无手牌/装备/判定牌副本，`CardInstance` 无位置字段。T1 仅在构造状态时检查每张牌恰好处于一区；运行中所有移动须待后续统一移动系统实现后才开放。

结构化 `GameLog` 记录命令、决策、随机取值、事件、移动、判断与终局，文本由展示层按日志类型本地化；隐藏信息按玩家投影过滤。未来 replay 可由初态/规则版本/随机流/决策流重放并比对状态哈希，T0 不承诺日志本身即完整存档。

## 架构风险检查

- God Object：引擎只协调，系统分责；代码评审禁止在入口加入按牌名/武将名分支。
- GUI 耦合：核心不 import Qt，UI 仅接收投影和请求并提交 Decision；规则测试不启动 GUI。
- 扩展风险：新牌/武将注册 definition、效果/技能处理器与测试，不修改调度器；真正新增规则原语时允许经设计审查扩展系统协议，不能虚称任何未来机制都零核心改动。
- 一致性风险：单一写入口、状态版本、请求幂等校验、帧执行步数诊断与区域/栈不变量测试。

## T2 实际结算实现（2026-09-28）

`GameEngine.start_action` 创建根帧并同步运行 `run_until_blocked()`。循环只执行栈顶 `READY` 帧，按注册表查找 `ActionHandler`，处理明确的 `StepResult`：继续、请求、压入子动作、完成、取消或失败。每次循环最多 100,000 步，可配置以诊断不推进的处理器。引擎不按具体 Action 类型分支。

`ResolutionStack` 提供 push/top/pop/depth/snapshot。`ResolutionFrame` 保存 action、step_index、cursor、受限局部标量、decision、child_result、result 和 `FrameStatus`。生命周期为 READY → WAITING_DECISION → READY 或 READY → WAITING_CHILD → READY → COMPLETE → POP。只有 READY 帧可执行；完成后立即弹出。子帧完成时，结果写入仍在栈上的父帧 `child_result`，父帧恢复 READY 后继续其保存的步骤。

处理器发出 `PendingRequest` 时，引擎核对来源帧/动作、记录唯一 request_id、把帧设为 WAITING_DECISION，并停止运行。`submit_decision` 在修改帧前验证 request_id、player_id 和请求种类的合法值。无效答复保留原请求、栈及 WAIT 状态。合法答复写入帧的 `decision` 槽、清除请求，再运行同一循环。T2 真正校验 YES_NO、CHOOSE_OPTION、CHOOSE_PLAYER；其他种类只定义标识，留待具体规则阶段定义约束。引擎从不自动选择。

`ActionHandlerRegistry` 以准确的 Action 类映射处理器。Action 为数据，处理器负责步骤和状态变更。`Event` 是无执行逻辑的事实记录；`EventRecorder` 是测试用最小收集器，不是 EventBus 或正式日志。

与 T0 预期的差异：T2 的栈和待答请求暂存在 `GameEngine`，未加入 T1 `GameState`，以保留已验收模型边界；帧暂持有不可变 Action 数据对象，而非仅存 action_id。T2 保证 Python 调用栈退出后可恢复同一内存中的引擎，但尚不承诺序列化/跨进程恢复。后续如需存档，须设计 Action 数据编码与栈快照，再迁移至权威状态；不得将 GUI 对象或回调存入 Action。T2 也未建立 Command、状态版本、取消回滚及事务机制，留给对应后续阶段。


## T3 回合与阶段实现（2026-09-28）

`TurnAction` 是 T2 的普通 Action。`TurnActionHandler` 在开始时校验玩家仍存活；开始回合时设置 `GameState.current_player_id`、清空 `current_phase`、将 `turn_number` 加一并记录 `TurnStartedEvent`。其帧的 `cursor` 保存下一阶段位置；每个未跳过的阶段以 `PhaseAction` 子帧压入同一个 `ResolutionStack`。子阶段返回后父帧继续游标，全部阶段完成时记录 `TurnEndedEvent` 并保持 `current_player_id` 为刚结束回合的玩家、`current_phase=None`。`STANDARD_PHASE_ORDER` 是唯一默认阶段顺序：准备、判定、摸牌、出牌、弃牌、结束。T1 的 `Phase.START` 保留为兼容性枚举值，表示回合开始边界，不是可执行标准阶段；T3 不修改 T1 枚举。

`PhaseActionHandler` 负责统一生命周期：进入时设置 `current_phase` 并记录 `PhaseStartedEvent`，执行注册的 `PhaseBody`，完成后记录 `PhaseEndedEvent` 并清空 `current_phase`。`PhaseBodyRegistry` 允许替换各阶段主体；准备、判定、摸牌、弃牌、结束阶段在 T3 为无操作主体。这里没有抽牌或弃牌移动。被标记跳过的阶段根本不创建 `PhaseAction`，也不发布正常开始/结束事件，只发布 `PhaseSkippedEvent`；跳过顺序仍沿标准游标前进。

出牌阶段主体从 `PlayOptionProvider` 获取有序合法选项，追加明确的 `end_play_phase`，发布 `CHOOSE_OPTION` 请求。帧的 `step_index` 与 `cursor` 保存请求次数和恢复位置；选择操作后由 Provider 构造 Action，作为出牌阶段的子帧压栈。子 Action 及其更深子帧可提出自己的 `PendingRequest`。完成后出牌帧再次请求操作，直到收到 `end_play_phase`。默认 Provider 只提供结束操作；测试 Provider 提供 mock 操作。所有答复仍通过 T2 的 `GameEngine.submit_decision` 校验。

`next_alive_player` 按 `seat_order` 环形查找下一个存活玩家，跳过死亡座位。T3 只运行指定的单个回合；调用方可据此选择下一回合玩家，尚无自动整局循环或额外回合队列。开始第二个顶层回合时沿用 T2 的忙碌状态拒绝机制。T3 对 T2 引擎只加了通用 Handler `validate_start` 预检钩子，用于在创建根帧之前拒绝死亡玩家；引擎没有增加回合或阶段分支。


## T4 基础牌与移动实现（2026-09-28）

`CardDefinitionRegistry` 以稳定的 definition id 保存 T1 的不可变 `CardDefinition`。`content/cards/basic.py` 注册 `basic.slash`、`basic.dodge`、`basic.peach`；中文名称只用于展示，不参与规则分支。可执行行为在 `CardRuleRegistry` 中按 definition id 注册，`GameEngine` 仍只认 Action/Handler。未注册定义不会出现在出牌选项，强制使用会被拒绝。

`CardMoveService` 是 T4 正式规则修改 `GameState.zones` 的唯一入口。`CardMove` 记录牌 id、来源/去向、USE/RESPONSE/DISCARD/SYSTEM 原因、操作者和关联 Action；服务先验证所有牌属于来源、各牌位置唯一、去向容量及整批合法性，再一次提交两个区域并记录 `CardMovedEvent`。失败移动不改状态。T1 的 `CardInstance` 与 `PlayerState` 没有位置副本。T4 使用的正式路径为 HAND → PROCESSING → DISCARD；尚无摸牌、装备或判定规则。

`CardUseValidator` 分别检查存活、自己的 PLAY 阶段、实体牌在手牌、定义和规则已注册、卡牌主动使用条件及当前阶段使用次数。`TargetValidator` 委派每张牌的目标规则。普通杀目标由可替换的 `SlashTargetFilter` 提供；T4 默认允许除自己外任意存活玩家，**刻意不计算攻击距离**，T5 可替换过滤器。桃仅在受伤时对自己主动使用；闪仅响应，不能主动使用。非法使用在移动前被拒绝。

`UseCardAction` 不包含牌种分支。选择杀而未指定目标时，先发布 `CHOOSE_PLAYER` 请求；不允许隐式取消。合法目标答复后重新校验，HAND → PROCESSING，记录 `CardUsedEvent`，在 typed `GameState.play_usage` 中记一次使用，再从注册规则取得并压入效果子 Action。效果结束后 PROCESSING → DISCARD，记录 `CardResolvedEvent`。杀的默认每出牌阶段上限为一张，由可替换的 `SlashLimitProvider` 给出；`PhaseActionHandler` 在每次进入 PLAY 时创建新的 `PlayUsageState`，因此非法目标不计数、新阶段自动重置。

`LegalPlayActionProvider` 根据手牌区域顺序、定义、规则和使用次数生成 `use:<实体牌id>` 选项，沿用 T3 出牌阶段请求和循环。杀的目标选择是下一层请求，不为每个目标生成一个出牌选项。`RespondWithCardAction` 发布 `RESPOND_WITH_CARD` 请求，明列所需 definition id、可用实体牌 id 和显式 `PASS_RESPONSE`；T2 引擎在提交时验证选择。选择闪时由移动服务经处理区到弃牌堆，并记录 `CardRespondedEvent`；放弃时手牌不变。

杀的结算链是 `UseCardAction → SlashEffectAction → RespondWithCardAction`；闪成功则返回 avoided，放弃则压入 `DamageAction`。`DamageAction` 记录 BeforeDamage、DamageDealt、AfterDamage 事件后扣体力；体力可到零以下，并发 `DyingRequiredEvent`，但玩家仍为 ALIVE，T4 不启动求桃或死亡结算。桃的链是 `UseCardAction → PeachEffectAction → RecoverAction`，恢复量按最大体力截断并发 `HpRecoveredEvent`。这些都是同一 T2 显式结算栈中的子帧，可在目标和响应处多次暂停。

已知边界：T4 没有事务回滚机制。所有正常牌效分支都会把处理区的牌移到弃牌堆，且领域校验在首次移动前完成；若移动后的处理器发生意外框架错误，可能留下处理区牌，后续事务/恢复设计须处理。`DyingRequiredEvent` 是未来完整 `DyingSystem` 的接入点。酒、属性杀、装备、距离、技能、AI、GUI 等未实现。


## T5 可玩版实现（2026-09-28）

`GameSession` 是组成根与无界面整局调度器：构造五人 `GameState`、80 张实体牌、注入随机源、注册 T2 Action handlers 和 T3 阶段主体。每次 `step_auto()` 最多启动一个 `TurnAction` 或提交一个 AI `Decision`；所有规则仍由原 `GameEngine` 的显式结算栈运行。Qt 用 `QTimer.singleShot` 分批调用它，遇真人 `PendingRequest` 停止自动推进，让事件循环刷新界面。没有 GUI 回调进入规则处理器，也没有第二套结算循环。

`DeckService` 使用 T1 `RandomSource` 洗牌，发牌、摸牌、弃牌堆重洗都通过 `CardMoveService`。临时牌堆为杀 48、闪 20、桃 12；每人起手四张。摸牌阶段 `DrawPhaseBody` 压入 `DrawCardsAction(2)`。弃牌阶段 `DiscardPhaseBody` 以 `max(0, hp)` 为手牌上限，发布数量精确的 `CHOOSE_CARDS` 请求，再经移动服务转入弃牌堆。请求校验在引擎内完成，AI 和 GUI 提交相同的 `Decision`。

`DamageActionHandler` 在 T5 组成时注入濒死 Action 工厂；旧 T4 单元环境不注入时保留 T4 的仅标记行为。体力不截断，达到零或以下后，`DyingAction` 按濒死者起的座次逐人压入实体桃响应 Action。桃响应后压入 `RecoverAction`；体力仍不高于零则重新询问，所有存活玩家一轮均放弃后压入 `DeathAction`。死亡动作公开身份、弃置死者手牌/装备区/判定区卡牌，处理击杀反贼摸三张与主公杀忠臣弃所有手牌和装备区牌，再由 `IdentitySystem` 判断胜负。结果写入 typed `GameState.victory`，状态变为 FINISHED；出牌及回合帧完成清理后不再发新请求或新回合。

`projection.project_for_human` 是 GUI 的只读可见快照：只含真人具体手牌；对手只有手牌数量。真实身份仍在模型，公开身份由 `revealed_identities` 与主公公开规则决定。死亡时将玩家加入公开集合。`AIDecisionProvider` 仅解释 `PendingRequest`，用同一 `Decision` API；暂允许 AI 内部参考真实身份，优先受伤时用桃、可攻击时用杀、响应闪、友方濒死出桃，并按保留桃/闪的简单次序弃牌。

Qt 界面位于 `ui/`：`MainWindow` 管启动和计时器，`GameTable` 展示五人环形座位，`PlayerPanel` 承接目标点击，`HandView`/`CardWidget` 展示可点手牌，`DecisionController` 展示请求控制，`LogPanel` 仅展示公开事件。真人动作只构造 `Decision` 并调用 Session 入口；Qt 模块不被模型、引擎、牌规则导入。界面没有直接写 `GameState`。

这是用基础牌驱动的可玩版，尚无完整军争规则、距离装备、技能或公平隐藏信息 AI。T4 已知的意外处理器错误后处理区恢复仍待事务机制处理。


# T18A.7 验收报告

起点：`be47793015fe26935878e59a98b29d9cf7d6085d`（T18A.6 pre-deploy worker sync）。

结论：本轮已知验收问题已解决，**remaining issues = 0**。仅本地开发与验收；未公网部署，未开始 T17C，未生图，未新增武将。用户选择先由代理完整验收，再自行体验。

## 25 项最终验收

| # | 项目 | 结果与证据 |
|---|---|---|
| 1 | T18A.6 为什么仍看不懂 | 回合、thinking、actor、target 共用席位反馈，短暂状态覆盖长期状态；响应含倒计时但缺少原牌和要求；中央牌仅 144–196px；真人请求清队列造成信息断裂；AOE 目标声明未用于全场演出；杀/闪特效约 0.34/0.26 秒；简单响应约 2.2 秒，部分无合法响应仍等待 AI。基线真实对局记录保存在 `baseline/`。 |
| 2 | 回合状态 | 当前玩家完整、稳定暖金框，轻微光晕，席位边缘显示阶段；他人响应时金框保留，回合切换跟随 authoritative projection。 |
| 3 | 响应状态 | 独立青白完整框，2.4 秒缓慢呼吸；与金框使用独立伪元素，可同时存在。PendingRequest 结束后响应文字和倒计时一起清除。 |
| 4 | 响应什么 | 响应者席位底部显示原牌与要求，如“响应【杀】 / 请出【闪】”“响应【南蛮入侵】 / 请出【杀】”“响应【过河拆桥】 / 可使用【无懈可击】”；thinking、时间条、秒数同属席位状态。 |
| 5 | 中央卡牌尺寸 | 桌面 `clamp(220px,18vw,300px)`，1440px 宽时约 259px；短桌面高度为 220px；手机基础牌 150px，响应牌 126px。中央呈现牌、技能、关系和结果。 |
| 6 | 杀 VFX | 复用 Canvas portrait anchors，source→target 墨金轨迹与箭头，约 0.9 秒，目标冲击反馈，中央保留杀。见 `A-trajectory.png`、`A-slash-response.png`。 |
| 7 | 闪 VFX | 中央原杀旁显示闪；目标出现化解/闪避，轨迹偏折、消散，约 1.1 秒。见 `A-dodge.png`、`B-ai-dodge.png`。 |
| 8 | 南蛮全场 VFX | 使用 engine 声明的 targetIds 同时 fan-out、标记合法目标，随后按真实顺序逐人响应杀；待结算/当前/已结算席位标记。死亡、藤甲及南蛮免疫由 engine 排除。见 `C-trajectories.png`。 |
| 9 | 万箭全场 VFX | 同一 Canvas 多目标能力，扇形细箭影与方向线，区别于南蛮；逐人响应闪。见 `D-trajectories.png`。 |
| 10 | 不响应语义 | `{pass:true}` 只提交当前 request 的 PASS。反无懈产生新机会时会重新询问；真实引擎测试确认。 |
| 11 | 本次不无懈语义 | `{pass:true,scope:'root_trick'}` 绑定当前 root TrickAction、当前玩家，跳过该基础锦囊的其他目标和反无懈机会；根动作完成立即清除。同一 PhaseAction、同一回合的下一独立锦囊重新询问。snapshot/reconnect 恢复未完成 scope；错误响应上下文拒绝且不留下偏好。 |
| 12 | 无懈链 | 最多原锦囊 + 当前顶层无懈，显示无懈次数和当前有效/失效状态；奇偶数对应当前展示的响应，而非已切到下一目标的上下文。见 `F-counter-chain.png`。 |
| 13 | AI thinking 时长 | NORMAL 简单 2.8 秒；普通 3.5–4.94 秒；复杂从 4.5 秒起，上限 7 秒，按候选、目标、技能/ViewAs、资源取舍评分。真实五人记录 52 次、2.80–5.35 秒；八人 99 次、2.80–6.05 秒。这是服务器下发的实际计划等待，浏览器轮询会带来少量完成延迟。 |
| 14 | Decision 绕过调查 | 未发现真正 Decision 类型绕过统一 gateway。YES_NO、响应、单/多目标、单/多牌、选项及 virtual ViewAs 均覆盖；同一 pending 只生成一次 thinking。无合法响应和已选 root skip 是强制 PASS，立即推进，不伪装思考。 |
| 15 | AI 策略 | 保留原有先拆防具、装备范围、无中生有、击杀与低血资源评分；加强无懈的敌我价值、原锦囊收益、链奇偶和稀缺资源判断；南蛮/万箭按公开血量、装备、技能、手牌数量评估净收益。隐藏牌定义变化不影响对应评分/无懈决定，40 场完整 AI 回归逐次验证 action 合法。 |
| 16 | 五人实际体验 | seed=3、NORMAL、1440×1000，真实引擎持续到第 11 回合，经过 10 个完整玩家回合，263.73 秒；20 次出牌、3 次实体/虚拟响应、113 次 UI 状态观察、JS errors=0。席位 turn/thinking 与中央原牌关系可辨；截图结合 DOM 时间线复核，不仅检查测试通过。 |
| 17 | 八人实际体验 | 同条件到第 11 回合，10 个完整玩家回合，514.81 秒；33 次出牌、8 次响应、6 次技能、224 次 UI 状态观察、JS errors=0。多人连续响应、伤害与技能的信息归属可辨。这里“回合”按 engine turn_number，非全桌轮转 10 圈。 |
| 18 | mobile | 五人/八人各在 390×844、430×932 检查，4 项通过；响应说明、秒数、中央牌、确认/取消可见，操作区位于自己席位右侧，响应 footer 位于自己武将底部。见四张 `mobile*.png`。 |
| 19 | Python | full pytest **1075 passed / 0 failed**，398.97 秒。随后只强化 root scope 测试、调整前端和清除空白，后端逻辑未变；最终新增 7 项与 Worker 相关 13 项再次通过。见 `python-results.txt`、`worker-results.txt`。 |
| 20 | Vitest | **81 passed / 14 files**；turn、response、语义/倒计时、原牌与顶层响应、AOE、queue、已连接时恢复会话回归。见 `vitest-results.txt`。 |
| 21 | Playwright | 最终 A–F + 四项 mobile **10 passed**，另两场真实长局 **2 passed**，合计 12 项验收通过。最终场景日志为 `flow-playwright.txt`；`playwright-results.txt` 是较早的混合运行，包含当时 4 项场景失败和成功长局，失败已由修正 fixture/选择器、重连和链展示后的最终 10 项运行消除，不计为当前未解决项。 |
| 22 | TypeScript | **PASS**，最终 `tsc --noEmit` 检查；fresh build 也执行 `tsc -b`。见 `typescript-results.txt`。 |
| 23 | fresh Vite | **PASS**，55 modules，1.16 秒；构建后使用已有 `sync_web_assets.py` 恢复 PNG 开发资源。见 `build-results.txt`。 |
| 24 | Worker mirror | 使用既有 `scripts/sync_cloudflare_game_room.py` 同步；最终 `test_worker_engine_bundle_matches_authoritative_source` 逐文件/字节一致，Worker room、deck data、ack 等 13 项及本轮 7 项共 **20 passed**。未部署 Worker。 |
| 25 | remaining issues | **0 个本轮已知验收阻塞问题**。在此结论和所有 gate 通过后创建指定 checkpoint，并停止本轮开发。 |

## 数据来源、持续时间与清除

| 状态 | 来源 | 生命周期 |
|---|---|---|
| turn / phase | authoritative projection 的 current_player_id / current_phase | 当前玩家回合始终保留，换回合立即换席位 |
| response / timer | authoritative PendingRequest、waiting.deadline / remaining_ms | 与 request 绑定，重连恢复剩余时间；不从满时间开始 |
| thinking | room 的统一 AI gateway、ai_deadline、AIThinkingEvent | 仅 AI 席位；真实决定完成清除 |
| actor / target | 公共 action 事件、已有 presentation queue | 仅对应 reveal/target/result 阶段；不覆盖回合框 |
| card reveal / response | CardUsedEvent、TrickTargetsDeclaredEvent、响应事件与公开 combat context | 原牌贯穿当前结算；保留当前顶层响应；结算完清除上下文 |
| AOE target | engine 真实 targets、当前 TargetTrick / NullificationWindow、已结算 cursor | 全场声明后逐目标推进，不由前端生成目标或复制规则 |

复用现有 queue 合并原牌与目标声明。NORMAL reveal 1.4 秒（多目标约 1.61 秒）、轨迹阶段 0.85 秒起、响应 1.2 秒、技能 1.5 秒、伤害/回复 1 秒。服务器接受 AI 动作后采用一次最大语义 dwell：基础牌 2.3 秒、响应 1.2 秒、技能 1.5 秒、伤害/回复 1 秒；不按内部 engine 事件叠加 sleep。速度档只缩放 AI/presentation，不修改真人 deadline。

## 边界与复现

AI 仍为轻量评分，不能保证最优策略。本轮视觉结论覆盖所列桌面/手机尺寸、A–F 定向真实引擎场景和 seed=3 两场连续真实对局，不代表对所有武将组合和所有视口进行穷举。用户体验反馈仍可发现新的改善点，不纳入本轮未出现的已知问题。

`audit_server.py` 仅供本地 deterministic fixture，未导入 production。运行 `web/playwright.t18a7.config.ts` 使用 loopback 8007/5177；长局正常速度约需 9 分钟，可分别运行 flow 与 real-rounds spec。完整事件及 UI 时间线在 `military-*-observations.json`，汇总在 `summary.json`；原始较早失败日志保留用于审计，最终通过结果以对应最终日志为准。

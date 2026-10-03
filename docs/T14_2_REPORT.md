# T14.2 — Public Match Responsiveness & Interaction Flow

日期：2026-10-04。仓库：C:\Sanguosha。分支：t13-complete-roster-multiplayer。
基线：4db1575ca3f5a2e384e2833d9544c7dd51b80783。
公网：https://sanguosha.aopl-games.workers.dev。本轮未部署，以下 PASS 均为本地证据。

## 1. 确认后等待的根因

已确认的代码问题：GameEngine.submit_decision 原先在清除请求后立即同步 run_until_blocked；外层 room.submit 又继续 pump。Cloudflare WebSocket 事件的最终完成还包含快照持久化和广播，因此确认信息会被完整引擎结算占用的事件路径拖住。客户端又用笼统处理状态覆盖提交与已接受之间的区别。

本轮真正将引擎执行移出 ACK 路径：server 验证、将决定写入 READY frame、清除 pending request/deadline、记录 accepted_request_id、持久化接受快照并安排 durable alarm、发 DECISION_ACCEPTED；独立 alarm 继续结算并持久化后续状态。重启/休眠恢复读取相同标记。下一条非 HELLO/PING 消息也会先完成此前接受的操作。没有 authoritative sleep，也没有跳过验证或存储。

公网现场的“等半天”尚未通过新版本公网 diagnostics 复现。因此不能把以上代码问题等同于所有公网多秒延迟的唯一根因，也没有前后对照的性能改善百分比。

## 2. 延迟归属：A—F

| 层 | 当前证据与结论 |
|---|---|
| A Browser/UI | 点击到发送中位数 0.1 ms；提交状态即时变化，ACK 与结算状态分开。没有本地多秒点击延迟。 |
| B WebSocket network | 本地 RTT 中位数 2.45 ms；浏览器发送到收到 ACK 为 12.25 ms。此段还包含服务器处理与调度，不能全部归为网络。公网网络未测。 |
| C Worker/Durable Object | 收到到接受中位数 0 ms，p95 1 ms；采用独立 alarm 继续执行。实际公网 Worker 调度未测。 |
| D authoritative engine | 确认旧同步执行进入 ACK 路径的问题；修复后引擎结算在 ACK 之后。ACK emit 到 projection emit 中位数 39.5 ms 是调度、结算、广播等合计，尚无独立 engine profiler。 |
| E persistence/storage | 接受到 ACK 中位数 1 ms，包括接受快照、活跃标记、alarm 设置；不是单独 storage 耗时。接受快照始终先于 ACK。 |
| F projection/broadcast | ACK 接收到 projection 首帧渲染中位数 57.2 ms；没有把该段误归为 ACK 延迟。广播、浏览器调度与渲染未分别测量。 |

结论：确定存在 server resolution 的 ACK 路径耦合和 client state 表达问题；本地已修复。没有证据认定公网主要由网络、Cloudflare 或存储导致。

## 3. Decision timing 数据

真实本地 Cloudflare Durable Object + Chromium，最终代码，十次单人选将 Decision。不是纯 mock 性能测试，也不是公网数据；不覆盖所有战斗技能和长 AI 链。p95 使用 nearest-rank（n=10 时等于最大值）。原始非敏感样本：docs/T14_2_BROWSER_METRICS.json。

| 指标 | median ms | p95 ms |
|---|---:|---:|
| T0 click → T1 send | 0.1 | 0.2 |
| T1 send → T2 receive（时钟估算） | -2.0001 | -1.3999 |
| T2 receive → T3 authoritative accept | 0 | 1 |
| T3 accept → T4 ACK emit | 1 | 1 |
| T2 receive → T4 ACK emit（逐样本相加） | 1 | 2 |
| T1 send → T5 browser ACK | 12.25 | 13.8 |
| T5 ACK → T7 projection render | 57.2 | 64.4 |
| T4 ACK emit → T6 projection emit | 39.5 | 48.0 |
| T0 click → T7 visible completion | 69.4 | 76.4 |
| Ping/Pong RTT | 2.45 | 3.2 |

单向 send→receive 使用 Ping/Pong 中点校时，出现负数说明时钟精度、偏移估算和传输不对称影响；负数不是物理延迟，更不能用于归因公网网络。跨端可靠比较优先使用同端时钟间隔、server_timing_ms 和 RTT。

window.sanguoshaDiagnostics 提供最多 100 个数值 Decision 样本和 RTT，包含 T0—T7。开发模式可输出这些数值；生产模式不打印私有决定。指标不包含选项、手牌、隐藏身份、token、选将池、化身池或七星牌。回首页清空尚未完成的运行中指标追踪。

人工批准部署后，可在浏览器开发者工具读取 window.sanguoshaDiagnostics 并导出数值；应覆盖选将、响应、技能和出牌，重点记录慢操作的完整样本。当前公网仍是旧版本。

## 4. 的卢触发无懈的根因

未复现用户报告的公网现象，不能编造真实根因。基线规则注册已经把装备送入 EquipmentHandler，而非 TrickHandler；本地的卢使用没有 Nullification 请求。当前可证明的是分类与效果门控以及回归结果，无法判断当时是否是在处理邻近锦囊请求、旧版本或其他现场状态。

本轮没有 if card == dilu 特判。装备七匹坐骑、武器、护甲及基本牌回归均不错误开启无懈；正常锦囊和已有延时锦囊规则保持。

## 5. Nullification 判断层

CardDefinition.nullifiable 基于 CardCategory.TRICK / DELAYED_TRICK，再尊重 metadata['nullifiable'] == False。TrickHandler 和 DelayedHandler 在创建 NullificationWindow 前检查此属性。装备/基本牌不满足该属性，也不进入这两类锦囊效果处理器。

响应候选由 authoritative handlers/技能注册计算，包含实体与有效 ViewAs。room.pump 保留原有 has_legal_response 自动 PASS：只有 PASS 的可跳过响应不发到真人 UI；看破黑牌等合法候选仍保留。新增实际看破黑/红牌、disabled_skills 禁用回归；Dodge/Slash/rescue 及其他技能由既有规则链回归覆盖。

## 6. 选将 timeout 覆盖人工选择

未复现“server 已接受后随机覆盖”。基线已在人工选将时删除 request/deadline，正常 poll 不应再随机该请求。缺少当时 server receive/accept 数据，无法判定是真正已接受，还是只在浏览器点了确认后未及时到达服务器。

本轮强化：deadline 在 server 校验；合法接受立即写入 pregame.generals，并删除 request/deadline；存储接受快照和 accepted_request_id 后 ACK；完成 draft 可延后。重复提交被拒绝，旧请求不会二次消费。测试 deadline 前 100 ms 接受、deadline 后 2 s alarm，以及从接受快照休眠恢复仍保留人工选择。

浏览器 mock 测试在剩余 500 ms 提交，延迟 ACK 2.1 s，显示计时归零仍保留锁定选择；ACK 后隐藏旧 timer，再延迟 projection 1.1 s，未重复提交，最终显示选择的曹操。mock 测试验证 UI；server race 与恢复由实际 DO 代码配假存储测试验证。

## 7. 出牌流程结果

实体牌采用 CARD → TARGET(S) → 一次最终 CONFIRM，单一 {option, targets} Decision。server request 提供合法目标和 min/max，最终仍使用规则 validator 校验。杀与单目标锦囊首次点牌即选择、目标首次点击即高亮；无目标牌、装备直接最终确认；铁索等零目标重铸保留规则边界。

Cancel 先清目标并保留牌，返回目标选择；无目标时可退回选牌。技能转换原有专用交互继续使用原请求路径，没有将全部技能强行改成实体牌格式。非法点击有中文轻提示。

## 8. 60 秒统一配置

src/sanguosha/timing.py：HUMAN_DECISION_TIMEOUT_SECONDS = 60.0。
MultiplayerRoom、TCP transport、web rooms、桌面 ui/timing.py 均引用此配置，Cloudflare bundle 同步。浏览器只显示 server remaining_ms，不独立裁定超时。

Cloudflare 恢复旧房间时为未来请求应用当前 60 秒策略；已经存在的绝对 deadline 保留，避免改变一个正在进行的请求。离线 snapshot 工具仍保留显式自定义 timeout 值。AI 和 presentation 不使用此人类超时配置。

## 9. 中文化、AI 节奏、房间 UX

multiplayer/choice_labels.py 以 machine value → Chinese display label 分离内部值与 UI，覆盖固定分支、武将/技能目录、化身复合选项、ViewAs、牌区、花色、伤害量等。英魂使用中文分支；补正火包 14 个 catalogue skill names。web/labels.ts 统一技能类型及标记。对未知值使用中文“选项 N”，不直接展示 snake_case；这保证文字中文，但新增/未映射分支仍需后续人工核对具体语义。回归确认全 65 将目录的技能名含中文；不是已人工穷举 65 将每条实战分支。对方隐藏手牌和特殊区标签不泄露牌名。

保留 NORMAL presentation queue：普通 700 ms、重要 950 ms、阶段 600 ms；FAST 保持快速。真人 pending 到达立即可操作，queue 不占用 deadline；没有 engine sleep。

房间失效、无法恢复和重连终止返回首页轻 banner，几秒消失。短暂波动用顶部轻提示；回首页主动关 socket、清 reconnect timer、request、submit 及运行状态。保存的上一局只展示“继续对局/放弃”，用户选择后才恢复；超过 2 秒提交显示慢响应提示，决不自动重发 Decision。ACK 后区分“已确认，等待其他玩家…”和“已确认，正在结算…”。

## 10. 修改文件

下附文件清单包含本轮 checkpoint 全部文件。cloudflare/game-room/src/sanguosha 是权威 Python 源码的服务端镜像；一致性测试逐文件比对。test_t13_gods.py 的旧 PNG 路径断言改为读取生产资源 manifest（生产输出 WebP），未修改图片。未改美术、武将数、扩展或 T11 动画。docs/t11/god_art 的既有未跟踪目录未纳入提交。

## 11. Python targeted tests

核心指定集合：398 passed / 14.32 s，涵盖 military basics/equipment/chains/tricks、network/multiplayer、snapshot/room snapshot、Cloudflare、风火林山神、response legality/suppression、T14.2 flow/labels/equipment/ACK。
新增旧房间 60 秒迁移测试后，ACK + Cloudflare 集合：11 passed / 0.27 s，其中与上述集合重叠 10 项、新增 1 项。
额外 web validation/server、Cloudflare deck data：27 passed / 17.07 s（项目 .venv）。最终统一重跑上述完整 targeted 集合：426 passed / 16.12 s；不是全仓库 pytest。

全局 Python 额外网页集合首次收集失败：其 Starlette 需要未安装的 httpx2。改用项目既有 .venv 后全部通过；未修改项目依赖掩盖此环境问题。

## 12. Vitest

10 个 test files、40 tests 全部通过。覆盖 card/target/confirm、equipment、英魂、提交状态、请求替换和连接清理等。jsdom 输出 canvas getContext 未实现提示；测试没有失败，实际 Chromium 测试另行通过。

## 13. Playwright

interaction_reliability.spec.ts：17 passed / 22.8 s，使用真实 Chromium + WebSocket mock，覆盖用户列出的主要交互场景，以及 Cancel、无合法响应 mock、合法看破 mock、AI presentation 与慢 ACK 选将。
decision_diagnostics.spec.ts：1 passed / 6.8 s，十次真实本地 Cloudflare 选将全链路数值采集。
合计 18 项通过。前者不替代 server legality 和真实公网测试。

## 14. TypeScript

npm run build 中 tsc -b 成功。

## 15. Vite build

CLOUDFLARE_ROOMS=1 npm run build 成功，执行生产 WebP 资源同步、tsc 和 Vite。46 modules，JS 291.86 kB（gzip 91.54 kB），CSS 62.17 kB（gzip 13.94 kB）。没有部署。

## 16. Cloudflare targeted tests

pytest 包含真实 worker 模块的假存储 ACK/接受快照/alarm/休眠恢复，以及权威 bundle 逐字节一致性和 HTTP/protocol/deck 检查。
node cloudflare/game-room/test_runtime.mjs 本地真实 runtime 全部断言通过：65 将及生产头像资源、独立私有 draft、60 秒 deadline、ACK 安全 timing、ACK 先于 projection、开局、同席位重连、projection 恢复、SQLite snapshot 活跃状态。
测试服务仅本地 localhost:8793。

## 17. checkpoint

本报告随本轮 checkpoint 一起提交；确切 commit hash 在最终回复中提供。可用 git log -1 --format=%H -- docs/T14_2_REPORT.md 查询包含本报告的 checkpoint。提交在现有分支上保留基线与有效改动，不执行 reset，不部署公网。

## 验收矩阵

| 项目 | 结果及证据边界 |
|---|---|
| RESPONSE LATENCY | 本地 PASS；公网 PENDING。十次选将 ACK/首帧数据如上，无公网改善百分比。 |
| DECISION ACK | 本地 PASS；权威验证、接受持久化、独立 alarm，实际 runtime ACK 早于 projection。 |
| DRAFT TIMEOUT RACE | 本地 PASS；deadline-100 ms / +2 s / 休眠恢复，浏览器慢 ACK。现场覆盖根因未复现。 |
| 60 SECOND HUMAN TIMER | PASS；统一配置、新请求及旧房间未来请求；已有 deadline 保留。 |
| CARD → TARGET → CONFIRM FLOW | PASS；实体杀/锦囊/装备 Python 与浏览器；技能专用请求继续保留。 |
| CARD CLICK RELIABILITY | PASS；首次选牌与非法反馈浏览器测试。 |
| TARGET CLICK RELIABILITY | PASS；首次目标与取消返回浏览器测试。 |
| EQUIPMENT NULLIFICATION | 本地 PASS；的卢/其他坐骑/武器/护甲/基本牌规则测试；公网现场未复现。 |
| NULLIFICATION LEGALITY | PASS；实体与实际看破颜色、禁用状态规则测试。 |
| NO-OPTION AUTO PASS | PASS；authoritative eligible 列表，既有与新规则回归。 |
| AI PACING | PASS；保留 presentation queue，真人请求立即可操作。 |
| ROOM FAILURE UX | PASS；首页 banner 与实际浏览器回归。 |
| HOME RECONNECT UX | PASS；主动断开、停止重连与显式恢复选择。 |
| PLAYER-FACING CHINESE | 自动测试 PASS；目录与固定分支映射，未知值中文兜底；65 将全部实战分支人工验收 PENDING。 |

下一步为人工审阅与部署确认，部署后再采集公网真实慢操作 diagnostics，完成公网验收。本轮没有自动 deploy。

### checkpoint 文件清单

- `cloudflare/game-room/src/main.py`
- `cloudflare/game-room/src/sanguosha/content/characters/myth.py`
- `cloudflare/game-room/src/sanguosha/engine/card_use.py`
- `cloudflare/game-room/src/sanguosha/engine/engine.py`
- `cloudflare/game-room/src/sanguosha/engine/military_tricks.py`
- `cloudflare/game-room/src/sanguosha/engine/phases.py`
- `cloudflare/game-room/src/sanguosha/engine/requests.py`
- `cloudflare/game-room/src/sanguosha/model/card.py`
- `cloudflare/game-room/src/sanguosha/multiplayer/choice_labels.py`
- `cloudflare/game-room/src/sanguosha/multiplayer/protocol.py`
- `cloudflare/game-room/src/sanguosha/multiplayer/room.py`
- `cloudflare/game-room/src/sanguosha/multiplayer/transport.py`
- `cloudflare/game-room/src/sanguosha/room_snapshot.py`
- `cloudflare/game-room/src/sanguosha/timing.py`
- `cloudflare/game-room/test_runtime.mjs`
- `docs/T14_2_BROWSER_METRICS.json`
- `src/sanguosha/content/characters/myth.py`
- `src/sanguosha/engine/card_use.py`
- `src/sanguosha/engine/engine.py`
- `src/sanguosha/engine/military_tricks.py`
- `src/sanguosha/engine/phases.py`
- `src/sanguosha/engine/requests.py`
- `src/sanguosha/model/card.py`
- `src/sanguosha/multiplayer/choice_labels.py`
- `src/sanguosha/multiplayer/protocol.py`
- `src/sanguosha/multiplayer/room.py`
- `src/sanguosha/multiplayer/transport.py`
- `src/sanguosha/room_snapshot.py`
- `src/sanguosha/timing.py`
- `src/sanguosha/ui/timing.py`
- `src/sanguosha/web/rooms.py`
- `tests/test_t13_gods.py`
- `tests/test_t14_2_choice_labels.py`
- `tests/test_t14_2_cloudflare_ack.py`
- `tests/test_t14_2_equipment_nullification.py`
- `tests/test_t14_2_play_flow.py`
- `tests/test_t8_multiplayer.py`
- `web/e2e/decision_diagnostics.spec.ts`
- `web/e2e/interaction_reliability.spec.ts`
- `web/src/App.tsx`
- `web/src/components/GamePage.test.tsx`
- `web/src/components/GamePage.tsx`
- `web/src/components/HomePage.tsx`
- `web/src/components/PregamePage.tsx`
- `web/src/connection/diagnostics.ts`
- `web/src/connection/GameConnection.test.ts`
- `web/src/connection/GameConnection.ts`
- `web/src/labels.ts`
- `web/src/state/GameContext.tsx`
- `web/src/state/InteractionFlow.test.tsx`
- `web/src/state/RenderRestart.test.tsx`
- `web/src/types.ts`
- `docs/T14_2_REPORT.md`

# T18A.10 最终验收

稳定基线：`3529769 — T18B complete 103-general roster and presentation`。本轮没有新增武将。最终 checkpoint 名称：`T18A.10 battle readability AI and interaction hardening`。

## 37 项结果

| # | 项目 | 实现与验收 |
|---|---|---|
| 1 | 左慈 bug 根因 | 客户端把技能上下文、材料选中与普通出牌合法集合混用；取消材料后旧转化过滤仍影响后续选牌，获得技能又曾仅从本将技能中查找。现在依据服务器虚拟选项重算材料，不缓存客户端花色规则。 |
| 2 | ViewAs 生命周期 | `effectiveSelection` 每次验证请求 epoch、当前有效技能、材料和目标；取消全部清空，切换技能清除前文。请求替换、失去技能、化身切换、超时、重连、回合结束和死亡不会沿用旧选择。 |
| 3 | 其它 acquired skills | 客户端覆盖奇袭、武圣、龙胆、丈八蛇矛、龙怒、伏魂、龙魂、乱击、火计、看破；服务器实际化身/快照/失效覆盖奇袭、武圣、龙胆、火计、看破、连环、伏魂、龙怒。装备与特殊牌堆材料可选择。 |
| 4 | Presentation Queue | 复用现有队列，按事件 ID 去重。公开亮牌、弃牌、判定、火攻结果、AOE 目标及连环传播保留至播放完成；新 snapshot 或真人请求不会吞掉关键公开事实。规则和提交仍即时由服务器处理。 |
| 5 | 弃牌展示 | 多张同批展示，使用统一公开卡牌 renderer；正常约 2 秒，按 Fast/Slow 比例调整。普通隐藏摸牌不进入该展示。 |
| 6 | 过河拆桥公开展示 | 真正进入公开弃牌堆后展示卡名、花色、点数与卡图；手牌、装备、判定区域均有服务端回归。所有席位广播与重连历史测试通过。 |
| 7 | 隐藏信息安全 | 选择隐藏手牌时使用匿名暗牌选项，公开结果也不携带真实隐藏卡实例 ID；隐藏顺手取得不触发弃牌公开。原隐私测试及所有客户端公开结果回归通过。 |
| 8 | 火攻流程 | authoritative TargetTrick 记录真实亮牌，保留花色；展示后进入同花色弃牌选择或“没有可弃置”提示，再显示未造成伤害结果。有同花色分支继续既有伤害流程。真人/AI 均走同一事件路径。 |
| 9 | 火攻 reconnect | frame 保存已展示牌与花色；快照恢复沿用该牌。projection 提供 `public_reveal`，保留 source/target、请求及 deadline；效果结束后撤销当前亮牌，只保留合法公开历史。 |
| 10 | AOE current target | 逐目标开始先发 EffectTargetEvent；无懈链中 combat current target 保持同一角色，之后响应杀/闪再推进。既有根锦囊/逐目标/快照测试与南蛮万箭 E2E 通过。 |
| 11 | 无懈快速跳过 | 群体/多目标才提供“本轮不再询问”，服务器也校验此能力；只跳当前根锦囊剩余询问，下张恢复。单目标只“不响应”。原根跳过/后续锦囊测试继续通过。 |
| 12 | 铁索 | 持久连环边框及标签取自 projection；重连立即恢复。链传播发 source→target 事件，按队列逐项展示。五/八人桌面和移动截图可见两名连环角色。 |
| 13 | 马匹 +/- | 卡牌和装备区显示 +1/-1，不依赖记忆名字。截图包含绝影 +1、赤兔 -1。 |
| 14 | AI 修改 | 扩展现有 heuristic：敌友公开行为、目标资源/装备、生命风险、关键防御资源、装备重复价值、火攻成本与花色、铁索、AOE与治疗净收益。Normal 思考约 1.8–3 秒，保留动作停留。不新增搜索框架，不读取隐藏敌方牌面或身份。 |
| 15 | AI deterministic tests | 17 项：敌友、隐藏身份扰动不影响选择、濒死资源、无懈奇偶、拆/顺装备与隐藏牌面扰动、火攻保留桃、连环、AOE，以及实际获得技能快照/失效。见 ai_deterministic.log。 |
| 16 | 5 人 AI | 30/30 完整结束，没有未处理请求、无限循环或处理区遗留。详情见 ai_acceptance.json。 |
| 17 | 8 人 AI | 30/30 完整结束；两模式合计 9,182 次 projection 检查、99 次中途快照恢复，覆盖前轮 27 名新增将。最终伤害结算另修复胜利后暴虐请求与装备反应。 |
| 18 | 座位布局 | 自己稳定底部中心；五人/八人独立位置数组，以自己为原点旋转真实 seat order。移动端使用三列周边布局。 |
| 19 | turn-order consistency | 六种人数/视口组合从非首席视角检查下一席到上一席顺序、角色矩形不重叠与页面无横向滚动；当前行动和当前结算目标有高亮。 |
| 20 | 托管 | 断线 15 秒 grace 后自动 AI 托管，保留现有角色、资源、标记和 token。真实 pump 回归确认原 pending 被处理，短断线不会抢控制。 |
| 21 | reconnect takeover | 有效 token 恢复原 seat 真人控制，撤销托管与旧 AI 等待；不新建玩家，不重置状态。房间快照保存托管/断线字段。TCP 重连与状态保留回归通过。 |
| 22 | 中文文案 | 弃牌提示及选目标提示中文化；无懈提示明确锦囊与当前目标；“连环”“AI 托管”与马匹标识中文。既有短 toast 与网络状态逻辑保留。 |
| 23 | 卧龙 | 注册表明确八阵（锁定）、火计、看破，三个技能有独立完整说明；已实际打开 Web 与 PySide 详情。 |
| 24 | 袁绍 | 注册表明确乱击、血裔与主公技元数据，两个技能独立说明；已实际打开 Web 与 PySide 详情。 |
| 25 | 103/103 审计 | 导出所有将的名字、势力、最大/初始体力、版本和技能名称/类型/说明；同时校验 189 个注册技能。Fire 包 14 项缺失描述按现有 handler 补齐；钟会、神刘备、神张辽保持前轮锁定版本。 |
| 26 | placeholder | 0；全注册表禁止 TODO、placeholder、规则摘要、待补、generic 等。详见 skill_description_audit.json，可运行 scripts/audit_descriptions_t18a10.py 重现。 |
| 27 | Web | 实际 GeneralDetail 全 103 将打开、逐技能比对 authoritative 描述；奇袭取消后正常桃可提交；复杂选择继续复用 TemporaryInteractionPanel，中央动作牌保持紧凑。 |
| 28 | PySide | 168 项 targeted/smoke 通过，其中 103 项逐将详情使用同一注册表；没有另一份占位描述。 |
| 29 | mobile | 390×844、430×932 的五/八人座位测试通过；430 视口覆盖南蛮、万箭、两类无懈、五谷、托管。最终代表布局截图已人工查看。 |
| 30 | Python | full pytest：1585 passed，182.83 秒。TCP 清理回归修复了 Python 3.13 关闭监听器等待活跃连接的阻塞；消息等待以原 3 秒时间界限代替 100 条消息上限。 |
| 31 | Vitest | 112 passed / 16 files，包含服务器合法选项、取消、技能切换、请求 epoch、失效目标与关键展示保留回归。 |
| 32 | Playwright | 18 passed，28.0 秒；真实本地 engine fixture + Edge，不是截图静态假页面。 |
| 33 | TypeScript | `tsc -b` 通过，作为 npm run build 的第一步。 |
| 34 | fresh Vite | 全新生产构建通过；prebuild 同步生产资源。见 build.log。 |
| 35 | production smoke | 本地 FastAPI 生产静态检查 PASS，头像 103/103、卡图 43/43。Worker 本地镜像已同步，逐文件字节一致性复核通过；没有部署。 |
| 36 | screenshots | 20 张最终 PNG，18 项截图需求映射见 screenshots/README.md。包含桌面、两个移动视口与专项交互证据。 |
| 37 | remaining issues | 无已知阻断失败。AI仍是轻量 heuristic，不保证达到真人竞技水平；描述全量结构/渲染校验不等同于逐技能形式证明；ViewAs生命周期采用共同状态机及代表实际技能回归，未做每个技能×每种终止路径的穷举；移动端复杂交互以430为主，390验证布局；托管浏览器图为fixture，真实宽限期驱动由服务器测试覆盖。建议后续真人长局评估。 |

## 卡牌表现审计范围

火攻、过河拆桥、顺手牵羊、五谷丰登、南蛮、万箭、桃园、铁索、决斗、借刀、乐不思蜀、兵粮寸断、闪电、无懈均复核现有 TargetTrick/TrickAction、combat projection、临时选择面板与判定事件路径。重点修改共用公开牌 renderer、判定亮牌/替换/结果，以及 AOE 目标开启事件；未为每张牌新增协议。

## 验收证据

- pytest_complete.log：最终完整 Python 运行；早期挂起日志不作为最终结果。
- vitest_final.log、build.log、playwright_final.log 与 playwright_report.json。
- pyside.log、ai_deterministic.log、targeted_final.log、production_smoke.log。
- ai_acceptance.json：60 场逐局 seed、武将、回合、决策数、胜者、快照与 projection 检查。
- skill_description_audit.json：103 将与189技能的非占位说明审计。
- audit_server.py 仅用于127.0.0.1验收；不加入正式应用路由。

仅创建本地稳定 checkpoint。没有 Sealos/Cloudflare 部署，没有开始下一轮扩将。

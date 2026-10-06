# T18A.11 release audit checkpoint — NOT RELEASE CANDIDATE

日期2026-10-06（Asia/Shanghai）；基线573164f。未签发`T18A.11 release candidate rules and interaction audit`：尚不满足用户全部完成标准。代码修复中间checkpoint：8f04076（T18A.11 intermediate Huashen eligibility recast and rules hardening audit），不是最终RC。

103将全部纳入矩阵，189唯一技能、192行（共享技能逐将及动态授予附加行）；只有化身专项完成独立获取规则闭环。不能把目录、189非占位描述、已有测试和压力覆盖说成189技能完整gameplay conformance。

当前剩余BLOCKED审计checkpoint：`1e81f90`；矩阵 **175 BLOCKED / 14 FIXED / 3 PASS**。本次新增关闭奇策、乱击、智迟；此前无言已关闭。累计33项基线缺陷根因已修复。定向日志分别记录95/120/213/124/157等批次，不能相加冒充一次全量运行。化身795专项未重跑；用户要求的最终七项门禁等待BLOCKED=0，当前没有签发RC。

以下checkpoint表保留`8f04076`历史统计，后续审计详情与当前状态见文末更新及rules_conformance_matrix.md。

| 用户要求 | 本checkpoint证据/结论 |
| --- | --- |
| 1 武将 | 103/103目录；两种正式draft各200seed覆盖103/103；全员独立规则审计未完成 |
| 2 技能 | 189已注册、非占位；规则矩阵192行，1 FIXED、191 BLOCKED；化身90形式157原生技能及1派生展示条目资格已核验，139允许、18禁止、1派生禁止（不等同逐项技能效果 conformance） |
| 3 卡牌 | 43定义/160实体；card_audit.json全目录，逐定义独立来源闭环仍BLOCKED |
| 4 官方/锁定来源 | sources.md；使用锁版本和固定revision社区资料，未取得完整官方历史卡面，未复制外部实现 |
| 5–9 差异 | 9个真实缺陷已修复；6规则结算/成本、1死亡状态、1Web交互、1Windows运行时；已发现未修复产品缺陷0；未审计项不是已知缺陷0的证明。版本升级0；化身池基线已经90，属于防护明确化 |
| 10 ViewAs | 原选择状态与Web取消回归通过；全部转化技能组合压力闭环未完成 |
| 11 左慈 | 795专项测试；90逐名可达、12神/本人/在场/重复排除、未来registry无需名单、死亡和重连清理；基线90正确。高风险奇袭取消真实浏览器通过。所有取得技能组合行为仍未逐一人工核验 |
| 12 基本牌 | Golden suite涵盖三杀、酒杀、救援等；完整独立来源核验未完成 |
| 13 锦囊 | 现有回归+Golden+浏览器部分通过，逐卡规则闭环未完成 |
| 14 装备 | 装备链Golden、废栏回归通过；四装备槽为当前卡组范围，无宝物新增 |
| 15 无懈 | 三层链/奇偶/逐目标及root作用域回归通过；Web单/群体按钮验证通过 |
| 16 火攻 | AI展示、花色成本、无花色失败、刷新恢复浏览器通过 |
| 17 过拆 | 隐藏选择与弃置后公开呈现回归及截图通过 |
| 18 顺手 | 隐藏牌背及刷新选择浏览器通过；不把获得隐藏手牌公开 |
| 19 AOE | 南蛮/万箭当前目标、无懈窗口浏览器通过；Golden续算通过 |
| 20 五谷 | 顺序公共池Golden及面板浏览器通过；所有死亡/超时人工截图未完成 |
| 21 判定 | 多类判定/延时牌Golden通过；本轮未补齐独立最终判定截图 |
| 22 濒死 | 杀闪/救援/连环Golden通过；所有嵌套死亡来源独立审计未完成 |
| 23 死亡 | 处罚、摧克终局、阶段结束终局、化身私密清理修复；死亡请求合法例外为追忆、武魂，不能强删合法死亡技能 |
| 24 CardMove | 每模拟步GameState守恒验证；已枚举直接位置写入：正式移动集中CardMoveService/装备事务；观星仅同区排序；胆守/武圣距离探测为隔离副本；神吕布review fixture为显式本地准备路径。动态别名写入与全技能事件语义闭环仍待补 |
| 25 Projection | 已有全量隐私回归通过；并非103将完整逐字段hidden-info audit |
| 26 hidden info | 顺手/过拆/火攻/化身已有证据；新增103将×5/8人基础JSON载荷对隐藏牌面/ID/顺序/身份扰动209测试通过；特殊技能动态grant及所有事件路径全审计未完成 |
| 27 reconnect | 武圣修复后AI和随机对局定期snapshot restore、90名化身逐名重复/在场恢复；全部列举状态中途刷新仍未补齐 |
| 28 offline takeover | 现有真实grace/token回归通过；浏览器托管状态截图；并非全部request真人接管全景验收 |
| 29 AI | 5人50+8人50完整固定seed，0死锁/终局未清请求/异常；隐藏身份不变性现有测试通过；全189技能策略合理性未完成 |
| 30 布局 | 底部右侧本地将、空中央；5/8人及390/430截图；完整移动版参考视觉签收未完成 |
| 31 手牌 | 12张桌面轻重叠截图通过；名称、花色、点数可见，hover/selected沿用现有逻辑 |
| 32 装备区 | 四槽满装备、马+/-截图；装备与判定更清晰独立区域仍需继续细审 |
| 33 103选将 | 正式创建多人房间→AI补满→选将确认→完整初始角色和服务器第1回合，5人10+8人10；首画面可已进入后续回合，因为AI先行动 |
| 34 Golden | 50个指定行为节点、参数化后74项通过；复用测试不替代来源核验 |
| 35 invariant | 每步实体区域唯一/总数守恒，废栏无装备，请求主存活（追忆/武魂合法死亡例外）；不声称瞬时current player必须存活 |
| 36 random | 100场合法随机动作、固定seed；0死锁/终局请求/异常；生成器上限取实际候选数，避免生成非法sample |
| 37 pytest | 重铸修复后全量2477 passed（188.33秒），pytest_after_recast.log/XML；其后新增140项化身切换/超时测试单独通过（化身专项共795 passed）；基线1585 passed |
| 38 Vitest | 16 files、114 passed；新增重连座位未确认的重复面板复现 |
| 39 Playwright | 42 passed（43.6秒），包含20次正式选将及重铸目标刷新；playwright_after_recast.log、playwright_report.json、screenshots/ |
| 40 PySide | 已在全量pytest执行PySide回归；本轮未完成全部人工桌面截图与Web逐场景对照 |
| 41 TypeScript | npm run build中tsc -b通过 |
| 42 Vite | fresh生产build通过；web_build.log |
| 43 production | FastAPI生产配置+静态bundle smoke通过，103立绘/43卡面HTTP通过；生产环境镜像构建/部署未执行 |
| 44 Worker | 111 Python文件逐内容一致；镜像同步仅本地，不部署 |
| 45 remaining | 191矩阵行及43卡定义缺独立来源/语义/人工闭环；完整18类最终截图未齐（缺独立最终判定、临时废栏等）；全部reconnect/timeout类型人工闭环未齐；中文字符串总扫描未完成；Windows断开异常已通过显式Selector工厂修复；42场景最终服务器日志无Traceback |

## 测试与日志边界

Simulation详情见simulation_summary.json、ai_acceptance.json、random_simulations.json。每局记录winner/turns/decision steps/最大单步处理耗时/timeout fallback验证数/重连数；`max_pending_duration_seconds`是AI单步处理耗时，不冒充真人等待窗口的最大停留时间；timeouts=0表示该即时AI跑法没有实际等待超时，fallback每次验证合法。覆盖数量见summary，不推断未抽到角色。

复现日志保留真实失败用于证据，不能宣称整个目录没有Traceback。最终pytest、AI、随机对局无未处理引擎异常；首次浏览器服务器出现Windows Proactor断连清理WinError10054；显式Selector工厂及新规则修复后的42场景，browser_server_after_recast.log为空，未静默抑制异常。Vitest有jsdom无canvas的环境诊断；Node NO_COLOR/FORCE_COLOR warning；FastAPI TestClient依赖deprecation warning。均未静默抑制。

最终浏览器页面截图已查看底部满装备12手牌8人桌、390屏8人布局；其余输出截图并非全部逐张人工签收。未扩将、未新增卡牌、未重新生成立绘或动态、未部署Sealos或Cloudflare。既存美术和未跟踪日志保留。

本次继续：补齐姜维派生观星权限、铁索/连环重铸结算分类；795项化身专项及209项基础隐藏信息专项通过。最新100 AI+100随机整局覆盖合计103将，步数和重连指标已更新simulation_summary.json。42场景浏览器控制台/pageerror断言为零，重铸卡面截图已人工查看。首次新增重铸浏览器失败来自夹具提前合并提交及对不存在prompt的否定断言，不计产品缺陷。首次构建因系统Python缺Pillow失败，使用项目现有.venv重新fresh build通过，未安装依赖。完整2477项pytest运行后仅新增140项化身权限/timeout测试，单独已通过；没有冒称合并全量2617项曾整批执行。

2026-10-06继续剩余BLOCKED审计：当前3 FIXED、1 PASS、188 BLOCKED。本轮无懈/AOE首批修R08–R12，326相关AOE回归及40无懈/作用域回归通过；只属中间证据。未重跑化身795，未执行最终全量门禁，未签发RC。以上checkpoint表保留8f04076历史统计，最新详情见aoe_source_notes.md及矩阵。

继续判定/延时锦囊批次新增R13–R16，judgment_targeted.log 325 passed；当前仍188 BLOCKED。没有完成总规则闭环，不签发RC。

继续锦囊被动规则：无言延时锦囊及经典蛊惑帷幕例外R17/R18已修；当前186 BLOCKED、4 FIXED、2 PASS；384相关回归 + 35项禁止组合回归通过。仍不是RC。

贞烈目标确认分层R19及R10用牌事件补齐完成；当前185 BLOCKED、5 FIXED、2 PASS；multitarget345及zhenlie60相关回归通过。未签发RC。

延时牌处理区时序R20与当前无双响应冻结R21修复，无言类型边界闭环。当前184 BLOCKED、6 FIXED、2 PASS；相关407/91/250/118是独立定向批次统计，不合计为一次全量。未运行最终门禁或签发RC。

流离成本后距离与非法目标R22/R23修复，相关157通过；R21多目标无双冻结回归269通过。尚184 BLOCKED，不签发RC。

奇策/乱击来源、完整候选与成本边界闭环，新增R24–R26；当前182 BLOCKED、8 FIXED、2 PASS。95/120分别为定向批次，不相加冒充全量。最终门禁仍未运行，不签发RC。

智迟R27–R29及12个独立边界测试闭环，相关213（含80场AI）及追加反例124通过。当前181 BLOCKED、9 FIXED、2 PASS；定向结果不冒充最终全量。未签发RC。

判定收尾R30/R31修复，相关157通过；同人改判/FinishJudge全顺序待核，矩阵仍181 BLOCKED。未重跑化身795专项，未执行最终全量或签发RC。

共享用牌/响应/ViewAs第一批关闭6项，新增公共根因R32–R36，279相关定向通过；当前175 BLOCKED，系统队列剩余项仍待多目标/判定/特殊牌堆依赖闭环，未宣称完整系统已清零。版本/夹具/产品bug分类见view_as_system_audit.md；未重跑化身795、full pytest或最终七项验收。

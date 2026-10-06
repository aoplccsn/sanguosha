# T18A.11 final rules closeout audit

基线：代码974bc0c、报告9195e9f、153 BLOCKED。直接解析基线 Markdown 的全部 BLOCKED 行，与JSON一一对应；原始Markdown指纹保存在矩阵 final_audit。153条逐项结论、锁定条款、版本档案、实现位置和已有行为证据见 final_rule_clauses.json。未把共享依赖通过自动当作逐技能结论。

本轮关闭 **127 PASS / 26 FIXED**；最终总表 **142 PASS / 50 FIXED / 0 BLOCKED**。PASS沿用足够的来源、已有用例及代码证据；智愚采用完整独立代码与固定YJ2012条款核对，不伪称有未存在的直接测试。宗室手牌上限为即时有效势力集合修正。派生急袭、极略、排异均按母技能授予权限独立关闭。既有FIXED保留历史根因来源，不将修过的实现改记为从未出错的PASS。

本轮 **11个真实基线根因**，累计79。代码checkpoint：49f0bb0。22个新增最小复现只对应真实差异；六个既有用例更新为正确的选择顺序、空栏放置及救援座次契约。所有原有美术及未跟踪资料保留；未扩将、部署、重构架构或创建新专项。

## 组合规则及版本裁定

- 同角色判定多技能顺序：历史《规则集3.0》结算原则明确由该角色决定同一时机操作顺序，并以天妒/颂威、洛神/颂威举例。来源：https://gltjk.com/sanguosha/rules/rule/principle.html 。这不是引入现代改版；历史QS程序的稳定排序属于实现差异，不能取代规则文本。共用选择方法同时服务改判和FinishJudge；单技能请求不变。已选择、已问列表、当前最终牌及顺序请求均由已有frame快照恢复。
- 改判：从当前回合角色按座次，NotActive当前后置；同人多个合法技能可自行先后，消耗和材料按当时状态核对；鬼道交换旧牌，最终判定用被判定者上下文。经典鬼才使用手牌，不混入现代鬼才装备成本。
- FinishJudge：天妒为可选取得，屯田/洛神为对应判定的独立取得；颂威是被判定者决定发动/先后。牌已取得后不再询问取得同一张牌。经典身份局只有一名合法主公，构造多主公不是本轮新范围。
- 夺锐/止啼：锁定drlt版与项目四装备栏版本；不套OL改版。普通原生技能筛选、废栏装备离开触发、每人单租约、目标回合末/死亡恢复、借者死亡失去技能但目标失效保留到期、止啼三类事件与真实范围，均与已有组合用例/有效权限服务核对。临时、既有授予及原生同名技能按来源各自保留，不整项删除。
- 全部剩余孤立技能沿用锁定classic条款；Nos旧标准差异、旧/OL/non-drlt神将差异不合并升级。档案字节指纹见final_sources.json；规则文本因原始HTTP403无字节指纹，仅保留已读主文本引用。社区实现档案并不冒充发行商原始卡牌来源。

## 公共交互闭环

Projection: 其他人的手牌仅计数；攻心/魄袭显式观察者可查看指定手牌，授权要求双方存活、有效技能。star和committed牌堆及化身池仅持有者可见；田、权、逆、酒及不屈牌是各自规则公开牌堆，不误当私密。规则公开展示只进入公开事件/历史，不建立永久手牌观察权。现有209隐藏信息用例及星、蛊惑、魄袭、宗玄中途恢复证据复用。

Reconnect/timeout/AI: 数据快照包括权威阶段、PendingRequest、frame局部选择、使用次数、技能源及租约；恢复同一request identity。超时通过原Decision合法值执行，去重凭request/revision，当前未提交选择由已有客户端状态处理。15秒断线宽限、实际AI解答当前请求、原token重连恢复真人及同一PlayerState已由现有真实托管用例核验。死亡/终局由共享引擎门控停止普通请求并清暂存牌，保留武魂等死亡窗口直到终局裁定。未添加猜测的并发状态测试。

## 复现及验证边界

首批允许狂暴借取的探针经unique来源核对判定不合法，已移除；无前借取保留怒路线依赖该非法前提，也移除，对应额外主动防御测试与改动撤销。留下狂暴禁借、断肠失效、大雾失效三条合法发现。基线失败日志只保存最终保留的真实复现。龙魂目标p3超过普通距离、成本预览丢失实体牌位置，以及无技能会话依赖遗漏属于夹具/开发中错误，修正后不加入基线bug数。

最后必要定向回归：**560 passed in 22.86s**，涵盖上述修复及隐私、快照、多人托管。不相加早期重复选择。化身专项795仅核对收集数量，完全不执行；其既有证据保留。

## 最终七项验收与签发

**T18A.11 release candidate rules and interaction audit — ISSUED**

代码checkpoint：49f0bb0。2026-10-07（Asia/Shanghai）完成全部门禁：

| 验收 | 结果 | 证据 |
| --- | --- | --- |
| full pytest | PASS：2186，206.80s；按用户要求排除左慈795，其他tests完整执行 | final_pytest.log / final_pytest.xml |
| Vitest | PASS：16 files / 120 tests | final_vitest.log |
| Playwright | PASS：42，44.2s；最终代码重启服务后执行 | final_playwright.log / playwright_report.json / screenshots |
| TypeScript | PASS：tsc -b，exit 0 | final_typescript.log / final_acceptance.json |
| fresh Vite build | PASS：已有production资产同步后重新构建，exit 0 | final_vite_build.log / final_assets_build.log |
| PySide smoke | PASS：实际offscreen MainWindow启动并自动退出，exit 0 | final_pyside_smoke.log / final_acceptance.json |
| Worker mirror consistency | PASS：112文件路径及SHA256全部一致 | worker_mirror.json |

首次沙箱临时目录权限失败保留在full_pytest_environment_failure.log。项目目录首轮完整验收2176通过/10失败；六个AI终局失败是R77的既有复现，四个过时救援断言按已锁定座次更新。166项相关回归通过后重新完整执行2186，全部通过。日志full_pytest_before_closeout_fix.log/xml保留。没有新增R77测试，没有运行左慈795，没有扩将、改美术或部署。Worker另四个既有镜像漂移文件同步主实现以完成镜像门禁，不扩展主实现修复范围。


新增R76：同角色鬼才和极略复用改判公开事件身份，前端usePresentation/CombatVFX的已播放集合会吞掉第二次改判。单一公共事件身份根因；identity_reproduction.log基线1失败，identity_targeted.log 82通过。已按实际改判技能区分移动和公开事件ID。

R77：最终完整Python回归的六个既有AI对局实际复现终局回合中断后陷阵/智迟标记残留。公共terminal cleanup复用既有clear_turn，不新增测试。另四个旧救援断言已按既有座次询问规则更新，未改动救援实现、不计新bug。首轮环境权限失败及完整回归10失败日志均保留。

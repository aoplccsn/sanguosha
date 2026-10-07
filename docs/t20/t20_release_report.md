# T20 release report

日期：2026-10-07。基线e8b8570，开发分支t19-overpowered-generals。

## 实现

DUEL_1V1/TEAM_2V2完成。统一mode config提供座数、公开阵营、队伍解析、角色分配与胜负规则；复用权威死亡时序、卡牌/技能/距离、选将、AI补位、快照、断线托管与重连。两真人2v2默认p1/A与p2/B，队伍不随榻谟座次调整而改变。无主公或身份奖惩。终局不继续普通请求或阶段。

Web新增四模式入口、公开队伍徽记、人数与2/4座相对布局，保留本地手牌装备、立绘、动态与fallback。PySide本地模式选择及动态座数同步。108将均参与小桌完整对局；没有扩将、禁将、复制卡牌、开启全量技能审计或改平衡。

## 发现与修复

- 旧开局必须找主公、Pregame.lord_id必须存在：新模式无主公，改用持久化先手与可空lord_id，保留身份局路径。
- Worker原来落后于T19.2：补齐现有5%超标位、受保护测试房状态、榻谟存活座次条件，并同步T20。镜像与authoritative源码逐文件一致。
- 旧浏览器验收仍预期8个神将，且mock只拦截旧room URL：更新为当前17个神将与/ws创建协议；重连验证等待第二个连接和恢复大厅，避免依赖短暂toast。
- 首次本机npm build使用非项目Python缺Pillow：使用项目已有venv成功fresh build，未安装新依赖。

## 验收结果

- Python full pytest：3057 passed，241.29秒；最后涉及mode/Projection/Worker/PySide相关45项通过，新增榻谟全角色座次、队伍无懈/AOE覆盖后T20共18项通过。无T18A.11审计重跑。
- Vitest：17 files / 124 passed。TypeScript与fresh Vite production build通过。
- Playwright production回归：15/15 passed，含T20五条真实流程、原双真人游戏、选将资源、短连接恢复、受保护测试房。新桌面/390px截图已目视检查，无水平溢出；历史Cloudflare mock/HMR/审计文件不作为本次production套件。
- PySide offscreen：1v1/2v2分别仅显示2/4角色面板、可安装引擎与正确座数，PASS。
- Worker mirror一致性通过。生产HTTP资产108/108立绘、44/44卡牌通过；全部现有动态视频Range206通过，神郭嘉继续原静态fallback。

## 完整AI对局

结果见ai_acceptance.json：1v1 20/20、2v2 20/20终局，108/108将覆盖；无死锁、traceback或残留PendingRequest；存活队伍与胜者一致，含周期Projection/快照恢复检查。

| 模式 | 平均行动回合数 | 先手阵营胜率 | A胜率 | B胜率 |
| --- | ---: | ---: | ---: | ---: |
| 1v1 | 14.80 | 65% (13/20) | 45% | 55% |
| 2v2 | 23.35 | 50% (10/20) | 50% | 50% |

这是分将固定种子的smoke观察数据。先手胜率仅是观察指标，不根据几十局AI结果过拟合平衡。

## 发布与部署

按请求提交“T20 duel and 2v2 team modes”并push当前开发分支；沿用生产GHCR工作流生成完整HEAD SHA标签。最终SHA、镜像digest、工作流结果及Sealos实际部署状态在交付时核实，并写入本地deployment_status.json。

Sealos仅允许修改sanguosha-cn的image，保持1副本、8000与原DOMAIN/PUBLIC_ORIGIN/SECRET_KEY/SANGUOSHA_TEST_ACCESS_CODE。公网只有实际更新成功后才验收，旧版本不计作T20通过。

已知非阻塞项：神郭嘉继续原静态fallback；小样本AI胜率不能代表平衡；桌面多人窗口仍沿用既有TCP/Relay入口，本轮新增模式选择主要是Web与PySide本地入口。

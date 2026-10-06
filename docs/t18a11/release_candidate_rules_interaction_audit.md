# T18A.11 release candidate rules and interaction audit

ISSUED — 2026-10-07 Asia/Shanghai

代码checkpoint：49f0bb0；报告checkpoint为包含本证书的Git提交。

基线153 BLOCKED全部闭环：本轮127 PASS / 26 FIXED；最终142 PASS / 50 FIXED / 0 BLOCKED。本轮11个真实根因；22个新增最小复现，R77沿用既有真实失败，没有新增防御测试。

2026-10-07（Asia/Shanghai）完成全部门禁：

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

逐条证据：rules_conformance_matrix.md、final_rule_clauses.json；差异账本：rule_differences.md；机器可读门禁：final_acceptance.json。

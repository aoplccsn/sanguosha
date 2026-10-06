# T19 release report

日期：2026-10-07。代码与本地验收完成；生产部署尚待 Sealos 可用登录会话。

- 基线包含 49f0bb0 与 94facbc，分支 t19-overpowered-generals；没有回退 T18A.11。
- 正式 roster 108/108。神鲁肃、神太史慈、神孙策、神郭嘉、神荀彧新增；神司马沿用 mountain_god_simayi，旧忍戒/临时极略已替换。
- 六将使用当前移动版正式服规则，详见 rules_lock.md 与 simayi_source_evidence.json。使用现有 ResolutionStack、PendingRequest、技能来源、CardMove、Damage、Recover、Judgment、VirtualCard。
- 六将核心技能、中文资料、AI、Projection、私有选择、snapshot/reconnect、死亡清理已实现。派生神著取得后生效；极略永久技能按独立来源保存。
- 超标位概率 0.25，每次十选至多一名；太史慈/孙策/司马/郭嘉/荀彧权重 10/8/7/6/4，集中配置 general_draft.py，Pregame 和 Room 共用 authoritative RNG。
- 鲁肃普通池、metadata 显式允许化身；超标五将禁止化身；基础化身池 91，生产算法动态推导。
- 动态鲁肃、太史慈、孙策、荀彧接入 panel/detail/选将与 manifest；复用既有司马视频。总动态17套。未修改用户 master，未生成美术。
- 神郭嘉缺失 god_guojia_idle.mp4，暂用既有郭嘉静态画作 fallback。PySide已补齐PlayerPanel、GeneralDetail和选将的原生循环视频，安装项目gui extra所需的官方PySide6-Addons后实测五将各收到20–25帧；郭嘉静态回退。没有Multimedia的精简安装继续静态回退。Web视频已实测播放。奇正相生暂用卡牌通用图 fallback。

## 验收

- 六将 targeted 33 PASS；集中抽样14 PASS；受影响经典神将58 PASS；化身受影响子集51 PASS。
- full pytest 仅运行一次：3025 PASS / 5 FAIL；五项均为旧版极略或旧 roster/化身数断言，更新后相关9项 PASS。后续必要修复：31项 PASS，包含 Worker；PySide108详情及司马/荀彧共115项 PASS。
- Vitest 16 files / 120 PASS；TypeScript PASS；fresh Vite production build PASS。
- Playwright 基线正式验收40/42，神将第0回合势力选择适配后两项定向重跑2/2 PASS；T18B验收10/11，资源数适配108/44/17后剩余1/1 PASS；T19六将两种尺寸立绘、资料和刷新重连2/2 PASS。
- 旧全目录 Playwright 含 Cloudflare mock、历史固定seed和HMR开发测试，不适用于 FastAPI production bundle；尝试后停止，不把该错误模式记为正式通过。
- PySide offscreen启动 smoke PASS。Worker mirror同步且一致性测试 PASS。
- 生产HTTP资产108/108立绘、44/44卡牌 PASS，17套视频与Range206 PASS。
- AI40场：军五20、军八20，六将均覆盖；全终局，无残留PendingRequest，详见 ai_acceptance.json。

## 发布

代码checkpoint：0c904fe42345222598948e15025f28fb2397a09e，提交名 T19 overpowered generals and dynamic portraits，GitHub push成功。

GHCR生产工作流37538412659 SUCCESS；匿名registry读取完整SHA标签HTTP200：ghcr.io/aoplccsn/sanguosha-cn:0c904fe42345222598948e15025f28fb2397a09e，digest sha256:f8ce7a57828a70b8efc90b24699894c5402ff23e30ef47c9aa32a057de75664c。本报告后续提交同样触发完整HEAD SHA生产构建，最终交付摘要以最后核实的SHA标签为准。

额外必要最终检查：六将+draft+Worker共43 PASS；真实生产服务器两浏览器WebSocket开局1 PASS。

唯一剩余外部阻塞：Sealos部署登录不可用。公网health HTTP200/status ok，但catalogue为76，将此结果明确记为旧部署，不能算T19公网通过。Sealos目标保持 sanguosha-cn、北京、1副本、8000及既有域名/环境变量/SECRET_KEY。当前没有 kubeconfig，浏览器落在signin且页面控制多次超时；未改动生产应用。公网T19验收尚未执行。

最短用户动作：登录 https://bja.sealos.run 北京现有账号，再继续本任务；无需改规则、重跑开发或重新准备美术。只更新 sanguosha-cn 的已核实SHA镜像，保持现有配置，然后执行T19公网smoke。

后续完成审查补齐：原生视频按同一manifest加载、无音频、隐藏时暂停；实际帧证据 pyside_video_smoke.json。Native详情势力显示使用当前Projection。

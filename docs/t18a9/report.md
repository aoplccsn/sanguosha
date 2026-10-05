T18A.9 production assets and choice interaction polish

分支：`t13-complete-roster-multiplayer`。本轮完成生产资源路径、紧凑事件牌、临时选择面板及提示生命周期修复。未修改规则、AI pacing、动态 Master 或多人协议；未部署公网、Sealos、Cloudflare，也未开始 T17C。

| 序号 | 验收项目 | 结果与证据 |
|---|---|---|
| 1 | 武将破图根因 | Docker assets stage 执行 development 同步，输出 PNG；生产 React 却强制改成 WebP，仅已有 WebP 的武将正常。本地 production 同步转换后，catalog 又仍返回 PNG。前端现从同步 manifest 取实际路径；catalog 从 production dist manifest 返回实际地址。Docker 改用 Pillow + production 同步。 |
| 2 | 76 将 production | 76/76，不同 URL，HTTP 200、正确 image/webp 类型、文件非空；无统一默认图掩盖。读取实际 `/api/catalog/generals` URL。 |
| 3 | 手牌美术根因 | 同一 Docker PNG/WebP 不一致影响卡图；组件还自行拼接卡面路径并通过默认图遮盖失败。现映射 card definition 到 manifest 注册美术，移除手牌和中央牌的错误默认图替换；减轻不可用牌灰度以保留美术可读性。 |
| 4 | 卡图 production | 全部 43/43 注册卡面通过真实 HTTP，包括杀、闪、桃、酒、全部锦囊和装备类别；manifest 所有注册路径文件存在。 |
| 5 | 中央牌修改前 | 桌面 clamp(120px,10vw,155px)，矮屏覆盖 125px；手机 clamp(78px,23vw,105px)。 |
| 6 | 中央牌修改后 | 桌面 clamp(85px,6.5vw,110px)，1440 宽约 93.6px；手机 clamp(58px,16vw,78px)，390 宽约 62.4px，430 宽约 68.8px。事件层及子元素 pointer-events:none。现有 3–5 秒可读 pacing 未变。 |
| 7 | 顺手牵羊 | 独立 TemporaryInteractionPanel；手牌/装备/判定分区，暗牌背点击高亮，再确认提交原有 Decision；装备可选并由服务器转移到自己手牌；禁止伪取消。桌面、390×844、430×932 通过。 |
| 8 | 五谷丰登 | 公共牌池临时面板，固定标题/当前 chooser/倒计时/底部控件；内容区滚动，卡牌自动换行。8 位真人 sequential selection 全部通过，仅当前 chooser 可选。额外覆盖取得无懈后服务器发出响应请求，面板内仍可使用现有响应牌及控件。 |
| 9 | 隐藏信息 | 自己完整 CardView；其他玩家无隐藏 hand、art、definition、suit、rank；顺手请求仅 hidden-hand:N 位置别名，不含真实隐藏实例 ID。Python 和浏览器 wire 验收通过，未改 Projection。 |
| 10 | 五谷刷新/重连 | 第二位 chooser 刷新后恢复 7 张剩余牌、当前 chooser、剩余时间与 PendingRequest；已取牌未回流，八人选完面板关闭。已有区域状态保存取得的牌；没有新增拿牌历史协议字段。 |
| 11 | 响应通知常驻原因 | notice 清除 effect 遇到 decisionAccepted 就退出，该标识可能保留至下次 Projection；stale 错误还会进入没有自动过期的 error 区。 |
| 12 | 响应通知修复 | 去掉 decisionAccepted 对通知定时器的阻断；短 notice / 本地交互提示 1200ms 后清除；stale/expired/duplicate 仅使用短 notice。提交处理中仍保留真实进度。 |
| 13 | snapshot spam | 普通 PendingRequest 替换不再创建“当前响应已更新”；同 request snapshot/deadline 更新不创建 toast。Vitest 与 Playwright 验证。 |
| 14 | 恢复中常驻原因 | offline handler 先 disconnect 再回首页，清掉 offline 状态与可重试连接信息；socket open 过早 reset failures，并把尚未恢复会话当成已连接，反复开/关可能无限循环。 |
| 15 | 成功恢复生命周期 | 重连 socket OPEN + 带座位/token 的 WELCOME + 恢复 snapshot/lobby/draft 后转 connected，立即清除恢复中；“连接已恢复”1200ms 后清除。真实 socket 断线恢复验收通过。 |
| 16 | 失败恢复终态 | 握手/恢复等待上限 8 秒，连续失败 6 次转 offline。保留旧牌桌与重连信息；显示“连接已断开。”和“重新连接”按钮，结束恢复中。覆盖持续无法恢复和打开却没有 snapshot 的测试。 |
| 17 | 桌面截图 | slash-desktop.png、snatch-1440.png、harvest-desktop.png；1440×1000 的完整八人牌桌/目标青白框/回合金框与真实美术可见。 |
| 18 | 手机截图 | slash-390.png、slash-430.png、snatch-390.png、snatch-430.png、harvest-390.png、harvest-430.png；390×844 / 430×932，面板确认在 viewport 内，牌池自动换行，中央牌符合尺寸范围。 |
| 19 | Python | 78 passed：production resources、hidden info、multiplayer、choice labels、T17B production、T18A.6/.7。见 pytest.txt。不是整个 Python 仓库全量运行。 |
| 20 | Vitest | 15 files / 86 passed，包含临时面板、手牌交互、通知、重连握手与有限失败、已有 pacing/动态画像回归。见 vitest.txt。 |
| 21 | Playwright | 10/10 passed，FastAPI 托管 production dist；全量资源、3 个视口暗牌选择、公开装备、8 人五谷/刷新、中央牌/真实恢复、toast 去重/失败终态、拆桥、五谷无懈中断。见 playwright.txt。 |
| 22 | TypeScript | tsc -b 通过，包含在 production build 中。 |
| 23 | fresh Vite | 新端口 5179 启动成功；入口、main.tsx、assets.ts、slash.png 均 HTTP 200。随后重新生成 production public assets/dist，未只凭 dev 验收生产。 |
| 24 | production static smoke | 本地 127.0.0.1:8009 FastAPI dist；`scripts/smoke_production_assets.py` 输出 portraits 76/76、card_art 43/43 PASS；见 production-smoke.txt。使用同一 FastAPI static mount，非 Vite preview。 |
| 25 | Docker / GHCR | Dockerfile 已修正，frontend 使用 assets stage 的 production manifest 与 WebP。此机器无可用 Docker CLI，未构建 Docker 镜像、未运行 GHCR Actions，镜像运行层仍需后续验证。没有公开部署。 |
| 26 | Remaining issues / 边界 | 未在物理手机及真实公网断网环境验收；手机采用 Chromium viewport，失败网络采用 WebSocket 故障注入，成功恢复走真实本地 socket。Vitest 有原有 jsdom canvas 提示，全部通过。共享 rule/multiplayer Python 未改，无需 Worker mirror 同步。没有新增武将或规则。 |

复验：在项目根目录用 `.venv/Scripts/python.exe docs/t18a9/audit_server.py` 启动仅本地 fixture。production build 应使用项目 venv Python：将 `.venv/Scripts` 放到 PATH 后运行 `npm --prefix web run build`。浏览器验收在 web 目录设置 `BASE_URL=http://127.0.0.1:8009`，执行 `npx playwright test e2e/t18a9-production.spec.ts`。HTTP smoke：`.venv/Scripts/python.exe scripts/smoke_production_assets.py http://127.0.0.1:8009`。

所有 fixture 只在 docs 中供本地测试，未导入 production app；测试时选择时限设为 300 秒，以允许建立八个独立浏览器席位，不改变产品 pacing。

干净 checkout 的 Vitest 入口新增 pretest 同步，避免忽略的 web/public/assets/manifest.json 缺失；prebuild 与 Docker assets stage 仍生成 production manifest。

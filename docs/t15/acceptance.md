# T15 — Dynamic Idle Portrait Integration

2026-10-04，Asia/Shanghai。**9/9 正式动态待机素材已接入；完整阶段验收仍有性能与原生桌面可见性两项未通过。**

基线：T14.2 `b763284f16905821ee3e501f172b075e6c869d6a`（747 Python passed）；功能 checkpoint `fbf53aaac52c9f8e1dfa9f8c57a66bf2af412937`。
本轮接续代码 checkpoint `374f6074d67e719166ef9dce6a4e541110e34584`，分支 `t13-complete-roster-multiplayer`，worktree `C:/Sanguosha`。
最终 Git hash 在交付消息和 git log 中提供。未部署公网，未 push。

## 原体系与复用

PlayerPanel 和游戏内 GeneralDetail 原先均使用静态 img；`web/src/assets.ts` 通过 catalog portrait / kingdom 解析路径，production 使用 WebP。
Qt `ResourceManager` 读取 `assets/manifest.json` 为静态 QPixmap 提供 fallback，与浏览器视频无关，未修改。
审计了 T11 GodPortrait、GodCinematic、CombatVFXLayer、CombatVFXRuntime、选将、图鉴/列表、general registry、resolver、manifest、production sync 与 `docs/t11/acceptance.md`。
T11 的 GodPortrait 是分区 SVG/PNG 原型，没有原生 video 实现可补完；本轮使用唯一的 `web/src/components/DynamicPortrait.tsx` 实现正式原生待机视频。
复用现有 High/Medium/Low 状态及静态 resolver；保留旧 T11 美术预览、非 idle 演出和 Combat Canvas，没有把视频绘入 Canvas，没有重写 Slash/Dodge/beam。

## 九名角色与正式路径

稳定 ID 来自 `src/sanguosha/content/characters/myth.py`。张角保持 `wind_zhang_jiao`，没有创建神张角。

| general | registry id | static PNG | cleaned runtime MP4 | runtime bytes |
|---|---|---|---|---:|
| 神吕布 | `forest_god_lvbu` | `assets/generals/qun/forest_god_lvbu.png` | `assets/portraits/idle/forest_god_lvbu.mp4` | 7,771,456 |
| 神赵云 | `mountain_god_zhaoyun` | `assets/generals/qun/mountain_god_zhaoyun.png` | `assets/portraits/idle/mountain_god_zhaoyun.mp4` | 4,946,785 |
| 神周瑜 | `fire_god_zhouyu` | `assets/generals/qun/fire_god_zhouyu.png` | `assets/portraits/idle/fire_god_zhouyu.mp4` | 5,309,640 |
| 神诸葛亮 | `fire_god_zhugeliang` | `assets/generals/qun/fire_god_zhugeliang.png` | `assets/portraits/idle/fire_god_zhugeliang.mp4` | 5,541,704 |
| 神曹操 | `forest_god_caocao` | `assets/generals/qun/forest_god_caocao.png` | `assets/portraits/idle/forest_god_caocao.mp4` | 5,445,257 |
| 神司马懿 | `mountain_god_simayi` | `assets/generals/qun/mountain_god_simayi.png` | `assets/portraits/idle/mountain_god_simayi.mp4` | 4,823,576 |
| 神关羽 | `wind_god_guanyu` | `assets/generals/qun/wind_god_guanyu.png` | `assets/portraits/idle/wind_god_guanyu.mp4` | 6,630,502 |
| 神吕蒙 | `wind_god_lvmeng` | `assets/generals/qun/wind_god_lvmeng.png` | `assets/portraits/idle/wind_god_lvmeng.mp4` | 5,546,714 |
| 张角 | `wind_zhang_jiao` | `assets/generals/qun/wind_zhang_jiao.png` | `assets/portraits/idle/wind_zhang_jiao.mp4` | 7,254,438 |

上述每个 MP4 均为 **H.264 High / yuv420p，720×1280，24/1 fps，10.000 秒，audio=no，faststart=yes**。
每个 runtime 的完整 ffprobe codec/pixel/resolution/fps/duration/size/audio 和 source probe 见 `media_report.json`。
九个 runtime 总量 **53,270,072 bytes**；最大为神吕布 **7,771,456 bytes**。
母带总量 54,774,173 bytes，全保留在用户提供的外部源目录；没有 source MP4 进入 dist。

## 源文件保护与 static Master 匹配

用户提供了九个 MP4，没有单独静态 Master。九个源 SHA256 审计前后完全一致，未覆盖、修改或删除。
神吕布动态版明显不同于旧静态造型。九名角色均从其最终视频首帧生成匹配的正式 PNG 与 WebP fallback；PNG 为 720×1280，像素与视频提取首帧完全相同。
旧静态备份仅放在本任务 workspace 的 `portrait_source_audit/static_before`，不进入生产/提交。原 T11 六个未跟踪源目录保留原样，不提交。
静态来源、pixel SHA256、source SHA256、runtime SHA256、first-frame 时间戳与更新标记均写入 `media_report.json`。production static 路径为表中 `.png` 对应 `.webp`。
九个 runtime 都优先 **stream copy**：`-map 0:v:0 -c:v copy -an -movflags +faststart`，音轨真正移除；编码视频 payload 的 SHA256 与母带一致。
保留原比例、24 fps、10 秒内容；没有改播放速度、裁剪时间、JS seek 或前端插帧。

用户确认未安装 ffmpeg/ffprobe 后，明确授权下载便携工具至任务目录。使用 Gyan FFmpeg 9.0.2，不安装、不修改系统 PATH、不提升管理员权限；zip URL/SHA256/工具路径见 `asset_size_report.json`。
可复现处理器为 `scripts/prepare_idle_portraits.py`；`--static-from-first-frame` 可在没有 static_master 时直接生成匹配 fallback。
`docs/t15/sources.example.json` 为模板；机器本地真实路径映射 `sources.local.json` 保留但通过 .gitignore 排除。

## PlayerPanel / GeneralDetail / 静态页面

PlayerPanel 只替换 portrait content layer，frame、HP、identity、名字、势力、状态、技能、当前回合、合法/选中 glow、响应 UI、重连与响应式布局保留。
合法目标状态点击头像按钮会直接选目标；其他状态仍打开详情。video、static 和 loading/fallback 容器均 pointer-events none。
GeneralDetail 使用同一组件与 registry 当前角色视频，失败回到同造型静态。
十将选将、选将详情/缩略图、图鉴大网格、general list、大量小头像仍静态；真实十将选将测试确认没有 video 元素。
object-fit cover 和 objectPosition metadata 共用尺寸；九名都使用 `center top`，没有逐角色 scattered CSS 或缩小人物的特例。
已检查两组覆盖九名角色的牌桌截图、神吕布详情和静态回退；动态/静态尺寸一致，frame、HP、identity、skill 正常，视频不越框、不盖按钮。

## quality / motion / preload / lifecycle / fallback

- High、Medium 使用浏览器原生 autoplay muted loop playsInline；preload=metadata。
- Low 和系统 prefers-reduced-motion 不挂载 video，释放播放器/解码负担；实时偏好切换已测试。
- registry import 仅元数据，未构造播放器；首次真正进入 viewport 且 document visible 才加载对应视频。
- 离开 viewport / document.hidden pause；回到 viewport / visible 只恢复符合条件的视频。
- 卸载时清理 IntersectionObserver、visibility/preference listener 和播放 effect；play promise rejection catch，卸载后不更新状态。
- 无 video、404/load/decode/error、play() throw/reject、Low、reduced-motion 使用静态；playing 前 video 透明，静态一直在底层。
- 没有 React 每帧工作、setInterval loop、timeupdate loop、currentTime seek、Canvas 视频解码或绘制。

production/development sync 只允许 `idle_portraits.json` 明确注册的 cleaned runtime MP4，拒绝 missing/越界路径；未注册 MP4/MOV/WebM、source_art 不进入 public/dist。

## 性能与生产体积

| 指标 | 实测 |
|---|---:|
| T14.2 dist 原基线 | 11,868,359 bytes |
| 视频接入前代码 checkpoint dist | 11,870,771 bytes |
| 九个视频接入后 dist | 65,073,876 bytes |
| 与原基线总增量 | 53,205,517 bytes |
| 视频本身增量 | 53,270,072 bytes |
| production 首屏视频请求 | **0** |
| 单神吕布新增视频下载 body | 7,771,456 bytes |
| 张角/吕布/关羽/周瑜/赵云五人在场视频 body | 31,912,821 bytes |
| 五视频首次物理头像点击→selected class | 4.20 ms |

首屏网络检查在真正 production preview 中执行；runtime 只有当前牌桌/详情所需角色按需下载。上述下载量是本地浏览器冷缓存实测，HTTP transferSize 额外包含约300 bytes/响应的计账开销，见 `final-browser-metrics.json`。

**性能不能给完整 PASS：** 单视频页面约 60.05 fps；五视频含 active beam 页面调度约 31.26 fps，静态基线约 59.78 fps，p95 frame=33.40ms。每个视频仍接近24 fps，12秒采样仅少量掉帧，long tasks=0。
没有视频导致 React 高频 rerender，首次目标点击延迟正常；但五视频页面合成调度较静态下降，因此不能宣称满足“5视频无明显掉帧”。
已复核 Chromium headless-shell 和安装的 Edge（包括有窗口模式），现象一致。540×960 高质量 Web runtime 与局部合成隔离试验未改善调度，因此全部撤回，正式保留原画质 stream copy。
试验报告 `runtime-540-trial-metrics.json`、`runtime-720-original-metrics.json` 仅作为性能限制的证据，试验视频仅在本任务 workspace，未进入 production。

## 验证与实际边界

- Vitest **59 passed / 11 files**：DynamicPortrait、multiple panels、第一次目标点击、实时 reduced-motion、Low、404/decode/play拒绝、visibility/viewport、unmount、详情；现有 T14.2 交互与 T11 VFX 单元测试一起通过。
- pytest **5 passed**：源母带不能进入 public/dist、runtime whitelist、missing/path traversal、九个正式资源的完整性、音轨/codec与静态像素匹配。
- 独立临时仓库执行处理器 `--static-from-first-frame` 与码流 SHA256 验证 PASS；源文件未变，临时fixture已清理。
- TypeScript `tsc -b` PASS；Vite production build PASS。使用项目现有 `.venv`；未安装系统依赖。
- Chromium 最终真实素材/原机制/多人选将牌桌详情测试：**10 passed，1 skipped**（原生窗口可见性环境限制）。
- T11 Canvas presentation/performance 回归单独 PASS；measurements 存在 `t11_performance_regression.json`，旧 T11 tracked report 保持基线。
- 另在安装的 Edge 中运行了真实视频性能及首次目标点击场景。native loop 已跨越10秒边界；静态回退无 bounds 变化、无 UI collapse、无未处理 play rejection。
- 未改 Python shared registry/schema、engine、multiplayer 或 Decision ACK；未重复 full 747 Python。

**原生桌面隐藏验收未通过：** 这个自动化桌面中，实际切换标签页/最小化窗口后 document.hidden 仍为 false；关闭测试焦点模拟和后台节流参数后仍如此。
所以没有伪造 native-visibility PASS：document.hidden 的暂停/恢复逻辑通过 Vitest 和真实浏览器受控 visibilitychange 测试，actual background tab 测试保留为 opt-in `T15_NATIVE_WINDOW=1`，仍需在能提供原生可见性变化的桌面验收。
`playwright.edge.config.ts` 可复用已安装 Edge，完全不修改系统设置。

## 修改文件与 Git

接续 checkpoint 的修改包括：九个 `assets/generals/qun/<id>.png/.webp`，九个 `assets/portraits/idle/<id>.mp4`，`assets/idle_portraits.json`，`scripts/prepare_idle_portraits.py`，`tests/test_t15_idle_pipeline.py`，`web/e2e/fixtures/t15.html`，`web/e2e/t15-final-idle.spec.ts`，`web/e2e/t15-background-tab.spec.ts`，`web/playwright.edge.config.ts`，`.gitignore` 和 `docs/t15` 报告/截图。
原统一组件、PlayerPanel/GeneralDetail 接入与质量机制在上一代码 checkpoint，未引入第二套视频系统。
只 stage 精确本任务文件；不提交源母带、便携工具、外部 workspace 临时脚本、dist、机器本地配置或原 T11 未跟踪目录。
最终 tracked worktree 清洁，剩余六个既有 T11 未跟踪源目录。未部署 Cloudflare、未 force push、未 reset --hard、未改系统。

## 完成标准状态

| 标准 | 当前状态 |
|---|---|
| 9/9 DYNAMIC PORTRAITS | PASS — 正式 cleaned runtime 全注册 |
| PLAYER PANEL / GENERAL DETAIL / STATIC FALLBACK | PASS |
| HIGH / MEDIUM / LOW / REDUCED MOTION | PASS |
| VISIBILITY PAUSE | 逻辑/受控浏览器 PASS；真实原生桌面隐藏 PENDING |
| VIEWPORT PAUSE | PASS |
| FIRST TARGET CLICK | PASS |
| COMBAT VFX COMPATIBILITY | PASS — 独立 Canvas，无规则/演出实现改动 |
| NO MASS VIDEO PRELOAD | PASS — production 首页0视频请求 |
| PRODUCTION ASSET SIZE | PASS — 仅53.27MB cleaned视频，无母带；总dist65.07MB |
| SELECTION PAGE STATIC | PASS |
| T14.2 INTERACTION REGRESSION | PASS — 现有Web交互回归与首次物理点击 |
| 5视频页面性能无明显下降 | **未通过完整验收 — 页面调度约30fps vs静态60fps** |

阶段整体不能标记全项 PASS；尚存在上述两个验收问题。正式九名角色素材接入已完成，保持本地 checkpoint 等待后续性能/原生桌面验收及人工公网发布。

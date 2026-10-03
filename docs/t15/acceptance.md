# T15 Dynamic Idle Portrait Integration — 代码 checkpoint，素材接入未完成

日期：2026-10-04（Asia/Shanghai）。**正式动态素材 0/9；不得标记 9/9 PASS。**

基线 HEAD：`b763284f16905821ee3e501f172b075e6c869d6a`；前一功能 checkpoint：`fbf53aaac52c9f8e1dfa9f8c57a66bf2af412937`。
分支：`t13-complete-roster-multiplayer`；worktree：`C:/Sanguosha`。最终 checkpoint hash 见本次交付消息与 git log。

## 架构与实现

原 PlayerPanel 和游戏内 GeneralDetail 都使用静态 img；`web/src/assets.ts` 按 catalog portrait / kingdom 解析路径，production 转成 WebP。
Qt ResourceManager 读取 `assets/manifest.json` 处理静态 QPixmap，与浏览器视频无关，未修改。
T11 的 `GodPortrait` 是神吕布分区 SVG/PNG 原型，保留用于原有预览/演出；它没有可复用的原生视频播放器。
本次补充唯一的原生 idle 视频组件 `web/src/components/DynamicPortrait.tsx`，正式人物素材层使用它，T11 Combat Canvas、GodCinematic 与事件协议均未改。

`web/src/idlePortraits.ts` 读取 `assets/idle_portraits.json`；import 只读取路径元数据，不创建播放器、不预加载。
正式 manifest 当前为空，防止对缺失的资源进行虚假注册。9 名角色 ID 从 `src/sanguosha/content/characters/myth.py` 确认；张角沿用现有 ID。

## 角色资源清单

| 角色 | 稳定 registry ID | 当前 static PNG | 预定 cleaned runtime 路径 |
|---|---|---|---|
| 神吕布 | `forest_god_lvbu` | `assets/generals/qun/forest_god_lvbu.png` | `assets/portraits/idle/forest_god_lvbu.mp4`（未生成） |
| 神赵云 | `mountain_god_zhaoyun` | `assets/generals/qun/mountain_god_zhaoyun.png` | `assets/portraits/idle/mountain_god_zhaoyun.mp4`（未生成） |
| 神周瑜 | `fire_god_zhouyu` | `assets/generals/qun/fire_god_zhouyu.png` | `assets/portraits/idle/fire_god_zhouyu.mp4`（未生成） |
| 神诸葛亮 | `fire_god_zhugeliang` | `assets/generals/qun/fire_god_zhugeliang.png` | `assets/portraits/idle/fire_god_zhugeliang.mp4`（未生成） |
| 神曹操 | `forest_god_caocao` | `assets/generals/qun/forest_god_caocao.png` | `assets/portraits/idle/forest_god_caocao.mp4`（未生成） |
| 神司马懿 | `mountain_god_simayi` | `assets/generals/qun/mountain_god_simayi.png` | `assets/portraits/idle/mountain_god_simayi.mp4`（未生成） |
| 神关羽 | `wind_god_guanyu` | `assets/generals/qun/wind_god_guanyu.png` | `assets/portraits/idle/wind_god_guanyu.mp4`（未生成） |
| 神吕蒙 | `wind_god_lvmeng` | `assets/generals/qun/wind_god_lvmeng.png` | `assets/portraits/idle/wind_god_lvmeng.mp4`（未生成） |
| 张角 | `wind_zhang_jiao` | `assets/generals/qun/wind_zhang_jiao.png` | `assets/portraits/idle/wind_zhang_jiao.mp4`（未生成） |

production static 使用上述 `.png` 对应 `.webp`。所有静态资源保持现状；新版 Master 未提供可定位路径，尚未更新。
每名角色的 codec / pixel format / resolution / fps / duration / size / audio stream / faststart 均为 **N/A（最终母带与 runtime 缺失）**。
神吕布、张角新版动态与 static 的造型匹配、人物比例及裁切 **未验收**，不能用 T11 旧候选素材代替最终母带。

## 行为与生命周期

- PlayerPanel 与游戏内 GeneralDetail 使用统一组件；已有 frame、HP、身份、技能、状态和 VFX layer 保留。
- 合法 target 模式点击头像按钮直接选目标，非目标模式仍打开详情；真实组件的第一次头像点击立即 selected 已测试。
- High / Medium 可播放；Low 不渲染 video，释放解码器；系统 reduced-motion 实时变化时切换静态。
- viewport 首次可见且 document visible 才挂载 video。离开 viewport / hidden pause，恢复仅播放仍符合条件的视频。
- `autoplay muted loop playsInline preload="metadata"`；使用浏览器 native loop，没有 seek、timeupdate loop、setInterval 或 React 每帧更新。
- 静态图始终在底层，视频 playing 前透明；404/decode/load/play 拒绝回到静态，拒绝已 catch，卸载后的 promise 不更新状态。
- observer、visibility / preference listeners 和播放 effect 在卸载时清理。静态/动态 object-fit cover 共用尺寸与 objectPosition metadata。
- video、static 和容器 pointer-events none，头像按钮继续承担交互；combat Canvas 独立。
- 十将选择、选将详情/缩略图、武将列表/图鉴继续静态，不引入视频。

## 素材处理与生产保护

`scripts/prepare_idle_portraits.py` 接收明确 ID→源文件 JSON；未知 ID / 缺失源 / 源与 runtime 同路径会拒绝。
优先 H.264 yuv420p stream copy，`-map 0:v:0 -c:v copy -an -movflags +faststart`；不兼容时 H.264 yuv420p CRF18 转码，不改变播放速度或裁剪时间。
生成后验证 codec、音轨确实不存在、moov 在 mdat 之前、时长接近源文件和源 SHA256 保持不变；仅注册已生成文件，输出逐视频 probe 报告。
提供明确 static_master 时更新正式 PNG 与 WebP；绝不修改源 Master。工具不会安装系统软件、改变系统设置或部署。
`scripts/sync_web_assets.py` 对开发和生产都仅复制 manifest 内 runtime MP4；未注册 MP4/MOV/WebM 与 source_art 被排除。缺失/越界的注册路径直接阻止构建。

## 验证与证据

- Vitest：**59 passed，11 files**。包含 18 项 DynamicPortrait 测试与五动态 PlayerPanel 首次头像选目标回归；现有 Decision/交互与 T11 VFX 单元测试一起通过。
- TypeScript：`npx tsc -b` PASS。
- Vite production build：PASS（使用项目现有 `.venv` Python；系统 Python 缺少 Pillow）。
- pytest：`tests/test_t15_idle_pipeline.py` **4 passed**。验证源母带泄漏保护、runtime 白名单、missing registration、路径越界。
- 不修改 shared Python registry / resource schema / engine / multiplayer，不重复 full 747 Python。
- Chromium：T15 4 项机制测试、portrait-v3 真实多人选将/牌桌/详情测试通过；T11 Canvas performance 测试单独通过。
- Chromium production preview：首屏 **0 个动态视频网络请求**，PASS。
- 浏览器覆盖 High/Medium/Low、实时 reduced-motion、resize、viewport 暂停/恢复、缺失视频、play 拒绝、游戏内详情、首次目标点击、legal/selected glow、beam 与原有 Slash/Dodge 事件路径。
- 原生循环跨越循环边界时 portrait bounds 不变；五人 frame / HP / identity / skill 未被视频遮挡。机制截图：`browser-five-native.png`。
- 背景生命周期包括 Chromium freeze/resume，以及真实浏览器内 hidden/visible listener 的受控事件验证；没有以实际 Windows 前后台切换完成最终母带验收。

动态测试使用浏览器内存录制的 **160×240 WebM 色块夹具**，不是任何武将素材，永不进入 dist。
`browser-mechanism-metrics.json` 记录 native loop 与五视频 total/dropped frames；该小夹具结果不能推断九个真实 MP4 的性能，不能据此宣称“5 个最终视频无掉帧”。
`t11_performance_regression.json` 保存新 T11 measurements；原 `docs/t11/performance_final.json` 恢复基线，避免改写旧阶段报告。

## 生产体积与网络

| 指标 | 实测 / 状态 |
|---|---|
| dist 修改前 | 11,868,359 bytes |
| dist 代码接入后 | 11,870,771 bytes |
| 总增量 | 2,412 bytes |
| 本次正式视频增量 | 0 bytes（尚未生成） |
| 9 个 runtime 总大小 / 最大单视频 | N/A |
| production 首屏动态视频请求 | 0 |
| 1 个真实动态角色新增下载 | N/A，待最终 MP4 |
| 5 个真实动态角色新增下载 / 性能 | N/A，待最终 MP4 |

## 文件范围与 Git 保护

代码/资源：`assets/idle_portraits.json`、`web/src/idlePortraits.ts`、`web/src/components/DynamicPortrait.tsx`、`web/src/components/GamePage.tsx`、`web/src/styles.css`、`scripts/prepare_idle_portraits.py`、`scripts/sync_web_assets.py`。
测试：`web/src/components/DynamicPortrait.test.tsx`、`web/src/components/GamePage.test.tsx`、`web/e2e/t15-native-idle.spec.ts`、`web/e2e/fixtures/t15.html`、`web/e2e/portrait-v3.spec.ts`、`tests/test_t15_idle_pipeline.py`。
报告/证据仅在 `docs/t15/`。只 stage 上述指定任务文件，不使用 git add 全仓库。
开始前存在的六个未跟踪 T11 素材目录全部保留、不覆盖、不删除、不提交。
未修改 T14.2 Decision、游戏规则、技能、多人协议或 Canvas VFX 实现；没有公网部署，没有 force push。

## 未完成与所需输入

整个 `C:/Sanguosha` 文件清单（包含 ignored/hidden、排除 .git/.venv/node_modules）中没有 MP4。
ffmpeg/ffprobe 在 PATH 与已检查的常见工具目录中没有找到，未安装任何软件。
已通过异步问题请求最终母带与静态 Master 的本地目录，尚未收到路径。

继续完成需要：**九个最终 MP4 和新版 static Master 的明确本地目录；如果 ffmpeg/ffprobe 已在其他目录，提供它们的路径。**
神吕布最终素材 vertical slice、剩余八名角色接入、去音轨 probe、Master 匹配、逐角色裁切、最终 1/5 视频下载量与最终素材视觉/性能验收都在此输入之后执行。

## 验收状态

| 要求 | 当前状态 |
|---|---|
| 9/9 DYNAMIC PORTRAITS | BLOCKED — 0/9 最终视频 |
| PLAYER PANEL / GENERAL DETAIL | PASS — 统一代码机制；最终素材视觉待验 |
| STATIC FALLBACK / HIGH / MEDIUM / LOW / REDUCED MOTION | PASS — 机制测试 |
| VISIBILITY PAUSE / VIEWPORT PAUSE | PASS — 生命周期测试；实际前后台最终素材待验 |
| FIRST TARGET CLICK | PASS — 真实组件首次头像点击 |
| COMBAT VFX COMPATIBILITY | PASS — 未改 VFX，回归通过；最终视频 stacking 待验 |
| NO MASS VIDEO PRELOAD | PASS — lazy lifecycle / production 首页 0 请求 |
| PRODUCTION ASSET SIZE | 当前代码 PASS；9 个最终视频体积待验 |
| SELECTION PAGE STATIC | PASS — 真实十将选将零视频断言 |
| T14.2 INTERACTION REGRESSION | PASS — 现有 Web 单元测试与本地多人回归 |
| 新版 static Master 匹配 / 最终武将视觉 | BLOCKED — 素材路径缺失 |

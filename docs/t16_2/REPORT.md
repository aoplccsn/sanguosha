# T16.2 — Portrait Fusion Prototype

日期：2026-10-04（Asia/Shanghai）。基线 `7970b82`。只处理神吕布、神关羽、张角三个技术样板；保留 T16.1 portrait-first 布局，不推广 65 将，不部署。

## 方案与作用范围

采用 CSS `mask-image`，每个样板引用一张手工绘制的固定 SVG alpha 蒙版。SVG 以现有素材的 506×900 构图为坐标，包含脸/身体与武器的保留轮廓、外围径向背景渐隐、底部渐隐。轮廓内 alpha 核心保持不透明，人物外的场景背景退入牌桌。SVG 的静态 `feGaussianBlur` 只羽化蒙版边缘（身体 9 源图 px、细武器 3 px），并不作用于视频纹理；没有 CSS filter 加到视频，没有帧间蒙版动画。

蒙版之外叠加非常窄的左右（2%）及顶部（1%）CSS 边缘渐隐，防止素材碰到原图边缘的位置仍露出切线。样板的原矩形 caption 背景改为局部椭圆渐变，文字层、身份、HP、装备、技能、目标状态边缘和点击按钮保持独立。

SVG `preserveAspectRatio="xMidYMin slice"` 与当前 img/video 的 `object-fit:cover`、`center top` 对齐。img 与 video 使用共同的 `.dynamic-portrait` 父容器蒙版，解码失败、Low 画质或 reduced motion 回退不改变蒙版、viewport、crop 或 object-position。翻面把共有容器及蒙版一同镜像，内部媒体取消重复镜像，UI 文字保持正常方向。

实现没有修改 `DynamicPortrait.tsx`、`idlePortraits.ts`、MP4/静态素材、H.264 pipeline、媒体生命周期、AI pacing 或游戏规则。只给 PlayerPanel 添加 `data-character-id`，样式仅匹配这三个 ID 的牌桌席位。详情弹窗未做融合改版。

## 三个样板

| 样板 | 本轮重点与结果 |
| --- | --- |
| 神吕布 | 红月与暗场景的矩形顶边退去；脸、盔甲、左戟的主体仍清晰。原生 MP4 loop、故障静态回退正常。 |
| 神关羽 | 青绿色背景从明显照片变为沿人物与长刀的轮廓渐隐；脸、肩甲、手与刀刃保留，没有缩放或加重 crop。 |
| 张角 | 保留普通将样板；金色/水墨背景的顶边与大块外围退去，脸、身体、符纸与右侧杖保持存在感。 |

对照：`comparison-three.png` 四列依次为 T16.1 动态、T16.2 动态、T16.1 静态、T16.2 静态。三行依次神吕布、神关羽、张角。`comparison-five.png` 为整桌 before/after。

独立截图：`before-five.png` / `after-five.png`；三个 `before-{lvbu,guanyu,zhangjiao}-{dynamic,static}.png` / `after-...png`；故障回退 `error-*-static.png`。动态对比固定在 native video 的 0.5 秒，仅测试夹具暂停/seek，没有加入产品代码。

## 一致性、点击与回归

- 三个样板 before/after 的 img/video bounding rect、object-position、object-fit、transform、pointer-events 完全相同（`before-geometry.json`、`after-geometry.json`）。人物显示面积未缩小；外围背景透明不等于主体缩小。
- 样板脸与武器测试点的 alpha 均 1，外角/顶部背景 alpha 为 0（`mask-alpha.json`）。这是若干核心点验证，并非逐像素精确分割。
- 三个真实 MP4 都验证从 loop 末尾回到开头；分别触发 video error 后，蒙版与容器几何完全不变，video 移除，static 保留（`fallback-loop.json`）。
- Low/high、reduced-motion、离开视口、隐藏/恢复文档生命周期通过；隐藏文档使用受控 visibility 事件测试，不声称实际后台窗口检测。
- legal target glow / selected glow / 回合提示 / pointer-events:none、杀/闪实际 Canvas 绘制、beam、左慈 hover/focus/info/首选项点击、三档 pacing 和真人立即绕过队列均通过。
- 0/1/3/5 动态视频下，首次目标 selected class 更新耗时分别 3.6, 3.3, 2.9, 3.1 ms；选牌→选目标→最后确认与闪响应确认均 PASS。测量为 DOM 更新时间，不是网络响应时间。
- 五人/八人在 1440×1000、1366×768、1024×768 的席位无重叠/无越界。390×844 手机布局回归通过。密集装备、判定、技能与标记仍可读，装备预览保持 hover/focus。
- AI 节奏实测 slow 1456.2 / normal 1025.8 / fast 483.4 ms；生产 pacing 文件未修改。

## 性能

沿用 T15.1 的 CDP tracing + 6 秒原生 video/rAF 采样方法。先在真实 `7970b82` 保存同机 before，再测本轮 after；均显示大立绘并选目标保留 beam。性能统计的 rAF/Canvas 只在测试代码中，生产代码没有逐帧 JS、React、Canvas 或图像分割。

| 动态数量 | T15.1 历史 FPS | 本轮 before FPS | 本轮 after FPS | after p95 | 长任务 | video 丢帧/总帧 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 60.06 | 60.16 | 60.17 | 16.7 ms | 0 | 0/0 |
| 1 | 60.15 | 60.04 | 60.19 | 16.7 ms | 0 | 0/147 |
| 3 | 31.83 | 31.79 | 31.92 | 33.4 ms | 0 | 1/442 |
| 5 | 31.75 | 31.92 | 31.92 | 33.4 ms | 0 | 1/739 |

3/5 路相对 before 和 T15.1 未测得明显退化；该测试环境的基线就是约 32 FPS，不能将结果宣称为 60 FPS。3/5 路 CDP TaskDuration 为 641.9→631.4 ms、686.3→669.3 ms（6 秒窗口）。所有场景无媒体 src/poster/childList 变更，视频节点稳定，普通 projection 更新不新增 play/pause/observer。5 路合计丢 1/739 帧，与 T15.1 少量丢帧量级相同。

0/1 路 task/script 指标存在小幅波动，单路 TaskDuration 为 1139.7→1302.1 ms，FPS/p95 和长任务无退化；没有将一次采样的 CPU 时间当作跨设备保证。完整 tracing 指标在 before/after-performance.json；摘要见 performance-summary.json。

全部现有 idle MP4 的哈希前后完全相同（mp4-before-hashes.json / mp4-after-hashes.json），未重编码、替换或批处理视频。

## 测试

- Vitest：14 文件 / 67 测试 PASS，包括 18 个 DynamicPortrait 既有单测。
- TypeScript：`tsc -b` PASS。
- Vite：55 modules build PASS，蒙版作为 Vite CSS URL 资产打包。
- Playwright：最终主套件 11/11 PASS；之后补充翻面专用回归 1/1 PASS。证据 playwright.txt / face-down-test.txt。
- diff whitespace check PASS（交付日志尾部空白规范化）。

构建使用已有 `.venv` Python/Pillow，不安装新依赖。Vitest 保留 jsdom Canvas 未实现的既有提示；真实 VFX 由 Chromium 检查。浏览器使用真实 GamePage/样式/原始 MP4，但状态为确定性夹具，不能等同完整多人实战验证。

## 修改文件

- `web/src/components/GamePage.tsx`（只有角色 ID 样式定位属性）
- `web/src/styles.css`（三个样板蒙版/局部底衬/翻面规则）
- `web/src/portraits/fusion/lvbu.svg`、`guanyu.svg`、`zhangjiao.svg`
- `web/e2e/t162-fusion.spec.ts`、`t162-performance.spec.ts`、`t162-interactions.spec.ts`、`t162-table-regression.spec.ts`
- `docs/t16_2/`：before/after/性能/回归/本报告

## 限制

这是为现有构图手工调节的固定 presentation 蒙版，不是视频真透明或精准人物分割。神关羽头顶与长刀周围保留了少量亮背景，避免削掉帽饰、刀刃和运动余量；人物动态轮廓仍会有轻微背景晕圈。武器在源图边缘的部分仍受原 viewport 裁切，未扩大/重新制作素材。固定蒙版对更大幅度位移或未来不同构图视频需重新校对。未推广其他 62 将，未改详情弹窗；后续推广应以用户认可这三组对照为依据。

PORTRAIT RECTANGLE REDUCED: PASS
PORTRAIT-FIRST PRESERVED: PASS
DYNAMIC PORTRAIT FUSION: PASS（固定蒙版样板）
CLICK RELIABILITY: PASS
PERFORMANCE REGRESSION: NONE（本轮本机 3/5 路采样未测得明显退化）

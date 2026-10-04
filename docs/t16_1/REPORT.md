# T16.1 — Portrait-first Official-style UI Correction

日期：2026-10-04（Asia/Shanghai）。基线：`415d9e1`。本轮只修正 UI 结构与呈现，不改规则、网络决策、AI 队列或动态媒体生命周期，不部署公网。

## 修改文件

- `web/src/components/GamePage.tsx`：信息聚合到席位底部 caption；势力/距离/范围收为一行；标记随信息流排列；目标按钮使用明确的目标选择无障碍名称；中央牌堆/弃牌位置。
- `web/src/styles.css`：替换 T16 的厚框/双栏/大型底板布局；完整席位立绘；两侧姓名/体力；轻量底衬；本地人物与手牌统一；操作条随本地立绘宽度避让；HUD/tooltip 轻量化；五人/八人/窄屏布局。
- `web/e2e/t161-portrait-first.spec.ts`：视觉、空间占比、席位不重叠、装备预览、左慈、AI 节奏、HUD、目标光效、杀/闪 Canvas 绘制以及本地网络检查。
- `web/e2e/t161-interactions.spec.ts`：保留 T15.1 交互场景，在本轮独立记录 0/1/3/5 个真实动态立绘的首次点击、最终确认和响应确认。
- `docs/t16_1/`：本报告、截图、指标与测试日志。T16 原有证据未覆盖。

## 为什么比 T16 更接近描述的官方结构

T16 将人物放在左侧 104×176（八人 90×151）的窗口，右侧名字和信息以及下方技能占据独立实色空间，外面再包厚双框。本轮让人物铺满席位，名字/体力贴边，装备与状态依附在底部渐变；默认外框是 0px，仅在回合、合法目标、选择和响应时显示局部状态边缘。

在 1440×1000，其他席位立绘容器约 187×290，五人局显示容器面积约为 T16 的 3 倍，八人局约 4 倍。本地立绘约 216×300，周围不再有嵌套面板。100% 是容器占席位面积的测量值，并不意味着素材中的人物像素占比 100%。底部信息区在六组桌面尺寸/人数场景中约占高度 15%–44%，含装备、判定、两技能与怒标记的密集场景。

桌面牌桌不再强制 1000px 高；1366×768 的八个席位均在视口内。中央提示、淡桌面轮廓和牌堆/弃牌位置连接席位与牌桌，公共选牌池出现时隐藏中央牌堆，避免信息争夺。手牌仍是完整固定按钮，悬停/选中仅移动图片。

人物因此成为首要的面积与细节来源；边框、按钮、说明和状态的对比度及面积退居辅助。这里的“官方方向 PASS”依据本次任务列出的 A–F 结构特征，不声称逐像素匹配。本轮附件仅含文字，没有可直接打开的目标参考图。

## 验收

| 项目 | 结果与证据 |
| --- | --- |
| 五人/八人 | PASS；1440×1000、1366×768、1024×768 各两组，无席位重叠，均不越出视口 |
| 手机八人 | PASS；390×844 两列滚动布局，完整页面截图 `eight-mobile.png`；手机操作条固定在视口底部 |
| 立绘容器/轻框 | PASS；`layout-metrics.json`：容器面积比例 1，默认边框 0px |
| 动态立绘 | PASS；真实注册的 MP4 正常解码/播放；静态回退及低画质生命周期由既有单测覆盖 |
| 点击/确认 | PASS；选牌→首次选目标→最后确认；第一次取消清目标，再取消清选牌；无目标时确认禁用；闪响应也最后确认 |
| 点击耗时 | 0/1/3/5 动态席位分别 3.8, 3, 3.1, 3 ms；这是 click 到 selected-target DOM 更新的本地测量，不是网络往返 |
| pointer events | PASS；每席位 dynamic-portrait、图片和 video 均 `none`；信息仅装备预览参与 hover/focus |
| 回合/目标/VFX | PASS；current turn、合法/已选光效；beam 保留；杀/闪事件实际 Canvas 非空绘制，无 pageerror |
| 左慈 | PASS；registry 描述复用，hover、focus、Escape、触屏 info、第一次选项点击均正常 |
| AI pacing | PASS；慢 1460.3 ms / 正常 1019.6 ms / 快 471.0 ms；真人请求立即绕过展示队列；生产 pacing 源码未改 |
| HUD/中央 | PASS；速度/画质可操作，中央事件中文提示正常；本地 HTTP/assets/WS/持续连接诊断通过 |
| Vitest | PASS；14 files / 67 tests，见 `vitest.txt` |
| TypeScript | PASS；`tsc -b` exit 0，见 `typescript.txt` |
| Vite build | PASS；55 modules，见 `build.txt` |
| Playwright | PASS；7 tests，见 `playwright.txt` |
| 补丁检查 | `git diff --check` PASS |

构建使用仓库已有 `.venv/Scripts` 的 Python（系统 Python 没有 Pillow）。未安装新依赖。Vitest 保留既有 jsdom Canvas 未实现提示，真实 Canvas 由 Chromium 验证。

## 图片

- `five.png`、`eight.png`：1440×1000，多张手牌、真实动态素材、目标选中与 beam。
- `5-seats-1366x768.png`、`8-seats-1366x768.png`：常见笔记本视口。
- `5-seats-1024x768.png`、`8-seats-1024x768.png`：平板/较窄桌面。
- `5-seats-1440x1000.png`、`8-seats-1440x1000.png`：含装备、判定、技能、标记的密集场景。
- `eight-mobile.png`：手机完整滚动页面。
- `basic.slash.png`、`basic.dodge.png`：事件提示与运行中 VFX。

## 仍存在的距离

现有静态与 MP4 素材自带矩形背景，通过边缘渐隐减轻切割感，仍不能达到透明人物越出画面、自然融入背景的官方美术效果。部分源图的人物在原素材中本来偏小，放大容器不会改变素材本身的构图。中央桌面目前仍偏克制；本轮没有重新制作完整场景美术。1024px 与手机场景以可用性为先，提示会换行；手机席位仍需要纵向滚动。

浏览器视觉/交互使用真实 GamePage、原样式和真实立绘资源，状态由确定性夹具提供；AI pacing 是事件序列回归，并非一整场真人/AI 对局验证。官方风格方向得到明显修正，最终审美认可由用户查看截图决定。

PORTRAIT-FIRST UI: PASS
OFFICIAL-STYLE DIRECTION CORRECTION: PASS（结构方向）
PLAYER PANEL FRAME WEIGHT REDUCED: PASS
LOCAL PLAYER AREA IMPROVED: PASS
CLICK RELIABILITY REGRESSION: PASS
DYNAMIC PORTRAIT PRESENTATION: PASS
AI PACING PRESERVED: PASS

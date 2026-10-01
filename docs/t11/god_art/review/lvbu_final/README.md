# T11.2 神吕布验收记录

状态：**PARTIAL**。真实牌局触发、视觉序列、跳过和低动态已验证；中画质全屏演出的帧率仍低于目标，受击、濒死、胜利目前只有动作预览截图，尚无对应真实牌局截图。不得据此宣布 `DYNAMIC PORTRAIT` 或 `GOD ATTACK FX` 为 PASS。

## 范围与触发

- 只处理神吕布。常规 57 武将池未加入神将；本地开发环境通过 `?t11_lvbu=1` 开启真实 Web 对局验收场景，生产环境忽略该参数。
- 验收场景给神吕布准备怒标与三种杀，仅用于稳定复现。出牌、无前、神愤仍走对局请求、规则引擎与公开事件。
- 普通杀、火杀、雷杀由真实 `CardUsedEvent` 触发短角色演出；无前先记录强化状态，**随后真正使用杀牌时**触发 Level 2。神愤由规则引擎发出的 `GodSkillEvent` 触发 Level 3。
- 神愤目标来自事件中的实际角色列表；每名目标按节奏显示命中反馈。体力与弃牌由引擎结算，演出不计算伤害。
- 神吕布头像的入场、攻击、受击、死亡和胜利模式接到公开事件；大图动作预览用于检查造型和切层边缘。

## 画面证据

总览：[god_lvbu_final_review.png](god_lvbu_final_review.png)。其中 `REAL MATCH` 来自真实 Web 对局；`ACTION PREVIEW` 为动作界面预览，不能替代实战事件验收。

| 状态 | 截图 | 证据性质 |
|---|---|---|
| 待机 | [idle_real.png](idle_real.png) | 真实牌局 |
| 普通杀 | [slash_real.png](slash_real.png) | 真实出牌 |
| 火杀 | [fire_real.png](fire_real.png) | 真实出牌 |
| 雷杀 | [thunder_real.png](thunder_real.png) | 真实出牌 |
| Level 2 | [level2_real.png](level2_real.png) | 无前后的真实杀牌 |
| 神愤 | [shenfen_real.png](shenfen_real.png) | 真实技能与四目标结算 |
| 入场 | [entry_preview.png](entry_preview.png) | 动作预览 |
| 受击 | [hit_preview.png](hit_preview.png) | 动作预览 |
| 濒死 | [dying_preview.png](dying_preview.png) | 动作预览 |
| 胜利 | [victory_preview.png](victory_preview.png) | 动作预览 |

真实对局截图使用开发环境 `t11_capture=1` 在事件出现后暂停 CSS 动画到指定时刻，以便截图；该开关不参与生产构建，不改变规则结果。正常演出时长为普通杀约 0.9 秒、Level 2 约 1.2 秒、神愤约 2.1 秒。

## 性能

测量方式：Playwright Chromium 中画质、真实 Web 对局内的 `requestAnimationFrame` 帧间隔。该值受测试机器与无头浏览器影响。原始数据见 [performance_medium.json](performance_medium.json)、[performance_god_idle.json](performance_god_idle.json)、[performance_baseline.json](performance_baseline.json) 和各分辨率的 `performance_cinematic_*.json`。

| 分辨率 | 普通牌局待机 | 神吕布待机（分层缩图后） | 独立普通杀 | 独立神愤 |
|---|---:|---:|---:|---:|
| 1366×768 | 61 FPS | 60 FPS | 48 FPS | 40 FPS |
| 1600×900 | 59 FPS | 58 FPS | 41 FPS | 34 FPS |
| 1920×1080 | 55 FPS | 57 FPS | 29 FPS | 23 FPS |

六种场景、三种分辨率的最终连续测量如下；该测量会累积浏览器上下文与软件渲染负载，因此与上面的独立测量分开列出。

| 分辨率 | 待机 | 普通杀 | 火杀 | 雷杀 | Level 2 | 神愤 |
|---|---:|---:|---:|---:|---:|---:|
| 1366×768 | 61 | 54 | 51 | 50 | 46 | 41 |
| 1600×900 | 60 | 43 | 42 | 42 | 35 | 32 |
| 1920×1080 | 61 | 29 | 31 | 30 | 25 | 23 |

固定内部演出分辨率试验在 1920×1080 的独立测量中得到普通杀 30 FPS、神愤 21 FPS，未改善，故恢复现有视觉实现。普通牌桌待机已接近基线；短全屏演出尚未达到中画质接近 60 FPS 的目标。

## 自动验收

- Python 全套：455 通过。
- Web 单元测试：22 通过。
- 真实 Web 对局：普通杀、火杀、雷杀、无前后强化杀、四目标神愤通过。
- Esc 跳过与系统低动态：通过；跳过不改变引擎已经决定的伤害与目标。
- 当前仍需处理：中画质 cinematic 性能；受击、濒死、胜利真实对局抓拍；动态切层在更多设备上的肉眼复核。

参考规则：[三国杀官方神吕布武将页](https://www.sanguosha.com/hero/206)。

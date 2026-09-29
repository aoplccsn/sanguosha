# T7 战斗表现验收图

使用 `PYTHONPATH=src python docs/capture_t7_vfx.py` 在 Qt 离屏环境生成。脚本给正式 `CardVfxLayer` 送入公开事件，定格对应动画帧；胜负两图来自 seed 3（胜）和 seed 1（负）的完整真实对局及其正式 `GameEndedEvent`。前六图是用于检查视觉设计的定格场景，不代表一局真实对局的连续截图。没有修改对局规则或使用官方素材。

| 场景 | 截图 |
| --- | --- |
| 预选目标连线 | [target_beam.png](t7_vfx_screenshots/target_beam.png) |
| 普通杀 | [slash_vfx.png](t7_vfx_screenshots/slash_vfx.png) |
| 火杀 | [fire_slash_vfx.png](t7_vfx_screenshots/fire_slash_vfx.png) |
| 雷杀 | [thunder_slash_vfx.png](t7_vfx_screenshots/thunder_slash_vfx.png) |
| 闪避 | [dodge_vfx.png](t7_vfx_screenshots/dodge_vfx.png) |
| 一破播报 | [kill_announcement.png](t7_vfx_screenshots/kill_announcement.png) |
| 真人胜利 | [victory_overlay.png](t7_vfx_screenshots/victory_overlay.png) |
| 真人失败 | [defeat_overlay.png](t7_vfx_screenshots/defeat_overlay.png) |

专项测试见 `tests/test_t7b_vfx.py`；正式结果由 `GameEndedEvent` 决定，击杀归属由 `PlayerDiedEvent.killer_id` 决定。时长集中在 `src/sanguosha/ui/timing.py`；测试模式可将播放时间缩到 1 毫秒。

# T15 最终源视频审计

2026-10-04（Asia/Shanghai）。用户提供的源目录：`C:/Users/aopl/Documents/ChatGPT/small game 1/dynamic_portrait_sources`。

**母带 9/9 已定位，全部能在 Chromium 解码。正式无音轨 faststart runtime 现已全部生成并注册。**

用户明确授权后，使用任务目录中的便携 FFmpeg 9.0.2 完成处理；不安装、不改系统 PATH、不提升管理员权限。

ISO-BMFF atom 检查得到九个视频均为 AVC/H.264 High profile、level 3.1、720×1280、240 frames / 24 fps、视频轨 10.000 秒；均带 AAC (`mp4a`) 音轨。
Chromium metadata 时长约 10.005 秒。后续 ffprobe 已确认全部源为 yuv420p；正式runtime完整 probe 见 media_report.json。
源文件合计 **54,774,173 bytes**，最大为神吕布 **7,942,202 bytes**。源视频不得原样复制进 runtime/dist。

| registry ID | source filename | bytes | source faststart |
|---|---|---:|---|
| `forest_god_lvbu` | `god_lubu_idle.mp4` | 7,942,202 | yes |
| `mountain_god_zhaoyun` | `god_zhaoyun_idle.mp4` | 5,117,400 | yes |
| `fire_god_zhouyu` | `god_zhouyu_idle.mp4` | 5,475,145 | no |
| `fire_god_zhugeliang` | `god_zhugeliang_idle.mp4` | 5,707,070 | no |
| `forest_god_caocao` | `god_caocao_idle.mp4` | 5,610,595 | no |
| `mountain_god_simayi` | `god_simayi_idle.mp4` | 4,989,017 | no |
| `wind_god_guanyu` | `god_guanyu_idle.mp4` | 6,795,933 | no |
| `wind_god_lvmeng` | `god_lvmeng_idle.mp4` | 5,712,018 | no |
| `wind_zhang_jiao` | `zhangjiao_idle.mp4` | 7,424,793 | yes |

`source_audit.json` 包含每个源文件的 SHA256、浏览器解码元数据、视频/音频轨 atom 检查与 faststart 结果。
`source_static_comparison.jpg` 上排为最终视频首帧，下排为当前 static。视频是 9:16，现有静态多数为 2:3。
神吕布存在明显造型差异，需要从最终视频提取或使用匹配 Master 更新 fallback。其余角色主体整体一致，但构图/宽高比不同；正式接入时仍应逐一检查人物比例。

所有源文件只读，不覆盖、不修改、不删除。六个既有 T11 未跟踪素材目录保留。
此前 checkpoint `374f6074d67e719166ef9dce6a4e541110e34584` 的组件、生命周期、生产白名单和测试仍适用。
`assets/idle_portraits.json` 现已仅注册九个 cleaned runtime；未注册源母带。九个 fallback 已从最终视频首帧更新。

# Web 背景音乐

缺少用户提供的、有授权的 BGM；本补丁未下载或包含版权音乐。
请将中国风、沉稳、战斗桌氛围的授权音频放到 `assets/audio/bgm/main_bgm.mp3`，再运行 Web build。
现有 sync_web_assets.py 会复制音频到 public/assets，构建时自动检测文件并启用控制。
默认音量 0.2，首次用户交互后循环播放；开关及音量存储于 localStorage 的 sanguosha.bgm。
缺资源时控制禁用，不发起音频请求。PySide 本补丁未接入。

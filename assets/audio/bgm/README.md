# T21.4 双 BGM

- 大厅：**山河将起**（`lobby_bgm.wav`），64 秒、60 BPM。稀疏五声拨弦、箫笛式气声、轻弦乐底色与克制低鼓。
- 对局：**暗局·夜阵**（`main_bgm.mp3`），继续使用项目已有的原创战局音乐，120 秒、72 BPM。

两首均为项目原创程序合成，没有外部采样、人声或官方音频。
大厅曲沿用 `scripts/generate_bgm.py` 的合成原语，运行
`python scripts/generate_lobby_bgm.py` 可确定性重现；战局源文件仍由
`python scripts/generate_bgm.py` 生成。两者峰值均约 -9 dBFS。

大厅使用 22.05kHz 单声道 PCM WAV（约 2.69 MiB），无需新增编码依赖。
仅在交互后播放当前场景曲目；battle 在进入实际对局时才准备。
现有同步管线会发布大厅 WAV 和战局 MP3；战局的原始 `main_bgm.wav` 不发布。
资源失败时不抓取替代音乐；可在有权使用音频后替换资源并沿用双 BGM 系统。

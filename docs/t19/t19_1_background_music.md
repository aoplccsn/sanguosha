# T19.1 background music

基线：46e1711（最新 T19，原生动态立绘修复）。日期：2026-10-07。

Web 根入口挂载一个 BackgroundMusic；模块级单一 audio 跨页面、房间状态和 StrictMode 挂载复用。
首次 pointerdown/keydown 后播放，loop，默认音量 0.2；开关和音量保存到 sanguosha.bgm localStorage。
关闭暂停，重新开启续播，不重置 currentTime；不改游戏规则或已有音效。未重构 PySide。

音频资源缺失：仓库 assets 下未找到 mp3/ogg/wav/m4a 用户 BGM。未下载或使用官方三国杀/其它版权音乐。
预留 assets/audio/bgm/main_bgm.mp3；既有资源同步脚本自动复制，Vite 构建自动判断可用性。
缺文件时按钮显示“背景音乐 缺少音频”并禁用，不创建 audio 或请求不存在的资源。
资源到位后需重新构建，以启用 BGM。

验证：相关 Vitest 1 PASS（持久化、StrictMode、重复交互及 remount 单实例），资源存在测试 1 SKIP，原因明确为缺文件。
项目既有 .venv Python 执行资产同步后 fresh tsc + Vite production build PASS。

发布：T19 尚未部署。补丁直接提交到既有 t19-overpowered-generals 发布分支，push 后构建该补丁最终 HEAD SHA 的 GHCR 镜像。
Sealos 当前浏览器重查仍为 https://bja.sealos.run/signin，且本机无 kubeconfig；部署受登录阻塞。
未先部署旧 T19 镜像。获得现有北京 Sealos 登录会话后，只更新 sanguosha-cn 到本补丁最终 SHA，保持现有配置。

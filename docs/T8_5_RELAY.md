# T8.5 公网 Relay

唯一 GameState、规则引擎、随机数和决策校验仍位于房主电脑上的 GameServer。HostRelayTransport 通过出站 WebSocket 连接 Relay，并把每个来宾的逻辑通道反向代理到本机游戏服务器。Relay 只注册房间、分配安全房间码、隔离逻辑通道和转发现有 JSON 游戏协议。

在 Linux VPS 上运行 docker compose up -d。容器默认只绑定宿主机 127.0.0.1:8765，由 Caddy、nginx 或云服务反向代理终结 TLS，对外暴露 443 上的 wss://。普通玩家不得安装证书或关闭 TLS 验证。

支持 RELAY_HOST、RELAY_PORT、PUBLIC_BASE_URL、ROOM_TTL、HOST_RECONNECT_GRACE、MAX_ROOMS、MAX_CONNECTIONS_PER_IP、ROOM_CREATIONS_PER_MINUTE 和 LOG_LEVEL。

健康检查可以建立 WebSocket，发送合法版本的 PING 并等待 PONG。日志记录房间创建、玩家加入、断开、重连、关闭和协议错误。host token 仅记录 SHA-256 前缀；reconnect token、私有手牌和敏感 Decision payload 不写日志。

Relay 没有必须备份的业务状态。第一版不保证 Relay 进程重启后无缝继续。房主永久退出会结束对局，本阶段不提供 host migration。建议起步资源为 1 vCPU、512 MB 内存。

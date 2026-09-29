# T9.1 服务器资源

小规模试运行建议从 1 vCPU、1–2 GiB RAM、10 GiB 可用磁盘开始。实际容量取决于并发房间和浏览器连接数，部署后应观察容器内存、CPU、连接数和延迟，再调整 `MAX_ROOMS`、`MAX_CONNECTIONS`。需要稳定的公网 IPv4/IPv6、域名解析和开放的 80/443 TCP；443 UDP 可改善 HTTP/3，但不是必需。上行带宽建议至少 5 Mbps，并按实际玩家数量监测。

所有房间位于单个 Python 进程的内存中，生产命令固定为一个 worker。此版本不跨进程分片，也不持久化 GameState；容器或主机重启会结束现有对局。Caddy 证书和日志使用 Docker volume。游戏没有数据库，不需要数据库备份。

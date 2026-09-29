# T9.1 生产部署

状态：配置已面向生产设计。只有实际公网 HTTPS/WSS 和两浏览器验收通过，才能标记 `PUBLIC DEPLOYMENT PASS`。

## 首次部署（Ubuntu LTS）

1. 准备域名，把 A/AAAA 记录指向服务器公网地址。确认 80/tcp、443/tcp 可从公网访问；SSH 端口按现有运维设置保留。后端 8000 和 Vite 5173 不对公网开放。
2. 按 [Docker 官方 Ubuntu 安装文档](https://docs.docker.com/engine/install/ubuntu/) 安装 Docker Engine 和 Compose plugin。此项目无需数据库或 Node 运行服务。
3. 从代码托管地址克隆仓库，或上传完整项目目录到服务器；切换到 `t9.1-production-deploy`，确认 Git 工作区干净。当前本地仓库没有配置 remote，因此上传部署也是受支持的路径。安装 Python 3 与 `websockets` 包仅用于验收脚本；游戏运行在容器内。
4. `cp .env.production.example .env.production`，将 `DOMAIN` 改为真实域名，`PUBLIC_ORIGIN` 改为对应 `https://域名`，用 `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'` 生成独有 `SECRET_KEY`，并设置 `BUILD_COMMIT=$(git rev-parse HEAD)` 的实际值。把 `.env.production` 权限设为 `chmod 600`。执行 `ln -s .env.production .env`，使 Compose 的变量插值可以读取同一配置文件。不要提交这两个文件。
5. 运行 `docker compose -f docker-compose.production.yml up -d --build --wait`。以后已有镜像时，`docker compose -f docker-compose.production.yml up -d` 即可启动。
6. Caddy 自动申请及续期 TLS 证书；DNS 生效且 80/443 通畅时，浏览器访问 `https://$DOMAIN`。HTTP 会自动跳转 HTTPS，浏览器 WebSocket 使用 WSS。
7. 检查 `https://$DOMAIN/health` 返回 `status: ok`，`/api/version` 返回版本、实际构建 commit 与协议版本。运行 `python3 scripts/smoke_production.py "https://$DOMAIN"` 检查首页、健康、版本及两个 WSS 客户端创建/加入房间。然后运行 `cd web && BASE_URL=https://域名 npx playwright test e2e/production.spec.ts` 进行真实两浏览器流程。

## 运维

查看日志：`docker compose -f docker-compose.production.yml logs --tail=200 -f`。Caddy 访问日志保存在 `caddy_logs` volume，证书保存在 `caddy_data` volume；游戏日志为容器 stdout。日志不应包含隐藏手牌、牌堆顺序或完整重连 token。

升级：确认代码变更并在低峰时运行 `bash scripts/deploy.sh`。脚本快进拉取代码、记录真实 commit、构建镜像、等待容器健康，并进行 HTTPS/WSS smoke；失败返回非零。升级会结束当前内存对局。不要在有活动对局时无通知升级。

回滚：`git checkout <已验收提交>`，把 `.env.production` 中的 `BUILD_COMMIT` 改为该提交，然后执行 `docker compose -f docker-compose.production.yml up -d --build --wait`，再次运行 smoke。回滚同样结束当前对局。

故障排查：证书失败时检查 DNS、80/443 防火墙和 Caddy 日志；502 时检查 `web-game` 健康及 Python 日志；WebSocket 被拒绝时确认 `PUBLIC_ORIGIN` 精确等于 `https://DOMAIN`；Host 被拒绝时确认域名与 `DOMAIN` 一致；构建失败时检查 Node/npm 与 Python 阶段日志。生产只运行 Caddy 和单 worker 后端，不运行 Vite 开发服务或 `--reload`。

备份只需安全保存部署配置、`.env.production` 和代码或镜像。Caddy 证书可重新申请。对局状态不持久化，无法从备份恢复进行中的对局。

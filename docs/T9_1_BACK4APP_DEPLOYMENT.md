# T9.1 Back4app Containers 部署

本仓库根目录 `Dockerfile` 是唯一的 Web 生产镜像来源；它先构建 React/Vite，再用 FastAPI 提供网页、`/api`、`/ws`。T8.5 Relay 镜像位于 `Dockerfile.relay`，`docker-compose.yml` 已显式选用它。`Dockerfile.production` 已删除，避免两份生产镜像漂移。

## 创建应用

1. 把 `t9.1-production-deploy` 分支提交推送到你连接 Back4app 的 Git 仓库。创建 Containers 应用时选择此分支，Root Directory 选仓库根目录。Back4app 会读取根目录 `Dockerfile`。
2. 创建页面填写 **Port: `8000`**、**Health check: `/health`**。不要填写 Relay 的 `8765`。
3. 初次创建时设置环境变量：`BACK4APP=true`、`APP_ENV=production`、`PORT=8000`、`APP_VERSION=0.3.0`，以及独有的 `SECRET_KEY`（至少 32 字符）。可在本机运行 `python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成密钥；只把结果填入平台变量，不提交到仓库。可选填 `BUILD_COMMIT` 为本次 Git 提交号，供 `/api/version` 展示。
4. 此时平台尚未给出 `b4a.run` 地址，**不要**填通配域名、其他人的域名或关闭 Host/Origin 校验。首次构建可完成，但应用启动会因缺少 `DOMAIN` 和 `PUBLIC_ORIGIN` 而明确失败；这是预期的安全关闭状态。创建应用后到概览或 Domains 页面复制平台实际分配的完整 `b4a.run` 主机名。
5. 在应用环境变量中设置 `DOMAIN=实际主机名.b4a.run`（无协议、端口和路径），以及 `PUBLIC_ORIGIN=https://实际主机名.b4a.run`（末尾无 `/`）。保存后重新部署同一提交。不要把示例值照抄。若平台提供不同的实际主机名，以控制台显示为准。

配置完成后，服务在容器内监听 `0.0.0.0:$PORT`，固定 **1 个 worker**；`PORT` 未设置时默认 `8000`。游戏房间存在单进程内存中，重启或重新部署会结束进行中的对局；不要把服务扩成多个 worker 或多个独立实例。

## 验收

1. 打开 `https://你的实际主机名.b4a.run/`、`/health` 和 `/api/version`。健康接口应返回 `status: ok`；版本接口应返回 `app_version`、`build_commit` 和 `protocol_version`。
2. 浏览器从 HTTPS 页面连接同源 `wss://你的实际主机名.b4a.run/ws`。用两个浏览器分别创建和加入房间，验证准备、选将和进入牌桌；也可运行 `python scripts/smoke_production.py https://你的实际主机名.b4a.run`。
3. 若健康检查失败，先核对 `PORT`、`DOMAIN`、`PUBLIC_ORIGIN`、`SECRET_KEY` 和容器日志。生产 Host 只允许 `DOMAIN`，WebSocket Origin 只允许精确的 `PUBLIC_ORIGIN`；不要通过放宽这两项排错。镜像内部健康检查会携带已配置的 `DOMAIN` Host 请求 `/health`。

Back4app 的[部署准备说明](https://www.back4app.com/docs-containers/prepare-your-deployment)要求在项目根目录提供 Dockerfile；[容器排错说明](https://www.back4app.com/docs-containers/troubleshooting)要求镜像暴露应用监听端口；[域名说明](https://www.back4app.com/docs-containers/custom-domain)说明每个容器应用会获分配 `b4a.run` 地址。本文件描述的是部署准备与验收步骤，公网运行结果须在应用创建并重新部署后实际检查。

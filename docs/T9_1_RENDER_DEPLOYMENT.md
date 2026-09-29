# 在 Render Free 部署网页版三国杀

此方法得到一个 `https://…onrender.com` 公网网址。玩家只需打开这个网址，房主创建房间、分享房间码，朋友用另一个浏览器加入。无需购买 VPS、域名或证书。Render 会负责公网 HTTPS；容器只运行单个 FastAPI/Uvicorn 进程，并提供 React/Vite 已编译页面。原有 Docker Compose + Caddy 部署方式仍可单独使用。

## 一、把本地项目放到 GitHub

1. 注册或登录 [GitHub](https://github.com/)，打开右上角 `+` → `New repository`。
2. 填写仓库名，例如 `sanguosha-web`。可选 Private（Render 连接你的 GitHub 帐号后也能读取获授权的私有仓库）。**不要**勾选添加 README、`.gitignore` 或 License，因为本地仓库已有提交。点击 `Create repository`。
3. 复制 GitHub 给出的仓库 HTTPS 地址，形如 `https://github.com/你的用户名/sanguosha-web.git`。在本机项目 `C:\Sanguosha` 的终端运行（将地址替换为自己的）：

   ```powershell
   git status
   git remote add origin https://github.com/你的用户名/sanguosha-web.git
   git push -u origin t9.1-production-deploy
   ```

   当前本地仓库没有配置 Git remote；如果你后来已添加 `origin`，先运行 `git remote -v` 核对地址，不要重复添加。推送时按 GitHub 提示登录。确认 GitHub 网页中能看到 `render.yaml`、`Dockerfile`、`web/` 和 `src/`。不要上传 `.env.production`、`SECRET_KEY` 或登录凭据。

## 二、创建 Render Web Service（推荐：Blueprint）

1. 打开 [Render Dashboard](https://dashboard.render.com/) 并注册/登录。点击右上角 `+ New` → `Blueprint`。
2. 若尚未连接 GitHub，按页面提示授权 Render 访问刚创建的仓库。选中该仓库，点击 `Connect`。
3. Blueprint 分支选择 `t9.1-production-deploy`，Blueprint Path 保持仓库根目录的 `render.yaml`。检查预览只包含 **一个**名为 `sanguosha-web` 的 Free Web Service，不包含数据库或 Caddy，然后点击 `Deploy Blueprint`。
4. `render.yaml` 会指定根目录生产构建文件 `Dockerfile`、启动命令 `python -m sanguosha.web`、健康检查 `/health`、单个 Free 服务，并让 Render 自动生成 `SECRET_KEY`。Render 在部署日志中显示构建与启动进度。名称冲突时可以在创建界面选择可用的服务名。

## 三、手动创建 Web Service（不使用 Blueprint 时）

在 Dashboard 点 `+ New` → `Web Service` → `Git Provider`，连接 GitHub 仓库并点 `Connect`。填写：

| Render 字段 | 填写内容 |
| --- | --- |
| Name | 自选可用名称，例如 `sanguosha-web` |
| Branch | `t9.1-production-deploy` |
| Root Directory | 留空（项目根目录） |
| Language / Runtime | `Docker` |
| Dockerfile Path | `./Dockerfile` |
| Docker Build Context | `.` |
| Build Command | Docker 模式无需填写；Render 按 Dockerfile 执行 Node/Vite 和 Python 构建 |
| Docker Command / Start Command | `python -m sanguosha.web` |
| Instance Type / Plan | `Free` |
| Health Check Path | `/health` |
| Auto-Deploy | `On Commit` |

在 `Advanced` / `Environment` 里设置 `APP_ENV=production`、`APP_VERSION=0.3.0`、`LOG_LEVEL=INFO` 和 `SECRET_KEY`。生成密钥：在自己电脑终端运行 `python -c "import secrets; print(secrets.token_urlsafe(48))"`，把输出**只粘贴到 Render 的 `SECRET_KEY` 值栏**，不要放进 Git。最后点击 `Create Web Service` / `Deploy`。

Render 自动提供 `PORT`（默认 10000）、`RENDER_EXTERNAL_HOSTNAME`、`RENDER_EXTERNAL_URL` 和 `RENDER_GIT_COMMIT`。程序会优先读取 `PORT`，绑定 `0.0.0.0:$PORT`，只启动 **1 个 worker**；还会用 Render 的准确主机名和 HTTPS URL 限制 Host 与 WebSocket Origin。`DOMAIN` 和 `PUBLIC_ORIGIN` 因此可以留空，不会放开任意来源。如果想在 Dashboard 显式填写，先等 Render 分配地址，再设置 `DOMAIN=你的服务名.onrender.com`、`PUBLIC_ORIGIN=https://你的服务名.onrender.com`；两者必须与实际网址完全一致，不要加结尾 `/` 或 `*`。更改环境变量会触发重新部署。

## 四、找到网址并验证

打开 Render 服务详情页，在顶部复制 `https://…onrender.com` 地址。首次访问可能需等待空闲实例启动。依次打开：

- `https://…onrender.com/`：应看到游戏首页。
- `https://…onrender.com/health`：应显示 `"status":"ok"`。
- `https://…onrender.com/api/version`：应有 `app_version`、`build_commit`、`protocol_version`。其中 `build_commit` 应与 Render 本次 Git 提交一致。

用浏览器 A 打开网址，输入昵称，点「创建多人房间」，记下六位房间码。用另一个浏览器或无痕窗口 B 打开同一网址，输入不同昵称与房间码，点「加入房间」→「准备」。回到 A 点「开始游戏」，两边选将并确认，检查都进入游戏页。HTTPS 页面应使用 `wss://…onrender.com/ws`，无需玩家填写 IP、端口或安装证书。若有 Python 开发环境，还可运行 `python scripts/smoke_production.py https://你的服务名.onrender.com` 检查 HTTPS、版本和两个 WSS 客户端。

## 五、以后更新游戏

在本机修改代码、运行测试、提交，然后 `git push origin t9.1-production-deploy`。Render 连接 GitHub 的 `On Commit` 自动部署会重建并发布新版本；可在服务的 `Deploys` 页面查看状态。不要选择 `Public Git Repository` URL 或 `Existing Image` 作为部署源，因为这两种连接方式不支持所需的 Git push 自动部署。

当前所有房间和对局只保存在一个进程的内存中。**每次自动部署、实例休眠或平台重启都会结束进行中的牌局**，所以有人在玩时不要随意 push。Render Free 实例在空闲一段时间后会休眠，唤醒可能需要等待；此时页面会显示连接状态。如果旧房间已消失，页面会提示「服务器已重新启动，本局已结束」并提供返回首页。免费方案的容量、时数和流量限制以 [Render Free 官方说明](https://render.com/docs/free) 为准。

若部署失败，先看 Render 服务的 `Logs` 与 `Events`：端口错误应检查启动命令、`PORT`；`DOMAIN`/`PUBLIC_ORIGIN` 不一致会使生产启动失败；`SECRET_KEY` 缺失会明确失败；`/health` 不成功时检查 Docker 构建和启动日志。Render 平台会为公网访问提供 HTTPS 和 WebSocket 代理，不要在 Render 服务内启动 Caddy 或多个 Uvicorn worker。

官方参考：[Web Services](https://render.com/docs/web-services)、[Docker 部署](https://render.com/docs/docker)、[Blueprints](https://render.com/docs/infrastructure-as-code)、[默认环境变量](https://render.com/docs/environment-variables)、[自动部署](https://render.com/docs/deploys)、[GitHub 连接](https://render.com/docs/git-provider)。

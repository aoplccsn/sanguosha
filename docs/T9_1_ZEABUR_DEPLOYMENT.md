# T9.1：使用 Zeabur 部署网页版三国杀

> **先看平台限制（核对日期：2026-09-29）**：Zeabur 的 [Free Plan 说明](https://zeabur.com/docs/en-US/pricing/free-plan) 写着无需信用卡，但 [官方变更公告](https://zeabur.com/changelogs/phasing-out-shared-cluster) 写明：2026-03-15 起不能再在共享集群建新项目，原有免费共享集群也改为需要付费订阅；[创建项目说明](https://zeabur.com/docs/en-US/deploy/create/create-project) 现在要求选择已有服务器、购买服务器或绑定外部服务器。因此，**按现有官方政策，新用户无法仅凭 Free Plan、零服务器费用完成此部署**。本指南把代码和操作准备好；若你的实际控制台以后提供新的免费计算资源，可以继续。若只看到付费或自有服务器选项，就停在这一步，不要为了照做而付款。本项目尚未完成 Zeabur 公网实测。

部署后若平台允许，应得到 `https://你的名字.zeabur.app`。这个地址由 Zeabur 生成，不需购买域名。容器复用 `Dockerfile.production`，构建 React/Vite 页面并用单 worker FastAPI 提供网页、`/api` 和 `/ws`；不运行 Caddy。现有 VPS 和 Render 部署文件仍保留。

## 1. 把项目放到 GitHub

1. 打开 [GitHub](https://github.com/)，注册或登录。右上角点 `+` → `New repository`，输入仓库名，例如 `Sanguosha`。不要勾选自动添加 README、`.gitignore` 或 License；本地仓库已有这些内容。点 `Create repository`。
2. 在电脑上打开 PowerShell，进入 `C:\Sanguosha`，运行 `git status` 和 `git remote -v`。当前仓库可能有**示例占位 remote**，必须先核对它是否真是你自己的 GitHub 地址。若不是，在 GitHub 新仓库页面复制实际 HTTPS 地址，然后运行 `git remote set-url origin https://github.com/你的用户名/Sanguosha.git`；若没有 origin，运行 `git remote add origin https://github.com/你的用户名/Sanguosha.git`。
3. 确认代码已测试并提交后，运行 `git push -u origin t9.1-production-deploy`。按 GitHub 提示完成登录。刷新 GitHub 仓库页面，确认能看到 `Dockerfile.production`、`zbpack.json`、`web/`、`src/`。不要把 `SECRET_KEY`、`.env.production` 或密码放进仓库。

## 2. 注册 Zeabur，检查能否创建免费项目

1. 打开 [Zeabur](https://zeabur.com/)，用 GitHub 帐号注册/登录。查看帐户的计划页面，确认是 `Free Plan`，且没有让你升级或输入信用卡。Zeabur 可能另有帐户验证要求；按页面实际要求判断，但本指南不要求绑定信用卡。
2. 在 Dashboard 点 `Create Project` / `New Project`。如果能选**明确标为免费且不需要自备服务器**的计算资源，就选择它，给项目起名，例如 `sanguosha-web`。如只看到 `Select Existing Server`、`Buy New Server`、`Bind External Server`，且你没有已经免费的可用服务器，**停止**：当前 Zeabur 产品不满足“零服务器费用”的目标。不要把 Free Plan 帐号误认作免费服务器。
3. 若成功进入空项目，继续下一步。平台按钮可能改名；以 [创建项目官方说明](https://zeabur.com/docs/en-US/deploy/create/create-project) 为准。

## 3. 连接 GitHub 仓库并创建服务

1. 在项目中点 `Add Service` / `Create Service` → `Git Repository` / `GitHub`。首次使用时点连接 GitHub，授权 Zeabur 读取刚创建的仓库；如果只授权选定仓库，确保勾选 `Sanguosha`。选择该仓库与 `t9.1-production-deploy` 分支。不要选择预制镜像或仅填写公开 Git URL，否则后续自动部署能力可能不同。详见 [GitHub 集成说明](https://zeabur.com/docs/en-US/deploy/methods/github-integration)。
2. Root Directory 保持仓库根目录。仓库内的 `zbpack.json` 明确指定 `Dockerfile.production`，避免 Zeabur误用根目录另一个 `Dockerfile`。Zeabur 的 [Dockerfile 说明](https://zeabur.com/docs/en-US/deploy/methods/dockerfile) 支持这种路径配置。构建命令和启动命令可留空，使用 Dockerfile：启动脚本在 `ZEABUR=true` 时执行 `python -m sanguosha.web`，监听 `0.0.0.0:$PORT`，固定 **1 worker**。如果控制台要求手填启动命令，填 `python -m sanguosha.web`。
3. 先创建服务。首次构建或启动可能因尚未生成公网域名而失败；这是严格 Host/Origin 校验阻止未知域名，并非需要关闭校验。继续生成域名和填写变量，然后重部署。

## 4. Generate Domain，填写环境变量

1. 打开该服务的 `Domains` / `Public Networking` 标签，点 `Generate Domain`。选择一个可用名字，得到形如 `friends-sanguosha.zeabur.app` 的域名，复制**实际显示的**完整名字。不要填星号 `*.zeabur.app`。Zeabur 的 [公网网络说明](https://zeabur.com/docs/en-US/deploy/networking/public-networking) 介绍了这个按钮。
2. 打开服务的 `Variables` / `Environment Variables` 标签，逐项添加以下值。示例域名必须替换为上一步自己的实际域名：

   | 变量 | 值 | 说明 |
   | --- | --- | --- |
   | `ZEABUR` | `true` | 选用 Zeabur 动态端口启动方式 |
   | `APP_ENV` | `production` | 启用生产环境检查 |
   | `DOMAIN` | `friends-sanguosha.zeabur.app` | 只填主机名，不加 `https://`、端口或 `/` |
   | `PUBLIC_ORIGIN` | `https://friends-sanguosha.zeabur.app` | 必须正好是 `https://` + `DOMAIN`，末尾无 `/` |
   | `SECRET_KEY` | 自己生成的随机密钥 | 至少 32 字符；只存在 Zeabur Dashboard 中 |
   | `LOG_LEVEL` | `INFO` | 可选 |

3. 在本机 PowerShell 运行 `python -c "import secrets; print(secrets.token_urlsafe(48))"`，把输出复制到 Zeabur 的 `SECRET_KEY` 值栏。**不要提交进 Git**。Zeabur 通常自动注入 `PORT`，不要写死端口；程序会优先读取它。若界面没有注入 `PORT`，可在 Variables 添加 `PORT=8000`，与 Dockerfile 的 `EXPOSE 8000` 一致。`HOST` 无需填写，Zeabur 模式自动绑定 `0.0.0.0`。
4. `DOMAIN` 和 `PUBLIC_ORIGIN` 也可以分别填 `${ZEABUR_WEB_DOMAIN}` 与 `${ZEABUR_WEB_URL}`，Zeabur 文档列出这两个 Git 服务专用变量；**第一次部署建议填实际值**，更容易核对。不要使用 `*`、`allow all` 或其他人的域名。保存变量后点 `Redeploy` / `Deploy`，在 `Deployments` / `Logs` 查看构建和启动结果。健康检查如可配置，路径填 `/health`。[变量说明](https://zeabur.com/docs/en-US/deploy/config/environment-variables)。

## 5. 检查网址和双浏览器游戏

1. 在 `Domains` 标签复制 `https://friends-sanguosha.zeabur.app`（换成实际地址）并打开，应出现游戏首页。打开同域名的 `/health`，应返回含 `"status":"ok"` 的 JSON；打开 `/api/version`，应返回 `app_version`、`build_commit`、`protocol_version`。版本的 `build_commit` 可能显示 `unknown`，不影响游戏；以 Zeabur 部署记录核对实际提交。若页面打不开，先看部署日志、`PORT`、`DOMAIN`、`PUBLIC_ORIGIN` 和 `SECRET_KEY`。
2. 用浏览器 A 打开网址，输入昵称，点「创建多人房间」，记下房间码。用另一浏览器或无痕窗口 B 打开**同一网址**，输入另一个昵称和房间码，点「加入房间」并「准备」。回到 A 开始游戏，确认两边都能进入。HTTPS 页面自动连接同源 `wss://你的域名/ws`，不需填写 IP 或开发端口。
3. 如果有 Python 开发环境，也可运行 `python scripts/smoke_production.py https://friends-sanguosha.zeabur.app`，对 HTTPS、版本和两个 WebSocket 客户端做自动检查。

## 6. 后续更新和实例重启

本地修改后运行全量 Python pytest、Vitest、Playwright 和 Vite production build，再提交并执行 `git push origin t9.1-production-deploy`。连接 GitHub 的服务通常会按提交自动重新部署；在 Zeabur Dashboard 的部署记录确认新提交已上线。

房间和对局只存在于**一个进程的内存**中。每次 push 触发重新部署、免费实例休眠或平台重启，正在进行的牌局都会结束，**有人正在玩时不要随意发布**。旧房间丢失时客户端应显示「服务器已重新启动，本局已结束」，让玩家返回首页重新建房。不要把服务扩成多个 worker 或多个实例，否则玩家可能进入不同的内存房间。

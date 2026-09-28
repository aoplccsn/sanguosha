# 五人三国杀身份局（T6 baseline）

当前 T6 已通过正式验收。Windows GUI 默认使用经典军争 160 张实体牌、43 种卡牌定义；基础牌、普通锦囊、延时锦囊及装备规则已接入。真人为主公，与四名 AI 进行五人身份局。武将仍为无技能占位模型。

## 安装与启动

需要 Python 3.12 或更新版本。在项目目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m sanguosha
```

已有 `C:\Sanguosha\.venv` 可直接启动，不需要重新创建。点击“开始游戏”，选择可用手牌，再选择金光目标并确认；多目标牌可选择多个目标。响应、公共牌、材料选择及弃牌通过相应提示和确认按钮完成，AI 回合自动推进。

## 当前范围

- 经典军争牌堆：标准 104、EX 4、军争 52 张；原固定实体牌 manifest 保持不变。
- 6 种基础牌、12 种普通锦囊、3 种延时锦囊、22 种装备；距离、判定、无懈、属性传播、濒死救援及装备特效已验证。
- 40 种新增定义各有独立原创国风水墨卡图，通过 ResourceManager 和 manifest 加载。
- 目标选择、高亮、确认，装备/判定区、五谷公共牌、铁索状态及新增响应已接入 GUI。对手手牌不公开牌面，隐藏身份按规则显示。
- AI 可处理新增请求，但策略仍简单且可读取内部身份。武将技能、T6.5 主界面重构及 T7 尚未开始。
- 八卦阵的卡图造型调整由用户明确延期；当前规则行为已通过测试。
- GameSession 保留 basic 兼容模式供历史测试使用；正式 GUI 默认军争 160 张。

## 测试与验收

```powershell
.\.venv\Scripts\python.exe -m pytest
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe docs/validate_t6.py
```

T6 正式验收：167 passed、0 failed、0 warnings；43 种卡牌渲染及 seed 1–5 引擎/GUI 重复整局通过。提交 baseline 前另行运行完整测试。

见 [T6 验收](docs/T6_2026-09-28.md)、[验证记录](docs/T6_VALIDATION.json)、[部署记录](docs/T6_DEPLOYMENT.json)、[中断恢复](docs/RECOVERY_2026-09-28.md)、[原创卡图](docs/T6_ART.md) 和 [架构](docs/ARCHITECTURE.md)。早期规格与断点文档保留其历史含义，当前完成情况以 T6 验收记录为准。

## Git baseline 范围

提交正式 src、tests、assets（含美术源文件）、data（含 160 张牌清单）、scripts、docs 和项目配置。环境、缓存、恢复备份、staging 与历史验证副本由 .gitignore 排除，继续保留在本机。

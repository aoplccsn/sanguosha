# T17A 专项验证结果

2026-10-04（Asia/Shanghai），基线88ca556。使用项目现有Python、`-B`禁止写入运行目录的pyc。

```powershell
& C:\Sanguosha\.venv\Scripts\python.exe -B C:\Sanguosha\docs\t17\validate_catalog.py --repo C:\Sanguosha --self-test
```

生成稿与复制进项目后的最终目录均已运行该脚本；上述命令在最终目录返回PASS。

| 检查 | 结果 |
| --- | --- |
| 38名完整记录、所需字段与全部技能说明 | PASS |
| 11 + 12 + 11 + 4 | PASS |
| 现行65 + 新增38 = 目标103 | PASS |
| General ID唯一且不与现行65冲突 | PASS |
| 69个Skill ID无不兼容重复 | PASS |
| 已有技能复用标记（仅马术） | PASS |
| 钟会排异为觉醒获得，非开局原生技能 | PASS |
| 中文名、HP、势力、性别与固定源码节选 | PASS |
| 神甘宁初始3、上限6 | PASS |
| 精确技能全文/中文tooltip与来源revision一致 | PASS |
| 请求类型只引用现有8个枚举 | PASS |
| 逐将强度/AI/多人/顺序/版本矩阵覆盖 | PASS |
| 逐技能机制/请求覆盖、相对链接/roster锚点 | PASS |
| 31个LOCKED_REFERENCE + 7个QUESTION均有明确状态 | PASS |
| QUESTION都指向version_questions问题 | PASS |
| 顶层production/implemented/playable均false | PASS |

10个负例全部正确拒绝：production开启、缺一将、重复武将ID、与生产ID冲突、错expansion、不存在的PINDIAN请求枚举、技能文本空缺、待定无问题ID、tooltip与技能文本漂移、不兼容技能ID碰撞。自检在内存副本中执行，不污染文档或游戏状态。

这是设计目录完整性及证据一致性检查。官方卡面/勘误认证、版本人工选择与Q07/Q08裁定仍未通过，不能由目录PASS推导为规则实现PASS。没有运行full pytest，没有新增/修改技能实现，没有做UI/公网或美术操作。

Git验收：仅允许暂存docs/t17；提交前检查diff --check、staged文件范围与stat，提交后确认运行文件无diff、生产基线仍65、原有6个T11未跟踪美术目录保留。实际commit hash见最终报告答复。

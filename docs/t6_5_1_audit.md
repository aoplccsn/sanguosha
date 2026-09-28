# T6.5.1 装备与距离审计

规则实现沿用 T6。装备说明元数据与悬停展示在本阶段补齐。`test_t6_equipment_chains.py`、`test_t6_military_basics.py`、`test_t6_equipment.py`、`test_t6_distance.py` 和 `test_t6_5_1_ux.py` 覆盖生产路径；完整 160 牌 GUI smoke 覆盖 AI/GUI 决策与牌实例唯一性。

| 装备 | 规则 | 本阶段展示 | 审计依据 |
| --- | --- | --- | --- |
| 诸葛连弩 | ALREADY CORRECT | FIXED | 出杀次数 modifier、装备移除 |
| 雌雄双股剑 | ALREADY CORRECT | FIXED | 异性目标选项与摸牌 |
| 青釭剑 | ALREADY CORRECT | FIXED | 无视仁王盾 |
| 青龙偃月刀 | ALREADY CORRECT | FIXED | 闪后追加出杀 |
| 丈八蛇矛 | ALREADY CORRECT | FIXED | 主动与响应虚拟杀、双实体材料 |
| 贯石斧 | ALREADY CORRECT | FIXED | 闪后弃两牌造成伤害 |
| 方天画戟 | ALREADY CORRECT | FIXED | 最后一张手牌多目标 |
| 麒麟弓 | ALREADY CORRECT | FIXED | 伤害后弃目标坐骑 |
| 寒冰剑 | ALREADY CORRECT | FIXED | 防止伤害并弃牌 |
| 古锭刀 | ALREADY CORRECT | FIXED | 空手目标增伤 |
| 朱雀羽扇 | ALREADY CORRECT | FIXED | 普通杀转火杀、藤甲交互 |
| 八卦阵 | ALREADY CORRECT | FIXED | 判定视为闪、响应路径 |
| 仁王盾 | ALREADY CORRECT | FIXED | 黑杀过滤、青釭剑忽略 |
| 藤甲 | ALREADY CORRECT | FIXED | 普通杀/锦囊过滤、火伤 |
| 白银狮子 | ALREADY CORRECT | FIXED | 单次伤害上限、替换后恢复 |
| 绝影 | ALREADY CORRECT | FIXED | +1 防御距离 |
| 爪黄飞电 | ALREADY CORRECT | FIXED | +1 防御距离 |
| 的卢 | ALREADY CORRECT | FIXED | +1 防御距离 |
| 骅骝 | ALREADY CORRECT | FIXED | +1 防御距离 |
| 赤兔 | ALREADY CORRECT | FIXED | -1 进攻距离 |
| 大宛 | ALREADY CORRECT | FIXED | -1 进攻距离 |
| 紫骍 | ALREADY CORRECT | FIXED | -1 进攻距离 |

| 距离项目 | 结果 | 证据 |
| --- | --- | --- |
| 存活座次最短环形距离 | ALREADY CORRECT | `DistanceSystem.base_distance`、五人距离测试 |
| 阵亡玩家跳过 | ALREADY CORRECT | 一人及多人阵亡测试 |
| +1 马方向 | ALREADY CORRECT | 目标装备区修正测试 |
| -1 马方向 | ALREADY CORRECT | 出发装备区修正测试 |
| 双马叠加与移除 | ALREADY CORRECT | 同向叠加、立即移除测试 |
| 11 武器攻击范围 | ALREADY CORRECT | 定义值逐件检查、出杀距离规则 |
| 杀合法目标 | ALREADY CORRECT | 统一 `can_reach_with_slash`、范围内外测试 |
| 顺手牵羊 | ALREADY CORRECT | `MilitaryTrickRule` 距离限制、装备变化测试 |
| 兵粮寸断 | ALREADY CORRECT | `MilitaryTrickRule` 距离限制、装备变化测试 |
| GUI 目标与距离反馈 | FIXED | 合法目标高亮原有；本阶段增加基础/最终距离与攻击范围 tooltip |

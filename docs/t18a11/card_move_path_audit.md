# T18A.11 CardMove path audit

rg枚举位置写入并人工追踪：

- engine/card_moves.py：原子CardMoveService与EquipmentExchangeTransaction正式位置写入；校验区域唯一、目标栏和守恒，记录CardMovedEvent。
- engine/skills.py观星：只重排同一draw_pile，保持集合，不跨区域移动。
- engine/yj2013.py胆守：deepcopy或copy(state)+独立zones/zone对象模拟耗武器/马后的距离；仅探测副本，不修改live区域，实际成本通过transfer/CardMove。
- engine/skills.py武圣：耗装备后的距离与杀次数使用隔离zone副本，真实成本走CardMove。
- multiplayer/room.py _prepare_lvbu_review_match：显式review_god_lvbu本地review夹具直接把牌堆牌放入手牌；不属于正常对局技能路径，守恒但不记录常规移动事件。
- session初始发牌、snapshot恢复及docs/t18a11/audit_server.py本地场景准备单独分类为初始化/证据夹具；不能冒充正式技能移动。

两组100场模拟每步GameState不变量检查，新增重铸使用独立RECAST原因：不得触发discard专属落英/纵玄，不计使用专属集智/精策。仍需要检查全部动态别名写入、每技能移动批次与跨技能反应，状态BLOCKED；这是位置写入路径证据，不是全189技能CardMove语义PASS。

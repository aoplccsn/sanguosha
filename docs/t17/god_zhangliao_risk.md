# 神张辽夺锐与动态技能所有权（Tier 4）

基础版候选有技能获得/原主失效，OL档案仅使失效并结束出牌，不混用；Q06未解除之前不实现。下面是架构边界及保守可审核候选规则，不能假冒官方额外禁夺清单。

## 当前证据与缺口

SkillDefinition（model/skill.py）是冻结id/name/description/type/metadata；不应保存拥有者、计数或被夺状态。PlayerState只有granted_skills: dict[skill_id, source_string]、disabled_skills: set[skill_id]、transformation_pool/active_transformation/transformation_skill。SkillRegistry.has同时判断原生、grant、化身以及无前/极略特例；suppression是全技能id集合。distance.py马术直接查原生技能，动态获得不一定生效。神司马懿极略分支散落gods/card_use/judgment/military_basics等，不是五个独立永续技能。

当前结构会把同一技能的多个来源覆盖；结束租借时remove skill_id可能删除觉醒或化身获得技能；取消disabled_skills可能恢复已被断肠的技能。不能靠在夺锐中添加另一个if解决生命周期。

## 定义边界（拟定接口，不实现）

- SkillDefinition：唯一语义id，分类标签locked/awakening/lord/limited/conversion/compound、状态schema、可授予/可租借策略、依赖。同名不同语义不能共享definition（纵适/宗室、结营/劫营必须不同ID）。
- SkillSource：NATIVE_GENERAL、AWAKENING_GRANT、HUASHEN、JILUE_INTERNAL、TEMP_EFFECT、DUORUI_LEASE；有source_general_id/source_ownership_id/source_effect_id，不能只用字符串猜出处。
- SkillOwnership：ownership_id、holder_id、definition_id、source、acquired_event、expiry、private_state；同definition多个ownership可并存。
- SkillSuppression：suppression_id、目标ownership_id、原因effect_id与expiry；有效技能=存活有效来源至少一份且未被对应suppression阻断。断肠的永久禁用与夺锐临时禁用独立存在。
- SkillLease：lease_id、borrower、victim、victim_ownership_id、borrower_ownership_id、started_event、target_next_turn_token、expire_on死亡/回合末；仅移除自己的grant/suppression，不恢复其他失效原因。
- SkillService：eligible_for_duorui(victim)→ownership tokens；grant/lease/suppress/revoke(effect_id)；effective_definitions(holder)；on_source_changed/on_death/on_turn_end。所有合法性、Distance/ViewAs/Projection/AI统一查询service，不直接读character.skill_ids。

## 可夺范围：逐类规则提案

| 类别 | 基础版候选处理 | 风险/人工门禁 |
| --- | --- | --- |
| 普通原生主动/触发/ViewAs | 可夺，必须是目标武将牌有的有效技能；使用借用者自身成本/牌 | 名称不是身份绑定的handler硬编码；每个definition须借用兼容审计 |
| 锁定技 | 基础版不应因“锁定”一律排除；合格原生锁定可夺 | locked与awakening不同；伤害改写、上限、距离光环须即时更新 |
| 觉醒技 | 排除 | metadata awakening；不能用SkillType.TRIGGERED误允 |
| 主公技 | 排除，当前持有者是否主公也不改变分类 | metadata lord；非主公隐藏也不能列候选 |
| 限定技 | 排除 | 不复制/转移限定已用mark，不为借用者刷新一次 |
| 转换技 | 基础版排除清单未必含转换；默认不凭空排除，Q06待裁 | 借用者新ownership独立初始化，不搬原主状态；龙怒首态Q04未决，暂不支持实现 |
| 觉醒后获得技能（如排异、极略） | “仅武将牌技能”候选规则下不列原生可夺；Q06确认 | 已获得不等于原生；不能静默宣称官方禁止 |
| 左慈化身临时技能 | 候选仅NATIVE下不夺 | 不泄露化身池，不停其整个池，不清transformation_skill；若官方允许须单独再设计 |
| 左慈原生化身/新生 | 原生普通可夺范围可能包含，不能擅自从官方候选排除 | 化身私有状态独立创建，不能复制受害者池；现行has绑定mountain_zuoci不支持借用；标为BLOCKED_IMPLEMENTATION直到补通用适配 |
| 神司马懿原生忍戒/连破 | 满足元数据可夺 | 新借用忍戒不拷原主忍；连破额外回合归借用者；原主已有待结算效果按快照裁 |
| 神司马懿拜印 | 觉醒排除 | 当前id baoyin（非拼音baiyin），必须沿用现有id |
| 极略本体（拜印获得） | 非原生候选不夺，若FAQ允许需重新决定 | 获得后source=AWAKENING_GRANT，不是五个内部技能的所有权 |
| 极略内部鬼才/放逐/集智/制衡/完杀 | 不列五个独立夺锐候选 | 扣忍的组合能力，不注册独立永久grant；已有独立原生鬼才等仍按其真实ownership判定 |
| 父魂临时武圣/咆哮、无前临时无双 | source=TEMP_EFFECT，不夺候选 | 原生关羽武圣/张飞咆哮/吕布无双仍允许；同名不能误一起禁用 |
| 已夺锐获得技能 | source=DUORUI_LEASE不递归再借 | 避免环与无限lease；此限制属提案，Q06需确认“武将牌”边界 |
| 隐匿/使命/现代类别 | T17没有，引擎元数据拒绝未审计特殊类别 | 社区当前排除括号不当2018原始卡面证据 |

## 租借生命周期与状态

1. 实际PLAY伤害结束后重检两人存活、神张辽仍有夺锐、没有有效lease、目标存在合格技能；无候选不付废栏费用。
2. 选可废槽（空槽也可废候选）→弃原装备并正常离装反应→统一完成费用→选ownership→创建借用grant及原主suppression。期间死亡/候选消失要按卡面/FAQ裁，不能回滚已发生的离装反应。全废栏能否无费用发动Q06。
3. lease有效期绑定目标“下一回合结束”，不是神张辽自己回合末，也不是全局turn_number+1。翻面跳过回合依然需要最终回合边界；额外回合按真实target turn_token。若发动时不是自己的出牌阶段不允许。
4. 目标死亡立刻到期；神张辽死亡也清借用grant与该lease的失效原因；游戏结束统一清理。神张辽失去夺锐时lease是否继续按期限存在待FAQ，不盲目恢复原主。
5. 原主改化身/原技能来源撤销，不复活不存在的ownership；借用者已有同技能则多个来源共存，调用效果避免同一技能双触发与重付成本。
6. skill state位于ownership，不搬原主牌堆/星/田/化身/权/怒/忍；借用新生/忍戒可能不完整但这是机制风险，不能复制资源补强。持续光环失效立即撤销其作用；已经合法承诺的use/action继续还是重检以明确事件窗口为准。
7. 存档必须含grant、source、suppression、lease、expiry与私有状态；Projection仅公开应公开的技能名称与期限，私有池按holder过滤。

## 高风险组合与测试

- 左慈原生化身失效时势力/性别回原生，恢复后旧池保存或重新初始化依FAQ，不因租借把两玩家池指向同对象；借用者不读取原池。
- 断肠永久失效+夺锐到期：仅删lease suppression，仍禁用；已有觉醒grant与同名临时grant不被误删除。
- 极略忍计数与五内部功能不分裂；失去极略时临时完杀来源撤销按scope；获得普通鬼才不自动获忍戒。
- 马术/飞影等获得/失效实时改变距离与目标候选；陈宫智迟/神刘备结营等持续效果来源撤销与回合边界幂等。
- 拼点平局不触发止啼赢；决斗胜须专用结果事件而非所有duel damage；被伤来源为空不可恢复栏；恢复装备栏不凭空补装备。
- 两神张辽候选未来多副本：lease不得形成环，target ownership独占租借的策略需裁定；现正式选将唯一id不把多副本视为已支持。
- 每个选择暂停点重连、60秒fallback、重复ACK都不能重复废栏/获得技能/恢复技能；毒化未知ownership_id必须拒绝。

验收门禁：所有新增/既有定义完成borrowability元数据审计与状态schema迁移以后才实现神张辽。用户可后续决定另选官方版本或不加入；T17A不自创删技能平衡版。

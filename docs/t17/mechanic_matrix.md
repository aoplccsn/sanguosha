# 引擎依赖审计（仅设计）

38/38 项目最终版本于2026-10-04按用户决定LOCKED。锁定不等于官方卡面已验证：证据保持固定revision社区档案，authority_status不变。2012/2013/四神仍为catalog only；生产65。


证据为88ca556工作树src/sanguosha，不是Cloudflare副本。A是所需基础动作已存在且可复用；B是已有原语需要扩展通用接口/窗口；C是缺少相应通用primitive。已有某个武将专用handler不能等同所有新技能已支持。下表接口都是提案，没有新增运行代码。

| 依赖键 | 类 | 代码证据 | 拟定接口与语义 |
| --- | --- | --- | --- |
| MOVE | B | engine/card_moves.py: CardMoveService.move；military_equipment.py: MilitaryMoveService | move_batch(moves, batch_id, reason, owner/source provenance)：校验全批后发布移动与反应，避免落英/纵玄竞争重复获得 |
| REACTION | B | engine/events.py；military_equipment.py.next_reaction；wind/forest/mountain/gods现有专用handler | reaction_window(event, priority, once_key)：按点伤/一次伤害/整批移动区别调度，死者触发走专用窗口 |
| VIEWAS | B | model/virtual_card.py: VirtualCard；engine/card_use.py；skills.py的手牌候选 | view_as(definition, materials, forced, scope)：扩全手牌锦囊与强制身份变换，保留有效花色/颜色与材料区域 |
| TARGET | B | engine/card_rules.py；military_basics.py杀次数和防具；fire.py天义 | target_policy(use_id, source, target, scope)：区分合法指定/效果无效/次数豁免/距离忽略/范围无限；保留锦囊特殊目标 |
| HPREWRITE | B | engine/military_basics.py: MilitaryDamageHandler，已有天香/大雾；hp.py | rewrite_damage(context)->CANCEL/LOSE_HP/MODIFIED：绝情在伤害事件前改HP流失，取消只取消该目标该伤害，不清ResolutionStack |
| MAXHP | A | engine/hp.py: LoseMaxHpAction/GainMaxHpAction | 直接复用maxHP变化动作与濒死管线，禁止将上限减少误当伤害 |
| JUDGMENT | A | engine/judgment.py: JudgmentAction | 直接复用判定与改判管线，取最终判定花色/颜色，不自行抽牌替代判定 |
| PINDIAN | B | engine/pindian.py: PindianAction返回bool并立即弃牌 | PindianResult(source_card, target_card, ranks, winner, tie) + pre_cleanup窗口；原两次CHOOSE_CARD私密请求复用 |
| VISIBILITY | B | projection.py: gongxin_reveal/特殊牌区；multiplayer/choice_labels.py | VisibilityGrant(grant_id, viewer, subject, cards_or_zone, frame_id, expiry)：只授权发动者；重连重新构造，结束失效 |
| ORDER | B | engine/card_moves.py: to_top已存在；mountain.py观星 | ordered move/list约束 + request choices逐张排序复用；服务端确认首元素为顶，不依赖点击顺序猜测 |
| DEATH | B | engine/death.py: DeathActionHandler已有行殇/断肠/武魂与身份奖惩 | death_windows(before_discard, after_death, before_reward)：扩挥泪/追忆并固定优先级；死者可做最后专用请求 |
| DYING | B | engine/dying.py；hp.py；recovery.py；wind.py不屈/gods.py龙魂 | 沿用濒死栈与恢复，扩补益/仁心/伏枥/醇醪的成本动作与来源，完杀合法性统一 |
| AUTHUSE | B | engine/card_use.py；forest.py乱武；military_basics.py | authorized_use(actor, grantor, definition, targets, costs, quota_policy)：回合外不绕合法性，明策/xuanhuo/xiansi/zhiyan复用 |
| SCOPE | B | engine/turns.py清理固定mark；PlayerState.marks | EffectScope(source_id, target_id, turn_token/phase_token, expiry_event)：规范回合结束/阶段末/目标下回合末；幂等cleanup |
| EXCHANGE | C | 只有单CardMove原子性，无跨角色全装备事务 | EquipmentExchangePlan(snapshot, moves, batch_id).commit：完整槽位交换全部成功或不变，再排离装反应，不逐槽溢出 |
| PHASE | B | engine/turns.py: TurnAction禁止重复phase；skip_标记已存在 | schedule_extra_phase(PLAY, phase_token, before_preparation)：扩重复阶段/独立PlayUsage；阶段跳过原语复用 |
| OWNERSHIP | C | SkillDefinition存在；PlayerState.granted_skills dict、disabled_skills set、transformation_skill独立特例 | SkillOwnership(instance_id, holder, definition_id, SkillSource, active, expiry) + Suppression(effect_id, ownership_id)：独立来源/失效租约 |
| PILE | B | model/zones.py: SPECIAL；projection.py默认特殊区公开 | SpecialPilePolicy(key, owner, viewers, expiry, authority)：区存储/移动复用，按pile配置可见性与授权消费 |
| CATEGORY | B | model/enums.py CardCategory；requests.py只校验候选数量 | canonical_card_type基本/锦囊/装备 + LegalSelection(predicate)：延时锦囊归锦囊；混合弃牌方式禁止 |
| SUBSET | B | requests.py CHOOSE_CARDS无点数/花色组合验证 | selection_predicate(sum_rank≤13 / size4 & suits4 & owners合法) + legal_timeout_selection：验证和timeout同一合法集 |
| DISTRIBUTE | B | engine/skills.py遗计/仁德已有逐请求分牌 | distribution_progress(card_ids, recipient_ids, remaining)：私密逐次选牌/收牌人，断线不重复转牌，正常旧手可选依锁定文本 |
| SEQUENCE | B | ResolutionStack/ResolutionFrame已有cursor/local | SequentialEffect(cursor, threshold, pending_actor, processed_ids)：复用栈续结算；多人并非同时选择，死亡后跳过剩余不合法者 |
| COUNTER | B | engine/events.py CardUsedEvent；play_usage 与 marks | UsageLedger(use_id, turn_token, phase_token, quota_counted)：使用/打出区别、虚拟一张、多目标一张、龙吟不可重复减次数 |
| CONVERT | C | 无通用持久转换状态定义；现有临时view-as | ConversionState(ownership_id, state, phase_token)：按出牌开始切换，费用濒死时不提前进入下一步；状态/临时效果分别持久化 |
| AURA | C | 距离修改器与专用风/星mark存在，无通用跨人持续依赖关系 | Aura(source_ownership, beneficiary_predicate, modifier, expiry)：动态重算连环/范围/受伤/手牌上限；营有唯一effect实例，非裸全局mark |
| SLOT | C | model/enums.py只有4装备槽；设备移动仅占用容量验证 | EquipmentSlotState(enabled, disable_effect_ids)：废栏先弃原装、禁止未来安装；恢复指定一个，费用/移动同事务；无宝物槽 |

## 可完全复用的基础动作

DrawCardsAction、CardMoveService单次draw/discard/obtain的实体唯一位置、LoseHpAction、LoseMaxHpAction、GainMaxHpAction、RecoverAction、JudgmentAction改判、基础距离/装备/翻面/连环状态、PlayerState.marks、VirtualCard数据对象、ResolutionStack的push/ask/continue、PendingRequest/Decision和已有60秒ACK协议。PindianAction选择阶段可复用但结果窗口须扩；技能获得与临时无双存在专用做法但不具备多来源生命周期。阶段跳过已存在，不列成新原语；特殊牌区存储已存在，不另造重复存储；damage source replacement南蛮祸首已有，需接damage pipeline统一时序。属性伤害实际规则在MilitaryDamageHandler，不能因damage.py旧T4仅普通伤害误判为不支持。

## 每技能完整依赖矩阵

每一行都附机制/请求与边界测试，依赖按技能列出。接口字典是通用扩展上界；部分技能只直接组合现有动作/事件，因此该技能列A；复杂依赖按最高缺口列B或C。需要新技能handler不等于需要新engine primitive；动态获得这些技能仍要统一ownership查询。

| 武将/技能 | 类 | 依赖接口 | 机制语义 | 请求 | 边界测试 |
| --- | --- | --- | --- | --- | --- |
| 张春华/jueqing | B | HPREWRITE | 伤害正式产生前改为 LoseHpAction，保留原始行动链但不发布伤害事件；禁止铁索复制；无伤害杀手归因需Q08。 | 自动 | 火杀连环不传导；失去体力无伤害触发；上限变化；伤逝上限2/不封顶 |
| 张春华/shangshi | B | REACTION | 手牌/HP/maxHP变化后，手牌小于已损失体力时请求补至已损失体力；无2张上限；自身摸牌防递归。 | YES_NO | 火杀连环不传导；失去体力无伤害触发；上限变化；伤逝上限2/不封顶 |
| 于禁/yizhong | A（基础动作/事件直接组合；动态ownership仍需C） | TARGET | 被指定可合法；效果阶段黑色杀且无防具则对该角色无效。 | 自动 | 黑杀/红杀/虚拟无色杀；防具被移走；无效非不能指定 |
| 曹植/luoying | B | MOVE, REACTION | 只接受他人牌的弃置与判定弃置批次，逐张重检仍在弃牌堆且有效梅花；对使用/响应弃牌不触发。 | YES_NO, CHOOSE_CARDS | 使用材料不落英；已被获得不可再取；濒死酒诗；翻面跳回合；多点伤害一次翻面 |
| 曹植/jiushi | B | VIEWAS, DYING, REACTION | 酒的合法窗口翻面虚拟使用；伤害扣HP前记录face_up，结算后只按快照决定翻正。 | CHOOSE_OPTION, YES_NO | 使用材料不落英；已被获得不可再取；濒死酒诗；翻面跳回合；多点伤害一次翻面 |
| 法正/enyuan | B | MOVE, REACTION, SEQUENCE | 同一获得批次同一他人来源≥2可令其摸1；实际伤害每点要求来源给一手牌或失去HP，来源为空不要求。 | YES_NO, CHOOSE_OPTION, CHOOSE_CARD | 混合来源不合并恩；两点伤害两次怨；无来源；杀不可用转获得两牌；死亡中止 |
| 法正/xuanhuo | B | AUTHUSE, VISIBILITY, SEQUENCE | 替代正常摸牌，选受益者摸2，法正选其范围内合法杀目标；受益者USE_CARD，不用则法正依次获得其至多2牌。 | YES_NO, CHOOSE_PLAYER, USE_CARD, CHOOSE_OPTION | 混合来源不合并恩；两点伤害两次怨；无来源；杀不可用转获得两牌；死亡中止 |
| 马谡/xinzhan | B | VISIBILITY, ORDER | 一次出牌阶段；手牌>maxHP才私看顶3；可拒绝拿红桃，选择非空红桃集则公开获得；剩余排序。 | YES_NO, CHOOSE_CARDS, CHOOSE_OPTION | 手牌=上限不能发动；红桃0/1/3；顶牌顺序；无来源死亡；挥泪与反贼奖励顺序 |
| 马谡/huilei | B | DEATH, MOVE | 死亡触发，杀手为其他人且有牌则弃其规则范围所有牌；与奖励、行殇优先级须冻结。 | 自动 | 手牌=上限不能发动；红桃0/1/3；顶牌顺序；无来源死亡；挥泪与反贼奖励顺序 |
| 徐庶/wuyan | B | HPREWRITE | 在锦囊导致伤害时若来源或目标拥有技能则取消；不取消牌效果本身；南蛮先替换来源再判断。 | 自动 | 顺手/无中照常；南蛮来源替换；延时锦囊伤害；重置含解连环与翻正；无伤不可回复 |
| 徐庶/jujian | B | MOVE, REACTION | 结束阶段可付一非基本牌成本选其他人，由其选摸2/恢复1/解连环并翻正。 | YES_NO, CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION | 顺手/无中照常；南蛮来源替换；延时锦囊伤害；重置含解连环与翻正；无伤不可回复 |
| 凌统/xuanfeng | B | MOVE, REACTION | 装备离区以移动批次一次触发，或弃牌阶段结束满足≥2；两次区域弃置可相同角色，逐次校验。 | YES_NO, CHOOSE_PLAYER, CHOOSE_OPTION | 换装/甘露/死亡离区；同人两牌逐次合法；不足两牌；成本弃置与规则弃置范围核对 |
| 徐盛/pojun | A（基础动作/事件直接组合；动态ownership仍需C） | REACTION | 杀伤后角色存活时选发动，X=max(0,min(当前HP,5))，摸X再翻面；濒死结算完成后判断。 | YES_NO | 濒死救回后HP；X=0；伤害多点一次；原版不扣牌不增伤 |
| 吴国太/ganlu | C | EXCHANGE, MOVE | 两角色装备数差绝对值≤已损HP；快照所有槽、统一验证、原子交换再发布整批移动及离装反应。 | CHOOSE_PLAYERS | 双方同槽武器/空槽/白银狮子/枭姬旋风；差值边界；基本牌不救；反复濒死 |
| 吴国太/buyi | B | DYING, VISIBILITY | 濒死者手牌背面选1后公开；非基本则弃该牌恢复1；基本仅展示；死亡决定之前处理。 | YES_NO, CHOOSE_OPTION | 双方同槽武器/空槽/白银狮子/枭姬旋风；差值边界；基本牌不救；反复濒死 |
| 陈宫/mingce | B | AUTHUSE, MOVE | 一次出牌阶段给装备或杀，陈宫选合法杀目标，受益者选择视为杀/摸1；不存在目标仅摸1。 | CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION | 杀目标从受赠者计算范围；回合外受伤免后续锦囊；首伤不被自身取消；额外回合清理 |
| 陈宫/zhichi | B | TARGET, SCOPE | 回合外伤后建立当前turn_token内杀和非延时锦囊对本人的效果无效；不撤销首个伤害；回合末统一清理。 | 自动 | 杀目标从受赠者计算范围；回合外受伤免后续锦囊；首伤不被自身取消；额外回合清理 |
| 高顺/xianzhen | B | PINDIAN, TARGET, SCOPE | 一次出牌阶段拼点；胜则以source,target,turn_token绑定杀次数豁免/距离忽略/防具无效，没赢绑定全局禁用杀。 | CHOOSE_PLAYER, CHOOSE_CARD | 平局为没赢；对其他人次数正常；仅杀次数；禁酒含自救酒；虚拟酒材料；回合清理 |
| 高顺/jinjiu | B | VIEWAS | 强制酒身份替换为普通杀，不提供酒自救；虚拟酒及装备区材料解释待语义核对。 | 自动 | 平局为没赢；对其他人次数正常；仅杀次数；禁酒含自救酒；虚拟酒材料；回合清理 |
| 荀攸/qice | B | VIEWAS, TARGET | 成本为使用提交时全部非空手牌；选非延时锦囊definition及合法目标；整组VirtualCard保留材料列表并按普通牌结算。 | CHOOSE_OPTION, CHOOSE_PLAYERS | 手牌0不可奇策；多材料颜色；南蛮/借刀/铁索目标；无懈响应；智愚摸后颜色；无来源 |
| 荀攸/zhiyu | B | REACTION, VISIBILITY | 伤后可摸1并公开当前全部手牌；非空且颜色全同令存活来源弃手牌1；公开展示不永久开启观察权。 | YES_NO, CHOOSE_CARD | 手牌0不可奇策；多材料颜色；南蛮/借刀/铁索目标；无懈响应；智愚摸后颜色；无来源 |
| 王异/zhenlie | B | TARGET, HPREWRITE, DYING | 杀/非延时锦囊被指定后可失去1HP；完成濒死后若仍存活则弃来源牌并令该牌对自己无效；Q08裁顺序。 | YES_NO, CHOOSE_OPTION | 成本濒死/死亡后剩余效果；延时锦囊不可贞烈；秘计分多角色；混旧手牌；不足牌堆 |
| 王异/miji | B | DISTRIBUTE, VISIBILITY | 结束阶段受伤可选n∈[0,已损HP]摸n，随后从当前手牌分配实际获得数量给其他人；每张一次归属。 | YES_NO, CHOOSE_OPTION, CHOOSE_CARDS, CHOOSE_PLAYER | 成本濒死/死亡后剩余效果；延时锦囊不可贞烈；秘计分多角色；混旧手牌；不足牌堆 |
| 曹彰/jiangchi | B | TARGET, SCOPE | 摸牌数修改并加turn-scoped限制；多摸禁止use与respond所有杀，少摸+1次数且不限距离；默认不修改。 | CHOOSE_OPTION | 少摸为0；杀响应决斗也禁；雷火虚拟杀；额外阶段同回合；结束清理 |
| 钟会/quanji | B | PILE, REACTION | 受到每1点伤害可摸1并从当前手牌置1权；特殊牌区权可见性需Q07；持权数增加手牌上限。 | YES_NO, CHOOSE_CARD | 两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己 |
| 钟会/zili | C | MAXHP, OWNERSHIP | 准备阶段权≥3且未觉醒：减maxHP1，选择摸2/回HP1，然后授予排异来源zili；不得预先拥有排异。 | CHOOSE_OPTION | 两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己 |
| 钟会/paiyi | B | PILE, REACTION | 仅自立授予后，每出牌阶段1次弃1权，目标摸2后若手牌>自己的手牌，对其伤害1；可选自己。 | CHOOSE_CARD, CHOOSE_PLAYER | 两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己 |
| 廖化/dangxian | B | PHASE, COUNTER | 回合开始插入PLAY阶段，独立phase_token，后续正常PLAY使用次数独立；背面跳回合顺序Q08。 | 自动 | 背面回合是否当先候选待卡面裁定；两次出牌计数隔离；势力随化身变化；神按现行群 |
| 廖化/fuli | B | DYING | 限定濒死可回复到min(存活有效势力种数,maxHP)，然后翻面；不是额外回合；失败救起继续濒死。 | YES_NO | 背面回合是否当先候选待卡面裁定；两次出牌计数隔离；势力随化身变化；神按现行群 |
| 关兴张苞/fuhun | C | VIEWAS, OWNERSHIP, SCOPE | 两手牌普通杀ViewAs；该牌于PLAY造成实际伤害后授予wusheng,paoxiao到回合末，按来源回收。 | CHOOSE_CARDS, USE_CARD, RESPOND_WITH_CARD | 非出牌阶段不获；伤害被防不获；一阶段多次幂等；已有武圣不误移除；临时来源不夺 |
| 马岱/mashu | A（基础动作/事件直接组合；动态ownership仍需C） | TARGET | 语义复用已存在mashu，但当前distance.py直接查角色原生技能；动态获得/失效须接统一ownership。 | 自动 | 只封手牌不封装备材料；有效颜色红颜；虚拟材料来源；判定改判；回合末解除；不减上限 |
| 马岱/qianxi | B | JUDGMENT, TARGET, SCOPE | 准备阶段判定，选有效距离1角色；本回合按判定最终颜色禁止其手牌使用/打出，逐材料按区域检查。 | YES_NO, CHOOSE_PLAYER | 只封手牌不封装备材料；有效颜色红颜；虚拟材料来源；判定改判；回合末解除；不减上限 |
| 步练师/anxu | B | MOVE, VISIBILITY | 一次出牌阶段选两其他人手牌不同，少者选多者背面手牌公开获得，非黑桃步练师摸1。 | CHOOSE_PLAYERS, CHOOSE_OPTION | 同手牌数不可；不选自己；黑桃不摸；选择者不是步练师；死亡补益；无杀手不排除 |
| 步练师/zhuiyi | B | DEATH | 死亡后允许该技能专用最后选择，目标其他存活者排除杀手，摸3再恢复1；无来源死亡不排除。 | YES_NO, CHOOSE_PLAYER | 同手牌数不可；不选自己；黑桃不摸；选择者不是步练师；死亡补益；无杀手不排除 |
| 程普/lihuo | B | VIEWAS, TARGET, REACTION | 普通杀可转火；所有火杀可增一个目标；只转换杀造成过伤害则整牌结算结束扣HP1一次。 | CHOOSE_OPTION, CHOOSE_PLAYER | 铁索连伤只扣一次；原生火杀不扣HP；醇为空才补；多次救援；完杀；移去醇不是手牌酒 |
| 程普/chunlao | B | PILE, DYING, VIEWAS | 结束阶段没有醇时可存至少一杀；濒死时消耗一醇视为濒死者用酒，通过标准酒自救与濒死管线。 | YES_NO, CHOOSE_CARDS, CHOOSE_CARD | 铁索连伤只扣一次；原生火杀不扣HP；醇为空才补；多次救援；完杀；移去醇不是手牌酒 |
| 韩当/gongqi | B | TARGET, SCOPE | 一次出牌阶段弃任意一牌，本回合攻击范围无限，若装备可再弃其他人牌1；不改通用距离。 | CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION | 攻击范围非距离；武器可来自手/装备；每次选择后重检存活；无武器摸；限定不可重复 |
| 韩当/jiefan | B | TARGET, SEQUENCE | 限定PLAY选角色；按当前席位序依次询问攻击范围含目标者，弃一武器（手或装备）否则目标摸1。 | CHOOSE_PLAYER, CHOOSE_CARD | 攻击范围非距离；武器可来自手/装备；每次选择后重检存活；无武器摸；限定不可重复 |
| 刘表/zishou | B | PHASE | 摸牌阶段可额外摸存活势力数；本回合出牌阶段用牌不能指定其他角色；不跳出牌阶段，回合边界清理限制。 | YES_NO | 满HP不自守；势力种数不是人数；神映射群；化身切换影响；不同原版修订另列 |
| 刘表/zongshi | B | SCOPE | 锁定手牌上限+存活有效势力种数，化身势力经SkillRegistry.faction；神当前映射群不自加新势力。 | 自动 | 满HP不自守；势力种数不是人数；神映射群；化身切换影响；不同原版修订另列 |
| 华雄/shiyong | A（基础动作/事件直接组合；动态ownership仍需C） | MAXHP, REACTION | 实际红色杀或带wine标签杀伤后maxHP-1，每次伤害一次；红且酒不重复。 | 自动 | 红酒杀仅一次；黑酒杀一次；多点仅一次；上限0死亡；无体力流失触发 |
| 曹冲/chengxiang | B | SUBSET | 伤后公开顶4，选择非空子集且rank总和≤13；选中获得余牌弃置，服务端计算不是仅计数检查。 | YES_NO, CHOOSE_CARDS | 和=13允许14拒绝；装备在手或装备区；成本翻面顺序；零装备；多点伤害整体防止 |
| 曹冲/renxin | B | HPREWRITE, MOVE | 别人HP恰为1伤前可翻面、弃装备牌防整次伤害；费用可来自手或装备，所有移动副作用正常触发。 | YES_NO, CHOOSE_CARD | 和=13允许14拒绝；装备在手或装备区；成本翻面顺序；零装备；多点伤害整体防止 |
| 郭淮/jingce | A（基础动作/事件直接组合；动态ownership仍需C） | COUNTER, REACTION | 每次PLAY结束时统计当前turn_token CardUsedEvent数量≥当前HP则可摸2；response不计，虚拟材料不多计。 | YES_NO | 打出不算使用；虚拟牌算一张；当先使用纳入回合；HP变化；不是结束阶段摸 |
| 满宠/junxing | B | CATEGORY, SEQUENCE | 一次PLAY至少1手牌弃置，按三大类型集计算补集，对方弃该补集类型手牌1，否则翻面摸成本张数。 | CHOOSE_CARDS, CHOOSE_PLAYER, CHOOSE_CARD | 基本/锦囊/装备三类延时属锦囊；三类全弃对方无法响应；御策无来源不回复；伤害濒死先救 |
| 满宠/yuce | B | CATEGORY, VISIBILITY, SEQUENCE | 伤后可展示手牌1；有来源才请求来源弃一不同大类型手牌，否则受伤者回复1。 | YES_NO, CHOOSE_CARD | 基本/锦囊/装备三类延时属锦囊；三类全弃对方无法响应；御策无来源不回复；伤害濒死先救 |
| 关平/longyin | B | COUNTER, REACTION | PLAY合法使用杀时可付一牌，撤销本杀quota计入一次，红色则摸1；多角色发动不重复扣quota。 | YES_NO, CHOOSE_CARD | 火雷颜色；先合法用杀后龙吟不能先突破额度；一次杀多目标只触发一次；多关平叠次数不可负 |
| 简雍/qiaoshui | B | PINDIAN, TARGET, SCOPE | PLAY开始拼点；胜利下一张基本/非延时锦囊可加一目标（忽略距离）/原有≥2减一；失败禁锦囊到回合末。 | YES_NO, CHOOSE_PLAYER, CHOOSE_CARD, CHOOSE_OPTION | 平局没赢；延时锦囊失败禁用；单目标不能减为0；无距离但保留其他限制；借刀成对目标；牌已被取 |
| 简雍/zongshi_jianyong | B | PINDIAN, MOVE | 纵适，拼点胜取对方牌，未胜取自己牌；需拼点揭示结果/弃置前取得窗口，不能等牌被他人获得再取。 | YES_NO | 平局没赢；延时锦囊失败禁用；单目标不能减为0；无距离但保留其他限制；借刀成对目标；牌已被取 |
| 刘封/xiansi | B | PILE, AUTHUSE, VISIBILITY | 准备阶段从1-2角色各取1手/装备牌置公开逆；其他人合法用杀窗口可消耗两逆视为对拥有者用普通杀且计次数。 | YES_NO, CHOOSE_PLAYERS, CHOOSE_OPTION, USE_CARD | 可取自己按候选文本；手牌背面选择；两个逆不足无选项；杀范围与享乐/距离；移区触发；主人死清理 |
| 潘璋马忠/duodao | A（基础动作/事件直接组合；动态ownership仍需C） | MOVE, REACTION | 杀伤后付一牌获得来源装备区武器（仍在该位置）；无来源/武器先不提供无意义发动。 | YES_NO, CHOOSE_CARD | 虚拟杀；无来源/无武器；暗箭方向不能写反；武器变化重算；铁索继发不再增伤 |
| 潘璋马忠/anjian | A（基础动作/事件直接组合；动态ownership仍需C） | TARGET | 杀对目标伤害计算时source不在target攻击范围内则+1；继发铁索伤害不重新触发目标规则。 | 自动 | 虚拟杀；无来源/无武器；暗箭方向不能写反；武器变化重算；铁索继发不再增伤 |
| 虞翻/zongxuan | B | MOVE, ORDER | 自己的弃置批次中仍在弃牌堆的牌可非空排序置顶，服务端保存ordered_card_ids与批次锁。 | YES_NO, CHOOSE_CARDS, CHOOSE_OPTION | 已被落英获得不再置顶；选择顺序定义；直言装备槽替换触发；回合外装备使用；用前死亡 |
| 虞翻/zhiyan | B | AUTHUSE, REACTION | 结束阶段选角色摸1并公开该牌；若装备先恢复1再由该角色回合外使用该实体装备，合法槽规则照常。 | YES_NO, CHOOSE_PLAYER, USE_CARD | 已被落英获得不再置顶；选择顺序定义；直言装备槽替换触发；回合外装备使用；用前死亡 |
| 朱然/danshou | B | CATEGORY, COUNTER, SEQUENCE | PLAY第k次发动付k牌并选范围内目标；k=1弃其1，2交给你1，3伤1，≥4双方摸2；成功付费再递增。 | CHOOSE_CARDS, CHOOSE_PLAYER, CHOOSE_OPTION | X=1/2/3/4/5；攻击范围；新阶段重置；先成本再分支；不是死亡触发；无足牌不能发动 |
| 伏皇后/zhuikong | B | PINDIAN, TARGET, SCOPE | 其他人回合开始自己受伤可拼点；赢绑定target本回合只能以自己为角色目标；没赢target至自己的距离忽略。 | YES_NO, CHOOSE_CARD | 非跳阶段版本；无手不能拼；平局方向距离；追加不得重复；无手可选求援；闪给牌非打出闪 |
| 伏皇后/qiuyuan | B | TARGET, SEQUENCE | 被杀指定后选除杀使用者与自己外的其他人，其给闪则只转移实体牌，否则也加为杀目标；去重循环保护。 | YES_NO, CHOOSE_PLAYER, CHOOSE_CARD | 非跳阶段版本；无手不能拼；平局方向距离；追加不得重复；无手可选求援；闪给牌非打出闪 |
| 李儒/juece | A（基础动作/事件直接组合；动态ownership仍需C） | REACTION | FINISH开始选无手牌角色伤1；不是失去最后手牌即时触发候选。 | YES_NO, CHOOSE_PLAYER | 灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1 |
| 李儒/mieji | B | CATEGORY, ORDER | 一次PLAY将黑色锦囊手牌置顶，选有手牌他人；其弃1锦囊或2非锦囊，用约束choice不能混搭。 | CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_CARDS | 灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1 |
| 李儒/fencheng | B | SEQUENCE | 限定PLAY，其他存活人席位序；首人X=1，每人弃≥X或2火伤；下一阈值为上人实际弃数+1，伤害分支令下人X=1。 | YES_NO, CHOOSE_CARDS | 灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1 |
| 神刘备/longnu | C | VIEWAS, CONVERT, SCOPE, MAXHP | PLAY开始强制当前转换状态费用与摸1；阴红色手牌视火杀不限距离，阳锦囊视雷杀不限次数，phase末撤销，状态持久交替。 | 自动 | 阴阳标签/首态待确认；阴红手火杀不限距离；阳锦囊雷杀不限次数；不是桃转换；解链即重横；多源上限 |
| 神刘备/jieying_liubei | C | AURA | 神刘备结营，自己被重置即重新横置；所有横置角色上限+2为来源绑定光环；FINISH强制横置另一角色。 | CHOOSE_PLAYER | 阴阳标签/首态待确认；阴红手火杀不限距离；阳锦囊雷杀不限次数；不是桃转换；解链即重横；多源上限 |
| 神陆逊/junlve | B | COUNTER, REACTION | 受到或造成实际伤害获得等量标记；若同时两身份均满足分别计入需Q08核对；HP流失不计。 | 自动 | 0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导 |
| 神陆逊/cuike | B | SEQUENCE, REACTION | PLAY开始军略奇数可伤1/偶数可横置角色并弃其区域1；后续军略>7可全移并对其他人伤1，逐个处理新增标记。 | YES_NO, CHOOSE_PLAYER, CHOOSE_OPTION | 0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导 |
| 神陆逊/zhanhuo | B | SEQUENCE, REACTION | 限定PLAY消费全部军略，选至多等量横置角色全弃装备，再选其中一个火伤1；无标记不能形成非空目标。 | YES_NO, CHOOSE_PLAYERS, CHOOSE_PLAYER | 0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导 |
| 神甘宁/poxi | B | VISIBILITY, SUBSET, PHASE | 一次PLAY先建立仅发动者可看目标手牌grant，可取消；选择双方手牌四种不同花色各1一起弃，根据自弃0/1/2/3/4分支。 | CHOOSE_PLAYER, YES_NO, CHOOSE_CARDS | 0/1/2/3/4张自身分支；取消看牌后不弃；其他客户端不能看；营增益后夺手；持营死/神死清理 |
| 神甘宁/jieying_ganning | C | AURA, SCOPE | 神甘宁劫营，营为独立来源persistent effect；没人有营才回合开始自得，FINISH可给其他角色，持者回合末移营后夺其所有手牌。 | YES_NO, CHOOSE_PLAYER | 0/1/2/3/4张自身分支；取消看牌后不弃；其他客户端不能看；营增益后夺手；持营死/神死清理 |
| 神张辽/duorui | C | OWNERSHIP, SLOT | PLAY实际对其他人伤后可废一装备栏并租借其一个合格武将技能，失效作用于指定ownership；目标下回合末/死亡回收；细则Q06。 | YES_NO, CHOOSE_OPTION | 出牌阶段伤害才夺；装备栏费用；目标下回合末/死亡；断肠多原因；化身/极略；拼点决斗胜利事件 |
| 神张辽/zhiti | C | SLOT, AURA, PINDIAN | 范围内已伤他人上限-1；与范围内已伤者拼点/决斗胜或被其伤害后恢复一废栏；决斗胜不能只依据造成任意伤害。 | CHOOSE_OPTION | 出牌阶段伤害才夺；装备栏费用；目标下回合末/死亡；断肠多原因；化身/极略；拼点决斗胜利事件 |

## 公共不变量与测试规划

1. CardInstance只有一个ZoneRef；每个成本/资源只消费一次，虚拟牌不能创造新实体牌。
2. rewrite发生在BeforeDamage/伤害触发以前；绝情不触发新生、军略、伤后卖血和铁索。避免伤害清零后仍播伤害事件。
3. 先付成本再收益，濒死由子栈完成后重检存活、技能有效、实体还在原区；不能用timeout跳过强制效果。
4. 多人序列保留cursor、已处理集合与当前threshold，重连不会从第一个人重来；新的额外阶段phase_token各不相同。
5. 临时状态在所有正常/死亡/游戏结束路径统一清理；不以全局marks.clear()清掉他人或其他来源。
6. 虚拟牌花色/颜色与材料区合法性统一，不能拿物理第一张作为组合牌唯一性质。
7. 模拟每个ask前/后断线、60秒timeout、重复ACK、旧request_id、恶意额外card_id与skill_id，Web/PySide给同一结果。

设计门禁：Q00–Q08未决规则不得自行写代码猜测。测试案例在各roster技能段及catalog.json，不在T17A写实现镜像测试或跑full pytest。

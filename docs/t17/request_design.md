# PendingRequest / Decision设计

现有真正枚举（engine/requests.py）：YES_NO、CHOOSE_OPTION、CHOOSE_PLAYER、CHOOSE_PLAYERS、CHOOSE_CARD、CHOOSE_CARDS、RESPOND_WITH_CARD、USE_CARD。CHOOSE_TARGET、PINDIAN、VIEW_AS、CHOOSE_SKILL、CHOOSE_GENERAL、CHOOSE_ZONE_CARD都不是当前枚举，不得在文档伪称已存在。

复用映射：选角色=CHOOSE_PLAYER(S)；拼点=两次私密CHOOSE_CARD，再同步公开；view-as=CHOOSE_OPTION声明+CHOOSE_CARDS材料+USE_CARD合法目标；技能=CHOOSE_OPTION使用合格ownership token；区域未知牌=CHOOSE_OPTION用hand:opaque_token，不能泄露物理id/顺序/名字；将牌=CHOOSE_OPTION稳定general ID，仅请求拥有者可见化身池。无需新增逐武将枚举。

## 需要扩展的通用能力，优先保持枚举

- selection_constraints：CHOOSE_CARDS的跨所有者、点数和、四异花色、类型组合。服务端白名单/原区快照/谓词共同验证；不能只检查min_count/max_count。
- visibility_grant：按request/frame授权显示他人手牌，choice_labels必须受同一过滤；标签、event、logs、replay均不能绕过授权。
- ordered_selection：先CHOOSE_CARDS确定集合，再逐次CHOOSE_OPTION选下一顶牌顺序，服务端存剩余集。现有枚举足以表达，未来可考虑通用ORDER_CARDS降低交互轮数，T17A不新增它。
- CHOOSE_OPTION的技能候选使用ownership实例句柄，中文label是技能名+来源武将；服务端拒绝任意未列ID，恢复期限公开。
- USE_CARD当前timeout_value没有分支：授权出杀必须通用合法PASS/拒绝导致替代收益；强制回合外装备使用不额外请求可由服务器提交确定目标，但合法性仍验证。RESPOND_WITH_CARD只有允许pass才可pass。
- subset timeout不能取eligible_card_ids[:min_count]：称象可能点数超13，魄袭可能花色重复；穷举确定合法子集或明确合法取消。强制discard必须构造谓词可行集；若无合法集合走技能规定失败分支，不抛出卡死。

## 请求生命周期

服务器建立originating_action_id/frame_id、actor、候选快照、约束、60秒deadline与中文metadata→仅actor收到候选→Decision校验身份/期限/id/候选/原位置/状态→支付成本→ACK已接受→恢复栈。重复ACK/Decision幂等，过期/旧id不能执行；重连保留原deadline和frame，不能凭重连重置60秒。技能目标死亡等使候选变动则服务器修订/撤销请求及合法fallback，客户端不能自行改候选。

## 全技能请求计划

| 武将/技能 | 复用类型 | 具体语义 | 中文choice_labels |
| --- | --- | --- | --- |
| 张春华/jueqing | 无需主动请求 | 伤害正式产生前改为 LoseHpAction，保留原始行动链但不发布伤害事件；禁止铁索复制；无伤害杀手归因需Q08。 | {} |
| 张春华/shangshi | YES_NO | 手牌/HP/maxHP变化后请求补至min(已损HP,2)；一次反应快照后再检测，避免自身摸牌递归。 | {"decline": "放弃发动", "done": "确认选择"} |
| 于禁/yizhong | 无需主动请求 | 被指定可合法；效果阶段黑色杀且无防具则对该角色无效。 | {} |
| 曹植/luoying | YES_NO, CHOOSE_CARDS | 只接受他人牌的弃置与判定弃置批次，逐张重检仍在弃牌堆且有效梅花；对使用/响应弃牌不触发。 | {"decline": "放弃发动", "done": "确认选择"} |
| 曹植/jiushi | CHOOSE_OPTION, YES_NO | 酒的合法窗口翻面虚拟使用；伤害扣HP前记录face_up，结算后只按快照决定翻正。 | {"decline": "放弃发动", "done": "确认选择"} |
| 法正/enyuan | YES_NO, CHOOSE_OPTION, CHOOSE_CARD | 同一获得批次同一他人来源≥2可令其摸1；实际伤害每点要求来源给一手牌或失去HP，来源为空不要求。 | {"give": "交出所选手牌", "lose_hp": "失去1点体力"} |
| 法正/xuanhuo | YES_NO, CHOOSE_PLAYER, USE_CARD, CHOOSE_OPTION | 替代正常摸牌，选受益者摸2，法正选其范围内合法杀目标；受益者USE_CARD，不用则法正依次获得其至多2牌。 | {"decline": "放弃发动", "done": "确认选择"} |
| 马谡/xinzhan | YES_NO, CHOOSE_CARDS, CHOOSE_OPTION | 一次出牌阶段；手牌>maxHP才私看顶3；可拒绝拿红桃，选择非空红桃集则公开获得；剩余排序。 | {"decline": "放弃发动", "done": "确认选择"} |
| 马谡/huilei | 无需主动请求 | 死亡触发，杀手为其他人且有牌则弃其规则范围所有牌；与奖励、行殇优先级须冻结。 | {} |
| 徐庶/wuyan | 无需主动请求 | 在锦囊导致伤害时若来源或目标拥有技能则取消；不取消牌效果本身；南蛮先替换来源再判断。 | {} |
| 徐庶/jujian | YES_NO, CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION | 结束阶段可付一非基本牌成本选其他人，由其选摸2/恢复1/解连环并翻正。 | {"draw": "摸牌", "recover": "回复体力", "reset": "解除连环并翻至正面"} |
| 凌统/xuanfeng | YES_NO, CHOOSE_PLAYER, CHOOSE_OPTION | 装备离区以移动批次一次触发，或弃牌阶段结束满足≥2；两次区域弃置可相同角色，逐次校验。 | {"decline": "放弃发动", "done": "确认选择"} |
| 徐盛/pojun | YES_NO | 杀伤后角色存活时选发动，X=max(0,min(当前HP,5))，摸X再翻面；濒死结算完成后判断。 | {"decline": "放弃发动", "done": "确认选择"} |
| 吴国太/ganlu | CHOOSE_PLAYERS | 两角色装备数差绝对值≤已损HP；快照所有槽、统一验证、原子交换再发布整批移动及离装反应。 | {"decline": "放弃发动", "done": "确认选择"} |
| 吴国太/buyi | YES_NO, CHOOSE_OPTION | 濒死者手牌背面选1后公开；非基本则弃该牌恢复1；基本仅展示；死亡决定之前处理。 | {"decline": "放弃发动", "done": "确认选择"} |
| 陈宫/mingce | CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION | 一次出牌阶段给装备或杀，陈宫选合法杀目标，受益者选择视为杀/摸1；不存在目标仅摸1。 | {"use_slash": "按授权使用杀", "draw": "摸牌"} |
| 陈宫/zhichi | 无需主动请求 | 回合外伤后建立当前turn_token内杀和非延时锦囊对本人的效果无效；不撤销首个伤害；回合末统一清理。 | {} |
| 高顺/xianzhen | CHOOSE_PLAYER, CHOOSE_CARD | 一次出牌阶段拼点；胜则以source,target,turn_token绑定杀次数豁免/距离忽略/防具无效，没赢绑定全局禁用杀。 | {"decline": "放弃发动", "done": "确认选择"} |
| 高顺/jinjiu | 无需主动请求 | 强制酒身份替换为普通杀，不提供酒自救；虚拟酒及装备区材料解释待语义核对。 | {} |
| 荀攸/qice | CHOOSE_OPTION, CHOOSE_PLAYERS | 成本为使用提交时全部非空手牌；选非延时锦囊definition及合法目标；整组VirtualCard保留材料列表并按普通牌结算。 | {"decline": "放弃发动", "done": "确认选择"} |
| 荀攸/zhiyu | YES_NO, CHOOSE_CARD | 伤后可摸1并公开当前全部手牌；非空且颜色全同令存活来源弃手牌1；公开展示不永久开启观察权。 | {"decline": "放弃发动", "done": "确认选择"} |
| 王异/zhenlie | YES_NO, CHOOSE_OPTION | 杀/非延时锦囊被指定后可失去1HP；完成濒死后若仍存活则弃来源牌并令该牌对自己无效；Q08裁顺序。 | {"decline": "放弃发动", "done": "确认选择"} |
| 王异/miji | YES_NO, CHOOSE_OPTION, CHOOSE_CARDS, CHOOSE_PLAYER | 结束阶段受伤可选n∈[0,已损HP]摸n，随后从当前手牌分配实际获得数量给其他人；每张一次归属。 | {"decline": "放弃发动", "done": "确认选择"} |
| 曹彰/jiangchi | CHOOSE_OPTION | 摸牌数修改并加turn-scoped限制；多摸禁止use与respond所有杀，少摸+1次数且不限距离；默认不修改。 | {"default": "正常摸牌", "jiang": "多摸一张，本回合不能使用或打出杀", "chi": "少摸一张，本回合杀不限距离且次数加一"} |
| 钟会/quanji | YES_NO, CHOOSE_CARD | 受到每1点伤害可摸1并从当前手牌置1权；特殊牌区权可见性需Q07；持权数增加手牌上限。 | {"decline": "放弃发动", "done": "确认选择"} |
| 钟会/zili | CHOOSE_OPTION | 准备阶段权≥3且未觉醒：减maxHP1，选择摸2/回HP1，然后授予排异来源zili；不得预先拥有排异。 | {"draw": "摸牌", "recover": "回复体力"} |
| 钟会/paiyi | CHOOSE_CARD, CHOOSE_PLAYER | 仅自立授予后，每出牌阶段1次弃1权，目标摸2后若手牌>自己的手牌，对其伤害1；可选自己。 | {"decline": "放弃发动", "done": "确认选择"} |
| 廖化/dangxian | 无需主动请求 | 回合开始插入PLAY阶段，独立phase_token，后续正常PLAY使用次数独立；背面跳回合顺序Q08。 | {} |
| 廖化/fuli | YES_NO | 限定濒死可回复到min(存活有效势力种数,maxHP)，然后翻面；不是额外回合；失败救起继续濒死。 | {"decline": "放弃发动", "done": "确认选择"} |
| 关兴张苞/fuhun | CHOOSE_CARDS, USE_CARD, RESPOND_WITH_CARD | 两手牌普通杀ViewAs；该牌于PLAY造成实际伤害后授予wusheng,paoxiao到回合末，按来源回收。 | {"decline": "放弃发动", "done": "确认选择"} |
| 马岱/mashu | 无需主动请求 | 语义复用已存在mashu，但当前distance.py直接查角色原生技能；动态获得/失效须接统一ownership。 | {} |
| 马岱/qianxi | YES_NO, CHOOSE_PLAYER | 准备阶段判定，选有效距离1角色；本回合按判定最终颜色禁止其手牌使用/打出，逐材料按区域检查。 | {"decline": "放弃发动", "done": "确认选择"} |
| 步练师/anxu | CHOOSE_PLAYERS, CHOOSE_OPTION | 一次出牌阶段选两其他人手牌不同，少者选多者背面手牌公开获得，非黑桃步练师摸1。 | {"decline": "放弃发动", "done": "确认选择"} |
| 步练师/zhuiyi | YES_NO, CHOOSE_PLAYER | 死亡后允许该技能专用最后选择，目标其他存活者排除杀手，摸3再恢复1；无来源死亡不排除。 | {"decline": "放弃发动", "done": "确认选择"} |
| 程普/lihuo | CHOOSE_OPTION, CHOOSE_PLAYER | 普通杀可转火；所有火杀可增一个目标；只转换杀造成过伤害则整牌结算结束扣HP1一次。 | {"decline": "放弃发动", "done": "确认选择"} |
| 程普/chunlao | YES_NO, CHOOSE_CARDS, CHOOSE_CARD | 结束阶段没有醇时可存至少一杀；濒死时消耗一醇视为濒死者用酒，通过标准酒自救与濒死管线。 | {"decline": "放弃发动", "done": "确认选择"} |
| 韩当/gongqi | CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION | 一次出牌阶段弃任意一牌，本回合攻击范围无限，若装备可再弃其他人牌1；不改通用距离。 | {"decline": "放弃发动", "done": "确认选择"} |
| 韩当/jiefan | CHOOSE_PLAYER, CHOOSE_CARD | 限定PLAY选角色；按当前席位序依次询问攻击范围含目标者，弃一武器（手或装备）否则目标摸1。 | {"decline": "放弃发动", "done": "确认选择"} |
| 刘表/zishou | YES_NO | 受伤摸牌阶段可增已损HP摸牌，并skip_play；非按势力数候选，禁止拼接新版。 | {"decline": "放弃发动", "done": "确认选择"} |
| 刘表/zongshi | 无需主动请求 | 锁定手牌上限+存活有效势力种数，化身势力经SkillRegistry.faction；神当前映射群不自加新势力。 | {} |
| 华雄/shiyong | 无需主动请求 | 实际红色杀或带wine标签杀伤后maxHP-1，每次伤害一次；红且酒不重复。 | {} |
| 曹冲/chengxiang | YES_NO, CHOOSE_CARDS | 伤后公开顶4，选择非空子集且rank总和≤13；选中获得余牌弃置，服务端计算不是仅计数检查。 | {"decline": "放弃发动", "done": "确认选择"} |
| 曹冲/renxin | YES_NO, CHOOSE_CARD | 别人HP恰为1伤前可翻面、弃装备牌防整次伤害；费用可来自手或装备，所有移动副作用正常触发。 | {"decline": "放弃发动", "done": "确认选择"} |
| 郭淮/jingce | YES_NO | 每次PLAY结束时统计当前turn_token CardUsedEvent数量≥当前HP则可摸2；response不计，虚拟材料不多计。 | {"decline": "放弃发动", "done": "确认选择"} |
| 满宠/junxing | CHOOSE_CARDS, CHOOSE_PLAYER, CHOOSE_CARD | 一次PLAY至少1手牌弃置，按三大类型集计算补集，对方弃该补集类型手牌1，否则翻面摸成本张数。 | {"decline": "放弃发动", "done": "确认选择"} |
| 满宠/yuce | YES_NO, CHOOSE_CARD | 伤后可展示手牌1；有来源才请求来源弃一不同大类型手牌，否则受伤者回复1。 | {"decline": "放弃发动", "done": "确认选择"} |
| 关平/longyin | YES_NO, CHOOSE_CARD | PLAY合法使用杀时可付一牌，撤销本杀quota计入一次，红色则摸1；多角色发动不重复扣quota。 | {"decline": "放弃发动", "done": "确认选择"} |
| 简雍/qiaoshui | YES_NO, CHOOSE_PLAYER, CHOOSE_CARD, CHOOSE_OPTION | PLAY开始拼点；胜利下一张基本/非延时锦囊可加一目标（忽略距离）/原有≥2减一；失败禁锦囊到回合末。 | {"add": "增加一名目标", "remove": "减少一名目标", "keep": "保留原目标"} |
| 简雍/zongshi_jianyong | YES_NO | 纵适，拼点胜取对方牌，未胜取自己牌；需拼点揭示结果/弃置前取得窗口，不能等牌被他人获得再取。 | {"decline": "放弃发动", "done": "确认选择"} |
| 刘封/xiansi | YES_NO, CHOOSE_PLAYERS, CHOOSE_OPTION, USE_CARD | 准备阶段从1-2角色各取1手/装备牌置公开逆；其他人合法用杀窗口可消耗两逆视为对拥有者用普通杀且计次数。 | {"decline": "放弃发动", "done": "确认选择"} |
| 潘璋马忠/duodao | YES_NO, CHOOSE_CARD | 杀伤后付一牌获得来源装备区武器（仍在该位置）；无来源/武器先不提供无意义发动。 | {"decline": "放弃发动", "done": "确认选择"} |
| 潘璋马忠/anjian | 无需主动请求 | 杀对目标伤害计算时source不在target攻击范围内则+1；继发铁索伤害不重新触发目标规则。 | {} |
| 虞翻/zongxuan | YES_NO, CHOOSE_CARDS, CHOOSE_OPTION | 自己的弃置批次中仍在弃牌堆的牌可非空排序置顶，服务端保存ordered_card_ids与批次锁。 | {"decline": "放弃发动", "done": "确认选择"} |
| 虞翻/zhiyan | YES_NO, CHOOSE_PLAYER, USE_CARD | 结束阶段选角色摸1并公开该牌；若装备先恢复1再由该角色回合外使用该实体装备，合法槽规则照常。 | {"decline": "放弃发动", "done": "确认选择"} |
| 朱然/danshou | CHOOSE_CARDS, CHOOSE_PLAYER, CHOOSE_OPTION | PLAY第k次发动付k牌并选范围内目标；k=1弃其1，2交给你1，3伤1，≥4双方摸2；成功付费再递增。 | {"decline": "放弃发动", "done": "确认选择"} |
| 伏皇后/zhuikong | YES_NO, CHOOSE_CARD | 其他人回合开始自己受伤可拼点；赢绑定target本回合只能以自己为角色目标；没赢target至自己的距离忽略。 | {"decline": "放弃发动", "done": "确认选择"} |
| 伏皇后/qiuyuan | YES_NO, CHOOSE_PLAYER, CHOOSE_CARD | 被杀指定后选除杀使用者与自己外的其他人，其给闪则只转移实体牌，否则也加为杀目标；去重循环保护。 | {"decline": "放弃发动", "done": "确认选择"} |
| 李儒/juece | YES_NO, CHOOSE_PLAYER | FINISH开始选无手牌角色伤1；不是失去最后手牌即时触发候选。 | {"decline": "放弃发动", "done": "确认选择"} |
| 李儒/mieji | CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_CARDS | 一次PLAY将黑色锦囊手牌置顶，选有手牌他人；其弃1锦囊或2非锦囊，用约束choice不能混搭。 | {"discard_trick": "弃置一张锦囊牌", "discard_two_nontricks": "弃置两张非锦囊牌"} |
| 李儒/fencheng | YES_NO, CHOOSE_CARDS | 限定PLAY，其他存活人席位序；首人X=1，每人弃≥X或2火伤；下一阈值为上人实际弃数+1，伤害分支令下人X=1。 | {"done": "确认选择", "take_fire_damage": "受到2点火焰伤害"} |
| 神刘备/longnu | 无需主动请求 | PLAY开始强制当前转换状态费用与摸1；阴红色手牌视火杀不限距离，阳锦囊视雷杀不限次数，phase末撤销，状态持久交替。 | {} |
| 神刘备/jieying_liubei | CHOOSE_PLAYER | 神刘备结营，自己被重置即重新横置；所有横置角色上限+2为来源绑定光环；FINISH强制横置另一角色。 | {"decline": "放弃发动", "done": "确认选择"} |
| 神陆逊/junlve | 无需主动请求 | 受到或造成实际伤害获得等量标记；若同时两身份均满足分别计入需Q08核对；HP流失不计。 | {} |
| 神陆逊/cuike | YES_NO, CHOOSE_PLAYER, CHOOSE_OPTION | PLAY开始军略奇数可伤1/偶数可横置角色并弃其区域1；后续军略>7可全移并对其他人伤1，逐个处理新增标记。 | {"decline": "放弃发动", "done": "确认选择"} |
| 神陆逊/zhanhuo | YES_NO, CHOOSE_PLAYERS, CHOOSE_PLAYER | 限定PLAY消费全部军略，选至多等量横置角色全弃装备，再选其中一个火伤1；无标记不能形成非空目标。 | {"decline": "放弃发动", "done": "确认选择"} |
| 神甘宁/poxi | CHOOSE_PLAYER, YES_NO, CHOOSE_CARDS | 一次PLAY先建立仅发动者可看目标手牌grant，可取消；选择双方手牌四种不同花色各1一起弃，根据自弃0/1/2/3/4分支。 | {"done": "确认选择", "cancel_selection": "结束选牌"} |
| 神甘宁/jieying_ganning | YES_NO, CHOOSE_PLAYER | 神甘宁劫营，营为独立来源persistent effect；没人有营才回合开始自得，FINISH可给其他角色，持者回合末移营后夺其所有手牌。 | {"decline": "放弃发动", "done": "确认选择"} |
| 神张辽/duorui | YES_NO, CHOOSE_OPTION | PLAY实际对其他人伤后可废一装备栏并租借其一个合格武将技能，失效作用于指定ownership；目标下回合末/死亡回收；细则Q06。 | {"slot_weapon": "废除武器栏", "slot_armor": "废除防具栏", "slot_offensive_horse": "废除进攻坐骑栏", "slot_defensive_horse": "废除防御坐骑栏"} |
| 神张辽/zhiti | CHOOSE_OPTION | 范围内已伤他人上限-1；与范围内已伤者拼点/决斗胜或被其伤害后恢复一废栏；决斗胜不能只依据造成任意伤害。 | {"decline": "放弃发动", "done": "确认选择"} |

所有技能名称、完整中文tooltip、版本、状态已在catalog.json定义；候选技能在UI metadata加“版本待确认”。动态候选牌名/玩家名/技能来源按观众权限生成，不能从固定共享label字典包含隐藏牌名。现行choice_labels.py屏蔽他人特殊区/手牌，魄袭扩展时须精确授权，不改为全部可见。

# Multiplayer / Projection审计

authoritative服务器是唯一规则与牌区状态源。仅设计，不改Web/PySide或协议。NONE表示本技能不新增隐藏信息，仍须ACK/重连基础测试；LOW为公开状态；MEDIUM为多步牌/公开后转移；HIGH为私看/特殊区/ownership/连续强制选择。

## 逐将风险矩阵

| 武将 | Projection Risk | Multiplayer Risk | 关键状态 | 验收 |
| --- | --- | --- | --- | --- |
| [张春华](roster.md#yj2011_zhang_chunhua) | LOW | LOW | 伤害改失去体力绕过卖血与铁索传导；伤逝防递归补牌 | 火杀连环不传导；失去体力无伤害触发；上限变化；伤逝上限2/不封顶；逐request重连/timeout/ACK |
| [于禁](roster.md#yj2011_yu_jin) | NONE | LOW | 空防具黑杀免疫；防具存在时正常结算 | 黑杀/红杀/虚拟无色杀；防具被移走；无效非不能指定；逐request重连/timeout/ACK |
| [曹植](roster.md#yj2011_cao_zhi) | MEDIUM | MEDIUM | 落英限他人弃置/判定；酒诗记录受伤前朝向 | 使用材料不落英；已被获得不可再取；濒死酒诗；翻面跳回合；多点伤害一次翻面；逐request重连/timeout/ACK |
| [法正](roster.md#yj2011_fa_zheng) | HIGH | HIGH | 恩怨按单次获得两张/每点伤害；眩惑由法正选杀目标 | 混合来源不合并恩；两点伤害两次怨；无来源；杀不可用转获得两牌；死亡中止；逐request重连/timeout/ACK |
| [马谡](roster.md#yj2011_ma_su) | HIGH | HIGH | 心战私看三牌、公开红桃、余牌排序；挥泪死亡惩罚 | 手牌=上限不能发动；红桃0/1/3；顶牌顺序；无来源死亡；挥泪与反贼奖励顺序；逐request重连/timeout/ACK |
| [徐庶](roster.md#yj2011_xu_shu) | LOW | LOW | 无言只防锦囊伤害；举荐末阶段非基本牌成本 | 顺手/无中照常；南蛮来源替换；延时锦囊伤害；重置含解连环与翻正；无伤不可回复；逐request重连/timeout/ACK |
| [凌统](roster.md#yj2011_ling_tong) | MEDIUM | LOW | 装备离区整批触发；弃牌阶段至少两牌一次触发 | 换装/甘露/死亡离区；同人两牌逐次合法；不足两牌；成本弃置与规则弃置范围核对；逐request重连/timeout/ACK |
| [徐盛](roster.md#yj2011_xu_sheng) | LOW | LOW | 破军按伤害后当前体力摸至多5再翻面 | 濒死救回后HP；X=0；伤害多点一次；原版不扣牌不增伤；逐request重连/timeout/ACK |
| [吴国太](roster.md#yj2011_wu_guotai) | HIGH | HIGH | 甘露全装备交换非逐槽覆盖；补益濒死看一张未知手牌 | 双方同槽武器/空槽/白银狮子/枭姬旋风；差值边界；基本牌不救；反复濒死；逐request重连/timeout/ACK |
| [陈宫](roster.md#yj2011_chen_gong) | MEDIUM | MEDIUM | 明策真实给牌后授权视为杀或摸牌；智迟持续到当前回合末 | 杀目标从受赠者计算范围；回合外受伤免后续锦囊；首伤不被自身取消；额外回合清理；逐request重连/timeout/ACK |
| [高顺](roster.md#yj2011_gao_shun) | MEDIUM | MEDIUM | 陷阵胜利只对拼点对手解除距离杀次数防具；失败全回合禁杀 | 平局为没赢；对其他人次数正常；仅杀次数；禁酒含自救酒；虚拟酒材料；回合清理；逐request重连/timeout/ACK |
| [荀攸](roster.md#yj2012_xun_you) | HIGH | HIGH | 奇策全部手牌视为非延时锦囊；智愚公开整个手牌 | 手牌0不可奇策；多材料颜色；南蛮/借刀/铁索目标；无懈响应；智愚摸后颜色；无来源；逐request重连/timeout/ACK |
| [王异](roster.md#yj2012_wang_yi) | HIGH | HIGH | 贞烈失去体力后目标无效与弃牌；秘计摸至多已损HP再分等量 | 成本濒死/死亡后剩余效果；延时锦囊不可贞烈；秘计分多角色；混旧手牌；不足牌堆；逐request重连/timeout/ACK |
| [曹彰](roster.md#yj2012_cao_zhang) | LOW | LOW | 将驰摸牌阶段三选默认/少摸/多摸；多摸禁使用和打出杀 | 少摸为0；杀响应决斗也禁；雷火虚拟杀；额外阶段同回合；结束清理；逐request重连/timeout/ACK |
| [钟会](roster.md#yj2012_zhong_hui) | HIGH | HIGH | 权计每点伤害摸一存权；自立觉醒获得排异 | 两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己；逐request重连/timeout/ACK |
| [廖化](roster.md#yj2012_liao_hua) | LOW | MEDIUM | 当先额外出牌阶段独立阶段次数；伏枥回复到存活势力数并翻面 | 背面回合是否当先候选待卡面裁定；两次出牌计数隔离；势力随化身变化；神按现行群；逐request重连/timeout/ACK |
| [关兴张苞](roster.md#yj2012_guan_xing_zhang_bao) | MEDIUM | HIGH | 父魂两手牌普通杀；出牌阶段造成伤害获武圣咆哮到回合末 | 非出牌阶段不获；伤害被防不获；一阶段多次幂等；已有武圣不误移除；临时来源不夺；逐request重连/timeout/ACK |
| [马岱](roster.md#yj2012_ma_dai) | MEDIUM | LOW | 马术复用；潜袭判定后距离1颜色手牌使用/打出封锁 | 只封手牌不封装备材料；有效颜色红颜；虚拟材料来源；判定改判；回合末解除；不减上限；逐request重连/timeout/ACK |
| [步练师](roster.md#yj2012_bu_lianshi) | HIGH | HIGH | 安恤少牌者选多牌者未知手牌并公开获得；追忆排除杀手 | 同手牌数不可；不选自己；黑桃不摸；选择者不是步练师；死亡补益；无杀手不排除；逐request重连/timeout/ACK |
| [程普](roster.md#yj2012_cheng_pu) | MEDIUM | MEDIUM | 疠火普通转火、多目标；一次杀有伤害后失去1HP；醇作濒死者酒 | 铁索连伤只扣一次；原生火杀不扣HP；醇为空才补；多次救援；完杀；移去醇不是手牌酒；逐request重连/timeout/ACK |
| [韩当](roster.md#yj2012_han_dang) | MEDIUM | MEDIUM | 弓骑弃牌换无限范围；装备额外弃牌；解烦一次范围内依次弃武器或摸牌 | 攻击范围非距离；武器可来自手/装备；每次选择后重检存活；无武器摸；限定不可重复；逐request重连/timeout/ACK |
| [刘表](roster.md#yj2012_liu_biao) | LOW | LOW | 采用候选受伤额外摸已损HP并跳出牌；宗室按势力上限 | 满HP不自守；势力种数不是人数；神映射群；化身切换影响；不同原版修订另列；逐request重连/timeout/ACK |
| [华雄](roster.md#yj2012_hua_xiong) | LOW | LOW | 红杀或酒杀伤害后减上限一次，不叠两次 | 红酒杀仅一次；黑酒杀一次；多点仅一次；上限0死亡；无体力流失触发；逐request重连/timeout/ACK |
| [曹冲](roster.md#yj2013_cao_chong) | MEDIUM | MEDIUM | 称象四张总点数≤13非空子集；仁心HP1其他人伤前翻面弃装备防伤 | 和=13允许14拒绝；装备在手或装备区；成本翻面顺序；零装备；多点伤害整体防止；逐request重连/timeout/ACK |
| [郭淮](roster.md#yj2013_guo_huai) | LOW | LOW | 出牌阶段结束比较本回合使用牌数与当前HP，摸2 | 打出不算使用；虚拟牌算一张；当先使用纳入回合；HP变化；不是结束阶段摸；逐request重连/timeout/ACK |
| [满宠](roster.md#yj2013_man_chong) | HIGH | HIGH | 峻刑多牌类型补集；御策公开一牌来源弃异类型否则回复 | 基本/锦囊/装备三类延时属锦囊；三类全弃对方无法响应；御策无来源不回复；伤害濒死先救；逐request重连/timeout/ACK |
| [关平](roster.md#yj2013_guan_ping) | LOW | LOW | 任意角色出牌用杀时弃一牌使本杀不计次数，红杀摸1 | 火雷颜色；先合法用杀后龙吟不能先突破额度；一次杀多目标只触发一次；多关平叠次数不可负；逐request重连/timeout/ACK |
| [简雍](roster.md#yj2013_jian_yong) | HIGH | HIGH | 巧说胜下一张基本/非延时锦囊加减目标；纵适获拼点牌 | 平局没赢；延时锦囊失败禁用；单目标不能减为0；无距离但保留其他限制；借刀成对目标；牌已被取；逐request重连/timeout/ACK |
| [刘封](roster.md#yj2013_liu_feng) | HIGH | HIGH | 陷嗣1-2人各一牌公开逆；别人花两逆视为对刘封杀计次数 | 可取自己按候选文本；手牌背面选择；两个逆不足无选项；杀范围与享乐/距离；移区触发；主人死清理；逐request重连/timeout/ACK |
| [潘璋马忠](roster.md#yj2013_pan_zhang_ma_zhong) | MEDIUM | LOW | 夺刀受杀伤后弃牌获来源武器；暗箭按对方范围算伤害+1 | 虚拟杀；无来源/无武器；暗箭方向不能写反；武器变化重算；铁索继发不再增伤；逐request重连/timeout/ACK |
| [虞翻](roster.md#yj2013_yu_fan) | HIGH | HIGH | 纵玄弃置牌重排顶；直言摸后公开装备回复并使用 | 已被落英获得不再置顶；选择顺序定义；直言装备槽替换触发；回合外装备使用；用前死亡；逐request重连/timeout/ACK |
| [朱然](roster.md#yj2013_zhu_ran) | MEDIUM | MEDIUM | 选择阶梯弃牌胆守，不采用结束一切结算原版 | X=1/2/3/4/5；攻击范围；新阶段重置；先成本再分支；不是死亡触发；无足牌不能发动；逐request重连/timeout/ACK |
| [伏皇后](roster.md#yj2013_fu_huanghou) | HIGH | HIGH | 惴恐赢限制他人目标；求援交闪否则追加目标 | 非跳阶段版本；无手不能拼；平局方向距离；追加不得重复；无手可选求援；闪给牌非打出闪；逐request重连/timeout/ACK |
| [李儒](roster.md#yj2013_li_ru) | HIGH | HIGH | 绝策末阶段空手伤害；灭计黑锦囊顶牌；焚城递增弃牌或2火伤 | 灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1；逐request重连/timeout/ACK |
| [神刘备](roster.md#shadow_god_liubei) | MEDIUM | HIGH | 龙怒两个状态按出牌阶段切换；结营强制横置与共享上限 | 阴阳标签/首态待确认；阴红手火杀不限距离；阳锦囊雷杀不限次数；不是桃转换；解链即重横；多源上限；逐request重连/timeout/ACK |
| [神陆逊](roster.md#shadow_god_luxun) | MEDIUM | MEDIUM | 军略按伤害点累积；摧克奇偶/超过7清标群伤；绽火限一次 | 0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导；逐request重连/timeout/ACK |
| [神甘宁](roster.md#thunder_god_ganning) | HIGH | HIGH | 初始HP3上限6候选；魄袭私看并选双方4异花色；劫营营所有权 | 0/1/2/3/4张自身分支；取消看牌后不弃；其他客户端不能看；营增益后夺手；持营死/神死清理；逐request重连/timeout/ACK |
| [神张辽](roster.md#thunder_god_zhangliao) | HIGH | HIGH | 夺锐临时借技能与独立失效；止啼受伤范围上限减1并恢复栏 | 出牌阶段伤害才夺；装备栏费用；目标下回合末/死亡；断肠多原因；化身/极略；拼点决斗胜利事件；逐request重连/timeout/ACK |

## 神甘宁魄袭：HIGH

服务器自己的完整状态不可直接广播。选择目标之前任何客户端（包括神甘宁）只有对方手牌张数；选定后创建(frame_id, viewer=神甘宁, subject=目标, exact current card ids)临时grant，仅神甘宁可见目标牌名花色点数/可选牌。目标只见自己的牌；其余角色与旁观者仍只有张数。选取不提前广播；正式弃置完成才公开四牌，其他结果仅公开合法HP/上限/阶段/数量变化。自弃2张没有附加效果，不漏分支。

取消/完成/死亡/frame退出时撤销grant；结束后重连也不得恢复旧手牌视图。request期间神甘宁重连恢复现存grant，不向其他人推送。物理id、choice_labels、eligible_card_ids、rejected-decision错误、事件记录与回放也受观众过滤；不要仅隐藏牌图。手牌变化时重建候选并校验材料原区；client提交没看见的牌也不能扩展权限。AI只在同样grant内看到对方牌，不读服务器全部state。营夺手牌只公开转移张数，具体牌仅新旧所有者按实际持有权限可见。

## 其他重点

- 马谡心战私看顶3、公开选中的红桃；剩余顺序不向其他玩家展示。虞翻纵玄处理已公开弃牌，但不泄露随后牌堆未公开内容；直言摸到一牌在技能公开节点前不能公开。
- 荀攸智愚有显式公开全部手牌节点，不把“展示”变永久观看；王异秘计分牌、法正恩怨给牌、陈宫给牌不自动公开所有旧手牌。
- 吴国太补益：选濒死者未知手牌用opaque token，选完才公开；步练师安恤选牌者是少牌者，只在选后公开获得牌。
- 钟会权区：存储原语复用；公开数量、owner内容、其他人内容Q07待决定。当前projection.py除star和committed外默认公开，不能直接挂权的新key而泄露。
- 刘封逆通常是公开存牌；取对手手牌阶段仍背面选择。程普醇为公开存牌候选，不展示其未选择存入的杀。
- 拼点是顺序两私密request，不是同时发消息给两人：第一张不在第二人选择前公开；reconnect/timeout也不能提前泄漏。
- 神张辽夺锐可选技能来自已公开武将所有权，禁止读取左慈化身池；只公开被夺技能名/来源/到期，不公开临时候选池或隐藏武将。
- 求援、解烦、焚城、眩惑都是sequential response；不设计simultaneous choices。进度公开但下一人候选只给下一人；上一人拒绝/死亡后的阈值更新由服务器做。

## 最小观众回归组

对每个HIGH技能用发动者、目标、其他在场者、旁观者、重连者五种snapshot检查：private手牌/name/id/suit/rank、private候选池、秘密Decision、临时grant、events/日志/labels均不越权。完成前后对比与公共状态对齐。Web/PySide使用同一Projection；不得为web新建另一套技能规则。

## 全技能信息流检查

风险采用保守的角色上界，具体私有数据/时序以flags与机制定义为准。无simultaneous choices；不是把所有候选广播后等人回复。

| 武将/技能 | Projection Risk | Multiplayer Risk | 信息流/权限 | simultaneous choices |
| --- | --- | --- | --- | --- |
| 张春华/jueqing | LOW | LOW | public_state_only | False |
| 张春华/shangshi | LOW | LOW | public_state_only | False |
| 于禁/yizhong | NONE | LOW | public_state_only | False |
| 曹植/luoying | MEDIUM | MEDIUM | public_discard_selection | False |
| 曹植/jiushi | MEDIUM | MEDIUM | private_response_candidate | False |
| 法正/enyuan | HIGH | HIGH | private_hand, sequential_response | False |
| 法正/xuanhuo | HIGH | HIGH | private_hand, private_candidates, sequential_response | False |
| 马谡/xinzhan | HIGH | HIGH | private_deck_view, private_candidates, temporary_visibility, ordered_choice | False |
| 马谡/huilei | HIGH | HIGH | public_state_only | False |
| 徐庶/wuyan | LOW | LOW | public_state_only | False |
| 徐庶/jujian | LOW | LOW | public_state_only | False |
| 凌统/xuanfeng | MEDIUM | LOW | public_state_only | False |
| 徐盛/pojun | LOW | LOW | public_state_only | False |
| 吴国太/ganlu | HIGH | HIGH | public_zone_exchange | False |
| 吴国太/buyi | HIGH | HIGH | private_hand, opaque_choice, public_reveal_after_choice | False |
| 陈宫/mingce | MEDIUM | MEDIUM | private_hand, sequential_response | False |
| 陈宫/zhichi | MEDIUM | MEDIUM | public_state_only | False |
| 高顺/xianzhen | MEDIUM | MEDIUM | private_hand, secret_choice, sequential_response | False |
| 高顺/jinjiu | MEDIUM | MEDIUM | public_state_only | False |
| 荀攸/qice | HIGH | HIGH | private_hand, private_candidates | False |
| 荀攸/zhiyu | HIGH | HIGH | public_hand_reveal_after_draw | False |
| 王异/zhenlie | HIGH | HIGH | private_hand, opaque_choice | False |
| 王异/miji | HIGH | HIGH | private_hand, private_candidates, sequential_response | False |
| 曹彰/jiangchi | LOW | LOW | public_state_only | False |
| 钟会/quanji | HIGH | HIGH | private_hand, private_candidates, special_pile_visibility_question | False |
| 钟会/zili | HIGH | HIGH | skill_acquisition | False |
| 钟会/paiyi | HIGH | HIGH | special_pile_visibility_question | False |
| 廖化/dangxian | LOW | MEDIUM | public_state_only | False |
| 廖化/fuli | LOW | MEDIUM | public_state_only | False |
| 关兴张苞/fuhun | MEDIUM | HIGH | private_hand, skill_acquisition | False |
| 马岱/mashu | MEDIUM | LOW | public_state_only | False |
| 马岱/qianxi | MEDIUM | LOW | public_state_only | False |
| 步练师/anxu | HIGH | HIGH | private_hand, opaque_choice, public_reveal_after_choice | False |
| 步练师/zhuiyi | HIGH | HIGH | public_state_only | False |
| 程普/lihuo | MEDIUM | MEDIUM | public_state_only | False |
| 程普/chunlao | MEDIUM | MEDIUM | private_hand, private_candidates, public_special_pile | False |
| 韩当/gongqi | MEDIUM | MEDIUM | public_state_only | False |
| 韩当/jiefan | MEDIUM | MEDIUM | private_hand, sequential_response | False |
| 刘表/zishou | LOW | LOW | public_state_only | False |
| 刘表/zongshi | LOW | LOW | public_state_only | False |
| 华雄/shiyong | LOW | LOW | public_state_only | False |
| 曹冲/chengxiang | MEDIUM | MEDIUM | public_reveal, private_selection_before_commit | False |
| 曹冲/renxin | MEDIUM | MEDIUM | private_hand, private_cost_choice | False |
| 郭淮/jingce | LOW | LOW | public_state_only | False |
| 满宠/junxing | HIGH | HIGH | private_hand, private_candidates, sequential_response | False |
| 满宠/yuce | HIGH | HIGH | private_hand, public_reveal, sequential_response | False |
| 关平/longyin | LOW | LOW | public_state_only | False |
| 简雍/qiaoshui | HIGH | HIGH | private_hand, secret_choice, sequential_response | False |
| 简雍/zongshi_jianyong | HIGH | HIGH | public_pindian_cards | False |
| 刘封/xiansi | HIGH | HIGH | private_hand, opaque_choice, public_special_pile, authorized_other_actor | False |
| 潘璋马忠/duodao | MEDIUM | LOW | private_cost_choice, public_equipment | False |
| 潘璋马忠/anjian | MEDIUM | LOW | public_state_only | False |
| 虞翻/zongxuan | HIGH | HIGH | public_discard_selection, ordered_choice | False |
| 虞翻/zhiyan | HIGH | HIGH | public_reveal_after_draw, authorized_other_actor | False |
| 朱然/danshou | MEDIUM | MEDIUM | private_hand, opaque_choice, sequential_response | False |
| 伏皇后/zhuikong | HIGH | HIGH | private_hand, secret_choice, sequential_response | False |
| 伏皇后/qiuyuan | HIGH | HIGH | private_hand, sequential_response | False |
| 李儒/juece | HIGH | HIGH | public_state_only | False |
| 李儒/mieji | HIGH | HIGH | private_hand, private_candidates, sequential_response | False |
| 李儒/fencheng | HIGH | HIGH | private_hand, private_candidates, sequential_response | False |
| 神刘备/longnu | MEDIUM | HIGH | public_state_only | False |
| 神刘备/jieying_liubei | MEDIUM | HIGH | public_state_only | False |
| 神陆逊/junlve | MEDIUM | MEDIUM | public_state_only | False |
| 神陆逊/cuike | MEDIUM | MEDIUM | public_state_only | False |
| 神陆逊/zhanhuo | MEDIUM | MEDIUM | public_state_only | False |
| 神甘宁/poxi | HIGH | HIGH | private_hand, private_candidates, temporary_visibility, private_selection_before_commit | False |
| 神甘宁/jieying_ganning | HIGH | HIGH | private_hand_transfer, persistent_relation | False |
| 神张辽/duorui | HIGH | HIGH | skill_acquisition, private_general_data_excluded, public_skill_candidates, temporary_ownership | False |
| 神张辽/zhiti | HIGH | HIGH | public_skill_state, equipment_slot_state | False |

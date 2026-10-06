# T18A.11 differences

基线573164f；代码修复checkpoint见final_release_audit.md。保留锁定经典版本，未升级现代规则。

| ID | 武将/系统 | 当前基线行为 | 锁定规则/正确行为 | 影响 | 修复测试 | 修复commit |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | 身份局主公误杀忠臣 | 共用死亡清理额外弃判定与特殊牌堆 | 处罚仅所有手牌及装备区牌；死者仍清全部区域 | 非法失去延时牌/权等牌堆 | test_t18a11_release.py penalty False/True | 8f04076 |
| R02 | 神陆逊摧克 | 杀死主公终局后继续询问追加群伤 | 终局不再开启效果窗口；来源死亡亦终止 | seed22011留下未完成请求 | test_t18a11_release.py cuike False/True | 8f04076 |
| R03 | 郭淮精策/阶段结束 | 出牌期间终局后仍进入阶段末精策 | 终局仅清阶段标记及结束事件，不询问新技能 | 随机合法动作留下终局request | test_t18a11_release.py jingce | 8f04076 |
| R04 | 左慈化身死亡清理 | 死亡后pool/active/skill仍存于快照 | 死亡技能完成后清除化身私密状态与临时技能 | 重连残留化身权限 | test_t18a11_huashen.py death | 8f04076 |
| I01 | Web重连座位旋转 | seatId未确认时-1索引造成重复对手节点 | fallback自位和旋转必须用相同合法索引 | 重复面板、React key冲突、移动桌错位 | GamePage.test.tsx never duplicates | 8f04076 |

| R05 | 关羽/左慈取得武圣 | 只允许红色手牌，成本区域写死手牌 | 红色手牌及装备可当杀使用/打出；耗武器/马后的距离重新计算 | 漏合法选择；需防止成本后距离错误 | test_t18a11_wusheng.py 6项 | 8f04076 |
| N01 | Windows Web入口 | Uvicorn0.54强制Proactor，浏览器断连回调WinError10054 | 单worker显式Selector工厂，旧Uvicorn策略兼容；非Windows默认auto | 断连产生未处理运行时异常日志 | test_t18a11_web_runtime.py 3项 + 41浏览器日志 | 8f04076 |

九项真实缺陷已复现并修复；六项规则结算/成本差异、一项死亡状态差异、一项Web交互差异、一项Windows运行时差异。未发现需要升级锁定版本的差异。独立规则审计尚未完成，不能据此声称全部差异仅九项。

化身池补充规则按用户2026-10-06明确决定：103 - 12神 - 本人 = 90，减本局普通将和自己的已有化身。基线独立执行即90/90，没有65/76硬编码池问题。新测试初版213失败含夹具未注入registry，不计入产品缺陷。此次新增显式god元数据、未来registry条目测试，以及基于SkillType/特殊元数据的过滤防护，是规则明确化与防回归，不把合成未来技能用例算成现有规则bug。普通可见锁定技可化身，不套用夺锐禁借名单。

布局：本地将从中央移到右下/底部；手牌12张的桌面截图重新验收。完整装备/判定独立分区与PySide视觉一致性仍未完成总验收，不作为全面布局PASS。

测试夹具修正：既有WebSocket full-game smoke发送客人READY后马上跨另一连接发送START，未等待服务器确认，有时被正确拒绝“all guests must be ready”。现等待客人自身ready广播再START，不修改生产准备门禁。此项不计产品bug。

| R06 | 姜维志继/左慈化身 | 目录展示的派生观星同时被识别为姜维初始拥有及化身可选 | 志继实际授予后姜维才拥有；姜维化身只直接选择挑衅，诸葛亮原生观星仍可选 | 提前发动技能、非法化身获取 | test_t18a11_huashen.py Jiangwei/future derived + 139 真实获取/重连条目 | 8f04076 |

| R07 | 铁索连环/连环重铸 | 重铸记录使用锦囊、触发集智/无谋/极略集智、计入精策并消耗巧说；弃牌原因错误；巧说/潜袭使用限制误禁重铸 | 零目标重铸独立RECAST原因，不产生CardUsed/CardResolved，不计用牌次数，仅公开重铸卡面后摸1；使用/打出限制仍允许重铸，指定目标仍禁止 | 额外摸牌/失血、次数与落英触发错误、漏合法操作 | test_t18a11_recast.py 10项 + 浏览器刷新/卡面/零集智窗口 + GamePage显示重铸 | 8f04076 |

| R08 | 祝融巨象/于吉蛊惑 | 成功蛊惑南蛮收尾直接弃材料，遗漏巨象；实体南蛮先入弃堆再收回 | 经典例外允许蛊惑单张材料；巨象在处理区收尾收取，奇策虚拟南蛮排除 | 漏取得合法材料；产生多余弃堆移动 | test_t18a11_aoe.py + aoe_reproduction.log；相关237通过 | 1e81f90 |
| R09 | 孟获祸首/南蛮多目标 | 每目标重新寻找祸首；持有者中途死亡后来源回退出牌者 | 同次南蛮指定目标时固定来源，死亡后后续伤害无来源；中途失效不改已固定来源 | 错误伤害归属及潜在奖惩/反馈触发 | test_t18a11_aoe.py刚烈真实死亡和失效重连；huoshou_reproduction.log | 1e81f90 |

继续审计首批新增2个真实规则缺陷。此前九项为8f04076 checkpoint历史计数；当前累计已修11项。奇策未被巨象取得符合固定历史来源，不计为缺陷。死亡夹具只读属性错误不计为产品缺陷。BLOCKED清零前不跑最终全量验收，不签发RC。

| R10 | 奇策/乱击/火计/蛊惑虚拟锦囊伤害 | 单目标效果只保留首材料ID；奸雄漏其余材料、无言认成基本牌、裸衣将杀材料误增伤 | 同一次使用的有效牌定义和全材料传递到伤害；按真实锦囊语义结算 | 六个新失败用例涉及错误获得/防止/增伤，共同元数据根因 | virtual_aoe_reproduction.log；test_t18a11_aoe.py；326相关回归通过 | 1e81f90 |
| R11 | 经典奸雄材料资格 | 接受部分仍可取得材料，包括弃堆材料 | 经典版本全材料均须仍在处理区；不拼接不完整虚拟牌，不从弃堆捞回 | 非法取得部分/已结算材料 | jianxiong_reproduction.log 2项；test_t18a11_aoe.py | 1e81f90 |
| R12 | 五谷丰登多目标揭示 | 初始池按免疫过滤后目标数；从牌堆先进出牌者手牌再移公共池 | 按存活角色数揭示，直接公共池；被免疫目标跳过效果，余牌最终清理 | 牌数不足及伪造手牌得失事实 | grace_reproduction.log；test_t18a11_aoe.py | 1e81f90 |

本轮后续又修复3项根因（R10–R12），累计14项真实缺陷；新增6个虚拟AOE失败用例属于同一元数据根因，不能计成6项产品缺陷。看破及无懈首批16个新增用例未发现差异。奸雄、无言、乱击、奇策等技能尚有优先级4/7触发与限制边界待核，保持BLOCKED，不能因当前组合修复就宣称完整闭环。

| R13 | 张角鬼道交换 | 替换判定后旧牌入弃堆 | 经典鬼道交换旧判定牌到持有者手牌；新牌成为最终判定牌 | 漏合法取得牌 | judgment_reproduction.log hand/equipment；test_t18a11_judgment.py | 1e81f90 |
| R14 | 鬼才/鬼道/极略多持有者 | 每技能next只查第一人，按技能组固定先后 | 当前回合座次逐角色改判，可连续替换；每人请求/移动事件ID唯一 | 遗漏合法改判、错误最终结果/重连事件 | judgment_reproduction.log order；两鬼才/鬼才鬼道天妒链 | 1e81f90 |
| R15 | 闪电传递 | 未命中/无懈后未查帷幕，重复检查仅实体定义 | 检查禁止目标及有效转化同名判定牌 | 非法传给帷幕、判定区叠同名牌 | lightning_reproduction.log 2项 | 1e81f90 |
| R16 | 潜袭与鬼才/鬼道/极略改判 | 禁止打出的黑色手牌仍列候选 | 改判按response合法材料，禁手牌不禁装备；无合法牌不扣忍 | 绕过颜色限制 | retrial_limit_reproduction.log 3项及装备反例 | 1e81f90 |

本轮判定再修4项基线规则根因，累计18项已修；判定相关325通过。人工中途技能失效实验缺乏时机证据，未计缺陷。新增DelayedHandler依赖漏注入与多持有者重复事件ID为本轮开发过程错误，已修，不额外计入基线缺陷。矩阵未核边界仍保留BLOCKED。

| R17 | 徐庶无言/闪电 | 牌类型仅trick.*，忽略delayed.*，闪电命中仍受3伤 | 锁定TypeTrick包含延时锦囊，闪电命中也防止伤害 | 漏合法伤害防止 | lightning_wuyan_reproduction.log 2/9点失败；1/10反例 | 1e81f90 |
| R18 | 贾诩帷幕/经典于吉蛊惑 | 无人质疑黑材料声明AOE被帷幕错误免疫 | 固定历史Weimu允许经典nosguhuo例外，项目guhuo沿此版本；其他黑锦囊不豁免 | 非法免疫经典蛊惑声明 | guhuo_weimu_reproduction.log；test_t18a11_aoe.py | 1e81f90 |

新增R17/R18，累计20项已修基线根因。当前矩阵186 BLOCKED、4 FIXED、2 PASS；本轮只关闭证据完整的巨象/祸首/看破/帷幕/谦逊，其他组合已修仍留待整技能闭环。禁止表新增11项通过，最终门禁尚未开始。

| R19 | 贞烈/AOE效果免疫目标确认 | 藤甲/祸首/巨象/智迟免疫目标先被过滤，遗漏贞烈合法确认窗口 | TargetConfirmed先于效果免疫；合法目标可选择贞烈成本和来源弃牌，AOE其他目标独立 | 漏合法技能时机 | zhenlie_immune_reproduction.log 3真实失败+1夹具错误；修后multitarget345、zhenlie60通过 | 1e81f90 |

R10补齐用牌事件虚拟元数据：混色奇策巧说新增帷幕目标错误也归入同一根因，不另计。R19后累计21项基线根因已修；当前185 BLOCKED、5 FIXED、2 PASS；尚未执行最终门禁。

| R20 | 延时锦囊/闪电材料位置 | 改判时延时牌仍判定区；闪电先弃再伤害 | 生效前移处理区；效果/伤害反应结束后仍在处理区才清理，已被取得不抢回；转化定义保存在frame | 判定区错误占位、漏合法奸雄取得 | delayed_table_reproduction.log 2项；delayed_targeted407、转化91通过 | 1e81f90 |
| R21 | 无双杀/决斗响应额度 | 每次响应重新查权限，中途失效让第二闪/杀需求消失；决斗响应编号缺失 | 当前次使用冻结响应额度，双响应各有1/2及2/2提示，牌结束清理 | 少付合法响应、重连提示不一致 | duel_reproduction.log；slash_quota_reproduction.log；duel_targeted250通过 | 1e81f90 |

R20/R21后累计23项基线根因已修。无双还存在多目标冻结时机待核，不能据这些测试关闭整项。无言已按锁定锦囊伤害防止版本完成类型边界闭环，当前184 BLOCKED、6 FIXED、2 PASS。最终门禁未运行。

| R22 | 大乔流离装备成本后距离 | 弃进攻马固定距离仍手算+1，误禁合法固定距离目标 | 固定距离优先，成本后共享距离/范围系统评估；隔离探测不修改真实区位 | 漏合法转移 | liuli_distance_reproduction.log；正式赤兔转移和武器/马/手牌反例；liuli157通过 | 1e81f90 |
| R23 | 流离目标合法性 | 仅检查转移者距离，允许转给空手空城等来源不合法目标 | 新目标须对原杀来源合法（无距离限制但保留禁止目标） | 非法指定杀目标 | liuli_kongcheng_reproduction.log；liuli_targeted157通过 | 1e81f90 |

R22/R23后累计25项已修基线根因；无双多目标额度问题属于R21同根因，未重复计。流离继续BLOCKED以保留尚未核完时机。当前仍184 BLOCKED。

| R24 | 奇策虚拟牌来源 | VirtualCard.skill_id为空，缺经典QiceCard设置的技能来源 | 声明虚拟锦囊保留qice来源 | 使用事件/伤害无法完整识别技能来源 | qice_identity_reproduction.log 1真实失败+1异常类型夹具；qice_targeted95 | 1e81f90 |
| R25 | 乱击使用限制 | 同花色材料未检查潜袭、巧说、惴恐、自守使用限制 | 候选/提交统一共享锦囊可用性及有效颜色限制 | 非法万箭使用和成本消耗 | luanji_limit_reproduction.log四限制；luanji_targeted120 | 1e81f90 |
| R26 | 乱击无序材料 | 合法同花色双材料逆序提交被拒绝 | 按双牌集合校验，仍排除同牌重复 | 漏合法操作 | 同日志反序失败及真实结算重连 | 1e81f90 |

新增R24–R26，累计28项已修基线根因。奇策/乱击关闭FIXED；当前182 BLOCKED、8 FIXED、2 PASS。旧角色前缀及异常类型夹具不计产品缺陷。最终全量门禁未运行，未签发RC。

| R27 | 智迟伤害后时机 | HP扣减时立即授保护，求桃前已生效 | 求桃/死亡处理完成后的Damaged入口检查一次 | 过早获得回合保护 | zhichi_reproduction.log fatal；逐请求恢复 | 1e81f90 |
| R28 | 智迟活跃回合资格 | 无当前角色、无phase、当前角色已死仍获得保护 | 必须当前角色存活且有活跃phase，持有者回合外存活有效 | 非回合时间非法保护 | 同日志3活跃条件失败 | 1e81f90 |
| R29 | 智迟当前角色死亡 | 只在后续TurnAction清标记，死亡立即清理遗漏 | 当前角色死亡时全员立即清智迟；非当前死亡不清 | 过期免疫影响死亡技能/连环后续 | 同日志死亡失败及非当前反例 | 1e81f90 |

R27–R29后三十一项已修基线根因；智迟关闭FIXED。当前181 BLOCKED、9 FIXED、2 PASS。213/124分别为相关长回归和新增边界批次。最终门禁尚未运行，不签发RC。

| R30 | 改判非活跃当前角色顺序 | 无phase仍从当前角色首先改判 | 固定classic getAllPlayers规则将NotActive当前角色尾移 | 错误最后改判者及结果 | judgment_finish_reproduction.log order；157相关回归 | 1e81f90 |
| R31 | 天妒拒绝与洛神独立取得 | 拒绝天妒强制判定牌入弃堆，忽略gain_on_match | 天妒拒绝仍尊重独立成功判定取得 | 漏合法取得牌 | 同日志gain失败；157相关回归 | 1e81f90 |

R30/R31后累计33项已修基线根因；本批不关闭尚缺其他时机证据的改判技能。当前仍181 BLOCKED、9 FIXED、2 PASS；最终门禁未开始。

| R32 | 共享ViewAs用牌资格/限制 | 部分转化动作绕过潜袭手牌颜色、巧说锦囊禁用；连环使用绕过颜色限制 | 共享validate_view_as_limits在请求/付款前验证角色、阶段、技能与有效牌限制；重铸保留独立例外 | 非法使用与成本消耗 | view_as_limits_reproduction.log初版9真实失败+1参数夹具；longhun_limit/lianhuan_limit独立原checkpoint复现；279相关通过 | b4964e1 |
| R33 | 共享龙胆Slash牌族 | 普通杀可转闪，火杀/雷杀遗漏 | response.longdan_materials统一有效Slash族供响应和method-none提供 | 遗漏合法响应 | longdan_slash_identity_reproduction.log 2失败 | b4964e1 |
| R34 | 共享转化响应编号 | 武圣/急救等路径默认1/1，丢失实际2/2 | _record_material_response统一传递当前响应编号 | 重连/交互事件提示错误 | view_as_response_number_reproduction.log 2失败 | b4964e1 |
| R35 | 共享双材料响应合同 | 丈八/父魂两材料记成两次响应，直接手牌到弃堆 | 全材料先复核后批量经处理区付款，一张虚拟杀记一次响应 | 响应事实重复及移动合同不一致 | two_material_response_reproduction.log 2失败 | b4964e1 |
| R36 | 转化提交权限复核 | 龙胆目标请求恢复后技能失效仍付款使用 | 共享校验再次检查角色/阶段/技能资格 | 过期请求非法使用 | view_as_submit_reproduction.log 1失败、4反例通过 | b4964e1 |

本批共享根因新增5项，累计38项基线缺陷已修。版本差异、夹具错误和未核验项不计为产品bug，分类见view_as_system_audit.md。6项关闭后当前175 BLOCKED、14 FIXED、3 PASS；低于30–50项清理区间，未跑full pytest或最终七项验收。


Damage / HP / death batch; code checkpoint 1f3f2bb:

| R37 | Dying rescue seats | Target-first rescue | Rotate current seat; inactive current last | Shared rule root; details in damage_system_audit.md | rescue order; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |
| R38 | Dying repeated rescue | Peach restarts the seat scan | Same rescuer repeats until saved or passes | Shared rule root; details in damage_system_audit.md | multiple Peach and snapshot; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |
| R39 | Recover no-op | Full HP emits zero event; dead target raises | Full/dead silently complete without event | Shared rule root; details in damage_system_audit.md | full/dead and cap; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |
| R40 | LoseMaxHP zero | Zero max HP enters Peach rescue | Direct death when max HP becomes zero | Shared rule root; details in damage_system_audit.md | zero max HP; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |
| R41 | Dead damage source | Damage credits already dead source | Normalize dead source to None | Shared rule root; details in damage_system_audit.md | dead-source event; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |
| R42 | Terminal resolution | Parents can create ordinary requests after victory | Engine-wide terminal gate; discard transient public cards; allow death exceptions before FINISHED | Shared rule root; details in damage_system_audit.md | parent gate; Zhuiyi/Wuhun; chain stop; public cleanup; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |
| R43 | Damage source modifiers | Anjian applied after Tianxiang; transferred Luoyi repeats | Freeze source bonus before transfer and target modifiers; exclude chain/transfer | Shared rule root; details in damage_system_audit.md | transfer reproduction and negative packets; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |
| R44 | Jiuyuan rescuer faction | Checks rescuer faction matches recipient | Checks Wu rescuer; lord/effective skill/other rescuer gates remain | Shared rule root; details in damage_system_audit.md | Wu vs matching Wei; self/nonlord/disabled; test_t18a11_damage_system.py; 302 targeted passed | 1f3f2bb |

8 new baseline roots repaired; cumulative 46 (previous 38). Correct-but-unverified, version differences and fixture/development errors are classified separately in damage_system_audit.md. Closed 4 rows: Jiuyuan/Wansha/Anjian FIXED, Zhuiyi PASS. Current {'BLOCKED': 171, 'FIXED': 17, 'PASS': 4}. No full pytest or final acceptance gates; no RC issued.


CardMove / special-pile batch; code 8d449b4:

| R45 | Tuntian movement qualification | Own hand/equipment relocation triggers; inactive current loss misses | NotActive current qualifies actual loss; same owner hand/equipment transfers excluded | Shared movement / area eligibility root | card_move_system_reproduction.log; 354 related + 2 AI + 3 privacy passed | 8d449b4 |
| R46 | Power pile derived count | Shared pile/death moves leave quan mark stale | Shared CardMove updates/removes count from authoritative zone | Shared movement / area eligibility root | card_move_system_reproduction.log; 354 related + 2 AI + 3 privacy passed | 8d449b4 |
| R47 | Zongxuan internal movement facts | Reservation triggers early/duplicate equipment departure and duplicate public final discard | Internal moves preserved for state but not rules/public events; publish original-source final facts once; top placements revealed | Shared movement / area eligibility root | card_move_reservation_reproduction.log; 354 related + 2 AI + 3 privacy passed | 8d449b4 |
| R48 | Xingshang eligible areas | Judgment cards gained with hand/equipment | Hand + equipment only; judgment/private pile remains death cleanup | Shared movement / area eligibility root | card_move_inherit_reproduction.log; 354 related + 2 AI + 3 privacy passed | 8d449b4 |

Four additional real baseline product roots, cumulative 50. Two separate contract improvements (H01 multizone obtain prevalidation on constructed corrupt state; C01 Xingshang acquisition summary) are not added to baseline defect count. Version differences and fixture errors recorded separately in card_move_system_audit.md. Closed Quanji/Xingshang FIXED; {'BLOCKED': 169, 'FIXED': 19, 'PASS': 4}. No full/final gates or RC approval.


Judgment / delayed batch; code b9558ef, coverage checkpoint 07d6bcb:

| R49 | Successful judgment destination | Tuntian enters discard/Luoying before field | Shared inverted pattern and success_destination route processing directly to field, preserve independent destination after Tiandu decline | Real baseline product bug | judgment_system_reproduction.log; judgment_system_audit.md; 299 targeted Python / 46 scoped Web | 07d6bcb |
| R50 | Final contextual face | Hongyan public spade vs heart result; Guidao AI uses actor context | Freeze final judged-player suit/color; public reveal/retrial/final and AI preference use correct context | Real baseline product bug, two manifestations of same semantic root | judgment_system_reproduction.log; judgment_ai_context_reproduction.log | 07d6bcb |
| R51 | Delayed consequence presentation | No Chinese outcome; final match text overwritten; AI retrial no dedicated dwell | Public delayed_result, Web/desktop final face/result and scoped AI dwell | Real product presentation gap | 3 outcome reproductions; scoped GamePage/pacing/desktop tests | 07d6bcb |
| R52 | Public reconnect lifecycle | Initial/replaced judgment and delayed result absent from history | Preserve reveal/retrial/final/transfer public history | Real baseline reconnect gap | judgment_restore_reproduction.log; Tiandu and transfer restore tests | 07d6bcb |
| R53 | FinishJudge vs cleanup | Luoying before Songwei after default discard | Offer FinishJudge Songwei before shared disposition; restore saved destination | Real baseline product bug; multiple FinishJudge ordering still BLOCKED | judgment_finish_order_reproduction.log | 07d6bcb |

Five additional real baseline roots, cumulative **55** (previous 50). H02 stale ResolveDelayed rejection is a defensive contract: dead/moved entry tests directly construct an invalid action, without proof of a natural reachable baseline bug; not included in R49-R53. A lethal-lightning cleanup regression introduced by the new guard was reproduced and repaired during development; not added to baseline count. Fixture and version differences are separately classified in judgment_system_audit.md and judgment_fixture_notes.md.

Scope 28 dependent rows / 27 unique skills. Closed Hongyan FIXED; newly closed PASS 0. Current matrix **168 BLOCKED / 20 FIXED / 4 PASS**. Shared proof does not close same-owner retrial/FinishJudge ordering; remaining clauses explicitly listed per dependency. 299 related Python and 46 scoped Web passed. No full pytest, Huashen 795 or final gates; no RC issued.

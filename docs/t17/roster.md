# T17A 38将完整定义目录
基线88ca556；非生产设计。LOCKED_REFERENCE只锁定所引档案的具体文本，不证明官方发行历史。QUESTION的文本是候选，不能开始实现。每人都受Q00官方出处补证门禁。阶段技在本目录设计为每出牌阶段限一次；与每回合限一次不同。技能段保留来源原文，界/十周年等文本只作排除对照。中文现代化排版不代表新增规则。
ID审计：现有标准无包前缀、神话再临使用wind/fire/forest/mountain前缀加拼音词；神将位于对应包内含_god_。新ID采用yj2011/2012/2013加分词拼音；阴/雷神将shadow_god_和thunder_god_，不机械套用示例。严禁建立shen_*第二ID。神势力是历史metadata；现行Kingdom没有god，候选runtime沿用旧神将qun映射，不能修改枚举。全体无主公技；主公身份局体力加成由现行规则处理，不写进Base HP。

## yj2011_zhang_chunhua

| Field | Definition |
| --- | --- |
| General ID | yj2011_zhang_chunhua |
| Chinese Name | 张春华 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | wei；当前runtime映射 wei |
| Gender | female |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | jueqing, shangshi；获得后才可用： |
| Chinese Skill Names | 绝情, 伤逝 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | QUESTION Q02；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 此项等待人工确认，不能视为最终官方版本锁。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | HPREWRITE, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | MEDIUM；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | YES_NO |
| Test Requirements | 火杀连环不传导；失去体力无伤害触发；上限变化；伤逝上限2/不封顶 |


### jueqing — 绝情 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 锁定技。伤害结算开始前，你将要造成的伤害视为失去体力。

来源键 `jueqing`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：伤害正式产生前改为 LoseHpAction，保留原始行动链但不发布伤害事件；禁止铁索复制；无伤害杀手归因需Q08。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rejueqing`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你对其他角色造成伤害时，你可以令此伤害值+X。若如此做，你失去X点体力并修改〖绝情〗（X为伤害值）。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `jueqing`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，你即将造成的伤害均视为失去体力。

**Test Requirements**：伤害正式产生前改为 LoseHpAction，保留原始行动链但不发布伤害事件；禁止铁索复制；无伤害杀手归因需Q08。；火杀连环不传导；失去体力无伤害触发；上限变化；伤逝上限2/不封顶；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### shangshi — 伤逝 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 每当你的手牌数、体力值或体力上限改变后，你可以将手牌补至X张。（X为你已损失的体力值且至多为2）

来源键 `shangshi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：手牌/HP/maxHP变化后请求补至min(已损HP,2)；一次反应快照后再检测，避免自身摸牌递归。

**UI/Decision**：YES_NO。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosshangshi`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当你的手牌数、体力值或体力上限改变后，若你的手牌数小于X，你可以将手牌补至X张。（X为你已损失的体力值）

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reshangshi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你受到伤害时，你可以弃置一张牌。当你的手牌数小于X时，你可以将手牌摸至X张。（X为你已损失的体力值）

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `shangshi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你的手牌数小于X时，你可以将手牌摸至X张（X为你已损失的体力值）。

**Test Requirements**：手牌/HP/maxHP变化后请求补至min(已损HP,2)；一次反应快照后再检测，避免自身摸牌递归。；火杀连环不传导；失去体力无伤害触发；上限变化；伤逝上限2/不封顶；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_yu_jin

| Field | Definition |
| --- | --- |
| General ID | yj2011_yu_jin |
| Chinese Name | 于禁 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | yizhong；获得后才可用： |
| Chinese Skill Names | 毅重 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | C；BALANCE RISK：下限过弱；不要自行加强 |
| Implementation Complexity | Tier 1 |
| Engine Dependencies | TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | NONE |
| AI Complexity | LOW；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | 无需主动请求 |
| Test Requirements | 黑杀/红杀/虚拟无色杀；防具被移走；无效非不能指定 |


### yizhong — 毅重 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。若你的装备区没有防具牌，黑色【杀】对你无效。

来源键 `yizhong`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：被指定可合法；效果阶段黑色杀且无防具则对该角色无效。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `yizhong`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，当你的防具栏为空时，黑色的【杀】对你无效。

**Test Requirements**：被指定可合法；效果阶段黑色杀且无防具则对该角色无效。；黑杀/红杀/虚拟无色杀；防具被移走；无效非不能指定；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_cao_zhi

| Field | Definition |
| --- | --- |
| General ID | yj2011_cao_zhi |
| Chinese Name | 曹植 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | luoying, jiushi；获得后才可用： |
| Chinese Skill Names | 落英, 酒诗 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | DYING, MOVE, REACTION, VIEWAS；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：落英限他人弃置/判定；酒诗记录受伤前朝向 |
| UI/Decision Requirements | CHOOSE_CARDS, CHOOSE_OPTION, YES_NO |
| Test Requirements | 使用材料不落英；已被获得不可再取；濒死酒诗；翻面跳回合；多点伤害一次翻面 |


### luoying — 落英 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 其他角色的牌因判定或弃置而置入弃牌堆时，你可以获得其中至少一张梅花牌。

来源键 `luoying`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：只接受他人牌的弃置与判定弃置批次，逐张重检仍在弃牌堆且有效梅花；对使用/响应弃牌不触发。

**UI/Decision**：YES_NO, CHOOSE_CARDS。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reluoying`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当其他角色的梅花牌因弃置或判定而进入弃牌堆后，你可以获得之。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `luoying`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当其他角色的梅花牌因弃置或判定而进入弃牌堆后，你可以获得之。

**Test Requirements**：只接受他人牌的弃置与判定弃置批次，逐张重检仍在弃牌堆且有效梅花；对使用/响应弃牌不触发。；使用材料不落英；已被获得不可再取；濒死酒诗；翻面跳回合；多点伤害一次翻面；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### jiushi — 酒诗 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 若你的武将牌正面朝上，你可以将武将牌翻面，视为你使用了一张【酒】。每当你受到伤害扣减体力前，若武将牌背面朝上，你可以在伤害结算后将武将牌翻至正面朝上。

来源键 `jiushi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：酒的合法窗口翻面虚拟使用；伤害扣HP前记录face_up，结算后只按快照决定翻正。

**UI/Decision**：CHOOSE_OPTION, YES_NO。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rejiushi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你需要使用【酒】时，若你的武将牌正面向上，你可以翻面，视为使用一张【酒】。当你受到伤害后，若你的武将牌背面向上且你未因此次伤害发动过〖酒诗〗，你可以翻面并获得牌堆中的一张随机锦囊牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `dcjiushi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。①当你需要使用【酒】时，若你的武将牌正面向上，你可以翻面，视为使用一张【酒】。②当你受到伤害后，若你的武将牌于受到伤害时背面向上，你可以翻面。③当你使用【酒】后，你使用【杀】的次数上限+1直到你的下个回合结束。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `jiushi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你需要使用一张【酒】时，若你的武将牌正面朝上，则你可以将武将牌翻面并视为使用了一张【酒】；当你受到伤害后，若你的武将牌于受到伤害时背面向上，你可以翻面。

**Test Requirements**：酒的合法窗口翻面虚拟使用；伤害扣HP前记录face_up，结算后只按快照决定翻正。；使用材料不落英；已被获得不可再取；濒死酒诗；翻面跳回合；多点伤害一次翻面；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_fa_zheng

| Field | Definition |
| --- | --- |
| General ID | yj2011_fa_zheng |
| Chinese Name | 法正 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | enyuan, xuanhuo；获得后才可用： |
| Chinese Skill Names | 恩怨, 眩惑 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 原版修订由回复联动改为牌获得联动，并用摸牌替代眩惑，身份辅助更可用而不带界版追加收益。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | AUTHUSE, MOVE, REACTION, SEQUENCE, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：恩怨按单次获得两张/每点伤害；眩惑由法正选杀目标 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_OPTION, CHOOSE_PLAYER, USE_CARD, YES_NO |
| Test Requirements | 混合来源不合并恩；两点伤害两次怨；无来源；杀不可用转获得两牌；死亡中止 |


### enyuan — 恩怨 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你获得一名其他角色的两张或更多的牌后，你可以令其摸一张牌。每当你受到1点伤害后，你可以令伤害来源选择一项：交给你一张手牌，或失去1点体力。

来源键 `enyuan`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：同一获得批次同一他人来源≥2可令其摸1；实际伤害每点要求来源给一手牌或失去HP，来源为空不要求。

**UI/Decision**：YES_NO, CHOOSE_OPTION, CHOOSE_CARD。choice_labels：`{"give": "交出所选手牌", "lose_hp": "失去1点体力"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosenyuan`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。锁定技。每当你回复1点体力后，令你回复体力的角色摸一张牌；每当你受到伤害后，伤害来源选择一项：交给你一张红桃手牌，或失去1点体力。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reenyuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你获得一名其他角色的至少两张牌后，你可以令其摸一张牌。当你受到1点伤害后，你可令伤害来源选择一项：①失去1点体力。②交给你一张手牌。若此牌不为♥，则你摸一张牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinenyuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你获得一名其他角色两张或更多的牌后，你可以令其摸一张牌；当你受到1点伤害后，你可以令伤害来源选择一项：1、将一张手牌交给你；2、失去1点体力。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `enyuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技。①当其他角色令你回复1点体力后，该角色摸一张牌。②当其他角色对你造成伤害后，其须交给你一张♥手牌，否则失去1点体力。

**Test Requirements**：同一获得批次同一他人来源≥2可令其摸1；实际伤害每点要求来源给一手牌或失去HP，来源为空不要求。；混合来源不合并恩；两点伤害两次怨；无来源；杀不可用转获得两牌；死亡中止；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### xuanhuo — 眩惑 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 摸牌阶段开始时，你可以放弃摸牌并选择一名其他角色：若如此做，该角色摸两张牌，然后该角色可以对其攻击范围内由你选择的一名角色使用一张【杀】，否则令你获得其两张牌。

来源键 `xuanhuo`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：替代正常摸牌，选受益者摸2，法正选其范围内合法杀目标；受益者USE_CARD，不用则法正依次获得其至多2牌。

**UI/Decision**：YES_NO, CHOOSE_PLAYER, USE_CARD, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosxuanhuo`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。阶段技。你可以将一张红桃手牌交给一名其他角色：若如此做，你获得该角色的一张牌，然后将此牌交给除该角色外的另一名角色。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rexuanhuo`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。摸牌阶段结束时，你可以交给一名其他角色两张手牌，然后该角色选择一项：1. 视为对你选择的另一名角色使用任意一种【杀】或【决斗】，2. 交给你所有手牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinxuanhuo`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。摸牌阶段开始时，你可以改为令一名其他角色摸两张牌，然后该角色需对其攻击范围内你选择的另一名角色使用一张【杀】，否则你获得其两张牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `xuanhuo`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以将一张红桃手牌交给一名其他角色，获得该角色的一张牌，然后交给除该角色外的一名其他角色。

**Test Requirements**：替代正常摸牌，选受益者摸2，法正选其范围内合法杀目标；受益者USE_CARD，不用则法正依次获得其至多2牌。；混合来源不合并恩；两点伤害两次怨；无来源；杀不可用转获得两牌；死亡中止；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_ma_su

| Field | Definition |
| --- | --- |
| General ID | yj2011_ma_su |
| Chinese Name | 马谡 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | xinzhan, huilei；获得后才可用： |
| Chinese Skill Names | 心战, 挥泪 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | C；BALANCE RISK：下限过弱；不要自行加强 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | DEATH, MOVE, ORDER, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：心战私看三牌、公开红桃、余牌排序；挥泪死亡惩罚 |
| UI/Decision Requirements | CHOOSE_CARDS, CHOOSE_OPTION, YES_NO |
| Test Requirements | 手牌=上限不能发动；红桃0/1/3；顶牌顺序；无来源死亡；挥泪与反贼奖励顺序 |


### xinzhan — 心战 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。若你的手牌数大于你的体力上限，你可以观看牌堆顶的三张牌，然后你可以展示并获得其中至少一张红桃牌，然后将其余的牌置于牌堆顶。

来源键 `xinzhan`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：一次出牌阶段；手牌>maxHP才私看顶3；可拒绝拿红桃，选择非空红桃集则公开获得；剩余排序。

**UI/Decision**：YES_NO, CHOOSE_CARDS, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `xinzhan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，若你的手牌数大于你的体力上限，你可以观看牌堆顶的三张牌，然后展示其中任意红桃牌并获得之。

**Test Requirements**：一次出牌阶段；手牌>maxHP才私看顶3；可拒绝拿红桃，选择非空红桃集则公开获得；剩余排序。；手牌=上限不能发动；红桃0/1/3；顶牌顺序；无来源死亡；挥泪与反贼奖励顺序；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### huilei — 挥泪 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。你死亡时，杀死你的其他角色弃置其所有牌。

来源键 `huilei`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：死亡触发，杀手为其他人且有牌则弃其规则范围所有牌；与奖励、行殇优先级须冻结。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `huilei`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，当你死亡时，杀死你的角色弃置所有的牌。

**Test Requirements**：死亡触发，杀手为其他人且有牌则弃其规则范围所有牌；与奖励、行殇优先级须冻结。；手牌=上限不能发动；红桃0/1/3；顶牌顺序；无来源死亡；挥泪与反贼奖励顺序；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_xu_shu

| Field | Definition |
| --- | --- |
| General ID | yj2011_xu_shu |
| Chinese Name | 徐庶 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | wuyan, jujian；获得后才可用： |
| Chinese Skill Names | 无言, 举荐 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择锦囊伤害防止与末阶段举荐，保留非伤害锦囊可用，避免初版大面积锦囊无效。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | HPREWRITE, MOVE, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | MEDIUM；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_OPTION, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 顺手/无中照常；南蛮来源替换；延时锦囊伤害；重置含解连环与翻正；无伤不可回复 |


### wuyan — 无言 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。每当你造成或受到伤害时，防止锦囊牌的伤害。

来源键 `wuyan`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：在锦囊导致伤害时若来源或目标拥有技能则取消；不取消牌效果本身；南蛮先替换来源再判断。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `noswuyan`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。锁定技。你使用的非延时锦囊牌对其他角色无效。其他角色使用的非延时锦囊牌对你无效

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinwuyan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，当你使用锦囊牌造成伤害时，你防止此伤害；锁定技，当你受到锦囊牌对你造成的伤害时，你防止此伤害。

**Test Requirements**：在锦囊导致伤害时若来源或目标拥有技能则取消；不取消牌效果本身；南蛮先替换来源再判断。；顺手/无中照常；南蛮来源替换；延时锦囊伤害；重置含解连环与翻正；无伤不可回复；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### jujian — 举荐 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 结束阶段开始时，你可以弃置一张非基本牌并选择一名其他角色：若如此做，该角色选择一项：摸两张牌，或回复1点体力，或重置武将牌并将其翻至正面朝上。

来源键 `jujian`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：结束阶段可付一非基本牌成本选其他人，由其选摸2/恢复1/解连环并翻正。

**UI/Decision**：YES_NO, CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION。choice_labels：`{"draw": "摸牌", "recover": "回复体力", "reset": "解除连环并翻至正面"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosjujian`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。阶段技。你可以弃置至多三张牌并选择一名其他角色：若如此做，该角色摸等量的牌。若你以此法弃置三张同一类别的牌，你回复1点体力。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinjujian`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。结束阶段开始时，你可以弃置一张非基本牌并选择一名其他角色，令其选择一项：1.摸两张牌；2.回复1点体力；3.将其武将牌翻转至正面朝上并重置之。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `jujian`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以弃至多三张牌，然后令一名其他角色摸等量的牌。若你以此法弃牌不少于三张且均为同一类别，你回复1点体力。

**Test Requirements**：结束阶段可付一非基本牌成本选其他人，由其选摸2/恢复1/解连环并翻正。；顺手/无中照常；南蛮来源替换；延时锦囊伤害；重置含解连环与翻正；无伤不可回复；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_ling_tong

| Field | Definition |
| --- | --- |
| General ID | yj2011_ling_tong |
| Chinese Name | 凌统 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | wu；当前runtime映射 wu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | xuanfeng；获得后才可用： |
| Chinese Skill Names | 旋风 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择装备失去/弃牌阶段旋风弃2，不采用最初视为杀/近距离伤害，也不带后期移动装备或额外伤害。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | MOVE, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：装备离区整批触发；弃牌阶段至少两牌一次触发 |
| UI/Decision Requirements | CHOOSE_OPTION, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 换装/甘露/死亡离区；同人两牌逐次合法；不足两牌；成本弃置与规则弃置范围核对 |


### xuanfeng — 旋风 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你失去一次装备区的牌后，或弃牌阶段结束时若你于本阶段内弃置了至少两张你的牌，你可以弃置一名其他角色的一张牌，然后弃置一名其他角色的一张牌。

来源键 `xuanfeng`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：装备离区以移动批次一次触发，或弃牌阶段结束满足≥2；两次区域弃置可相同角色，逐次校验。

**UI/Decision**：YES_NO, CHOOSE_PLAYER, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosxuanfeng`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当你失去一次装备区的牌后，你可以选择一项：视为使用一张无距离限制的【杀】，或对距离1的一名角色造成1点伤害

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rexuanfeng`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你失去装备区内的牌时，或于弃牌阶段弃置了两张或更多的手牌后，你可以依次弃置一至两名其他角色的共计两张牌，或将一名其他角色装备区内的一张牌移动到另一名其他角色的装备区内。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadexuanfeng`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你于弃牌阶段弃置过至少两张牌，或当你失去装备区里的牌后，若场上没有处于濒死状态的角色，则你可以弃置至多两名其他角色的共计两张牌。若此时处于你的回合内，你可以对其中一名目标角色造成1点伤害。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `xuanfeng`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你失去装备区内的牌时，或于弃牌阶段弃置了两张或更多的手牌后，你可以依次弃置一至两名其他角色的共计两张牌。

**Test Requirements**：装备离区以移动批次一次触发，或弃牌阶段结束满足≥2；两次区域弃置可相同角色，逐次校验。；换装/甘露/死亡离区；同人两牌逐次合法；不足两牌；成本弃置与规则弃置范围核对；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_xu_sheng

| Field | Definition |
| --- | --- |
| General ID | yj2011_xu_sheng |
| Chinese Name | 徐盛 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | wu；当前runtime映射 wu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | pojun；获得后才可用： |
| Chinese Skill Names | 破军 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 1 |
| Engine Dependencies | REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | MEDIUM；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | YES_NO |
| Test Requirements | 濒死救回后HP；X=0；伤害多点一次；原版不扣牌不增伤 |


### pojun — 破军 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你使用【杀】对目标角色造成伤害后，你可以令其摸X张牌，然后将其武将牌翻面。（X为该角色的体力值且至多为5）

来源键 `pojun`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：杀伤后角色存活时选发动，X=max(0,min(当前HP,5))，摸X再翻面；濒死结算完成后判断。

**UI/Decision**：YES_NO。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `repojun`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你使用【杀】指定目标后，你可以将其的至多X张牌置于其武将牌上（X为其体力值），然后其于当前回合结束时获得这些牌。当你使用【杀】对一名角色造成伤害时，若该角色的手牌数和装备区内的牌数均不大于你，则此伤害+1。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadepojun`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你使用【杀】指定目标后，你可以将其的至多X张牌置于其武将牌上（X为其体力值）。若这些牌中：有装备牌，你将这些装备牌中的一张置于弃牌堆；有锦囊牌，你摸一张牌。其于回合结束时获得其武将牌上的这些牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinpojun`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你于出牌阶段内使用【杀】指定一个目标后，你可以将其至多X张牌扣置于该角色的武将牌旁（X为其体力值）。若如此做，当前回合结束后，该角色获得其武将牌旁的所有牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `pojun`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你使用【杀】造成伤害后，你可以令受伤角色摸X张牌，然后其翻面（X为该角色的体力值且至多为5）。

**Test Requirements**：杀伤后角色存活时选发动，X=max(0,min(当前HP,5))，摸X再翻面；濒死结算完成后判断。；濒死救回后HP；X=0；伤害多点一次；原版不扣牌不增伤；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_wu_guotai

| Field | Definition |
| --- | --- |
| General ID | yj2011_wu_guotai |
| Chinese Name | 吴国太 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | wu；当前runtime映射 wu |
| Gender | female |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | ganlu, buyi；获得后才可用： |
| Chinese Skill Names | 甘露, 补益 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | DYING, EXCHANGE, MOVE, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：甘露全装备交换非逐槽覆盖；补益濒死看一张未知手牌 |
| UI/Decision Requirements | CHOOSE_OPTION, CHOOSE_PLAYERS, YES_NO |
| Test Requirements | 双方同槽武器/空槽/白银狮子/枭姬旋风；差值边界；基本牌不救；反复濒死 |


### ganlu — 甘露 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以令装备区的牌数量差不超过你已损失体力值的两名角色交换他们装备区的装备牌。

来源键 `ganlu`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：两角色装备数差绝对值≤已损HP；快照所有槽、统一验证、原子交换再发布整批移动及离装反应。

**UI/Decision**：CHOOSE_PLAYERS。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinganlu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限一次。你可以令两名角色交换装备区内的牌，然后若这两名角色装备区内牌数差的绝对值大于你已损失的体力值，则你弃置两张手牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `ganlu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以选择两名装备区内装备数之差不大于X的角色，令其交换装备区内的牌（X为你已损失的体力值）。

**Test Requirements**：两角色装备数差绝对值≤已损HP；快照所有槽、统一验证、原子交换再发布整批移动及离装反应。；双方同槽武器/空槽/白银狮子/枭姬旋风；差值边界；基本牌不救；反复濒死；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### buyi — 补益 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当一名角色进入濒死状态时，你可以展示该角色的一张手牌：若此牌为非基本牌，该角色弃置此牌，然后回复1点体力。

来源键 `buyi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：濒死者手牌背面选1后公开；非基本则弃该牌恢复1；基本仅展示；死亡决定之前处理。

**UI/Decision**：YES_NO, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinbuyi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。一名角色进入濒死状态时，你可展示其一张手牌。若此牌不为基本牌，则其弃置此牌并回复1点体力。若其以此法弃置的牌移动前为其的唯一一张手牌，则其摸一张牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `buyi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当有角色进入濒死状态时，你可以展示该角色的一张手牌：若此牌不为基本牌，则该角色弃置此牌并回复1点体力。

**Test Requirements**：濒死者手牌背面选1后公开；非基本则弃该牌恢复1；基本仅展示；死亡决定之前处理。；双方同槽武器/空槽/白银狮子/枭姬旋风；差值边界；基本牌不救；反复濒死；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_chen_gong

| Field | Definition |
| --- | --- |
| General ID | yj2011_chen_gong |
| Chinese Name | 陈宫 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | qun；当前runtime映射 qun |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | mingce, zhichi；获得后才可用： |
| Chinese Skill Names | 明策, 智迟 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | AUTHUSE, MOVE, SCOPE, TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：明策真实给牌后授权视为杀或摸牌；智迟持续到当前回合末 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_OPTION, CHOOSE_PLAYER |
| Test Requirements | 杀目标从受赠者计算范围；回合外受伤免后续锦囊；首伤不被自身取消；额外回合清理 |


### mingce — 明策 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以将一张装备牌或【杀】交给一名其他角色：若如此做，该角色可以视为对其攻击范围内由你选择的一名角色使用一张【杀】，否则其摸一张牌。

来源键 `mingce`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：一次出牌阶段给装备或杀，陈宫选合法杀目标，受益者选择视为杀/摸1；不存在目标仅摸1。

**UI/Decision**：CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION。choice_labels：`{"use_slash": "按授权使用杀", "draw": "摸牌"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `remingce`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限一次。你可以将一张【杀】或装备牌交给一名其他角色，其选择一项：1.视为对你选择的另一名角色使用一张【杀】，且若此牌造成伤害，则执行选项2；2.你与其各摸一张牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `mingce`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段，你可以交给一名其他角色一张装备牌或【杀】，然后令该角色选择一项：1. 视为对其攻击范围内的另一名由你指定的角色使用一张【杀】。2. 摸一张牌。每回合限一次。

**Test Requirements**：一次出牌阶段给装备或杀，陈宫选合法杀目标，受益者选择视为杀/摸1；不存在目标仅摸1。；杀目标从受赠者计算范围；回合外受伤免后续锦囊；首伤不被自身取消；额外回合清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zhichi — 智迟 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。你的回合外，每当你受到伤害后，【杀】和非延时锦囊牌对你无效，直到回合结束。

来源键 `zhichi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：回合外伤后建立当前turn_token内杀和非延时锦囊对本人的效果无效；不撤销首个伤害；回合末统一清理。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zhichi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，当你于回合外受到伤害后，所有【杀】或普通锦囊牌对你无效直到回合结束。

**Test Requirements**：回合外伤后建立当前turn_token内杀和非延时锦囊对本人的效果无效；不撤销首个伤害；回合末统一清理。；杀目标从受赠者计算范围；回合外受伤免后续锦囊；首伤不被自身取消；额外回合清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2011_gao_shun

| Field | Definition |
| --- | --- |
| General ID | yj2011_gao_shun |
| Chinese Name | 高顺 |
| Expansion | yj2011 / 历史来源 yj2011 |
| Year | 2011 |
| Faction | qun；当前runtime映射 qun |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | xianzhen, jinjiu；获得后才可用： |
| Chinese Skill Names | 陷阵, 禁酒 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | PINDIAN, SCOPE, TARGET, VIEWAS；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：陷阵胜利只对拼点对手解除距离杀次数防具；失败全回合禁杀 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_PLAYER |
| Test Requirements | 平局为没赢；对其他人次数正常；仅杀次数；禁酒含自救酒；虚拟酒材料；回合清理 |


### xianzhen — 陷阵 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以与一名其他角色拼点：若你赢，本回合，该角色的防具无效，你无视与该角色的距离，你对该角色使用【杀】无次数限制；若你没赢，你不能使用【杀】，直到回合结束。

来源键 `xianzhen`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：一次出牌阶段拼点；胜则以source,target,turn_token绑定杀次数豁免/距离忽略/防具无效，没赢绑定全局禁用杀。

**UI/Decision**：CHOOSE_PLAYER, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rexianzhen`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限一次，你可以和一名其他角色拼点。若你赢，你本回合内对其使用牌没有次数和距离限制且无视其防具。若你没赢，你本回合内不能使用【杀】。若你以此法失去的拼点牌为【杀】，则你的【杀】不计入本回合的手牌上限。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadexianzhen`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。每回合限一次。出牌阶段，你可以和一名其他角色拼点。若你赢：本回合你无视该角色的防具，且对其使用牌没有次数和距离限制，且本回合对其使用牌造成伤害时，此伤害+1（每种牌名每回合限一次）；若你没赢：你本回合内不能使用【杀】，且【杀】不计入手牌上限。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinxianzhen`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以与一名角色拼点。若你赢，你获得以下效果直到回合结束：无视该角色的防具且对其使用牌没有次数和距离限制，且当你使用【杀】或普通锦囊牌指定唯一目标时，可以令该角色也成为此牌的目标。若你没赢，你不能使用【杀】且你的【杀】不计入手牌上限直到回合结束。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `xianzhen`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以与一名角色拼点。若你赢，你获得以下效果直到回合结束：无视与该角色的距离；无视该角色的防具且对其使用【杀】没有次数限制。若你没赢，你不能使用【杀】直到回合结束。

**Test Requirements**：一次出牌阶段拼点；胜则以source,target,turn_token绑定杀次数豁免/距离忽略/防具无效，没赢绑定全局禁用杀。；平局为没赢；对其他人次数正常；仅杀次数；禁酒含自救酒；虚拟酒材料；回合清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### jinjiu — 禁酒 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。你的【酒】视为【杀】。

来源键 `jinjiu`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：强制酒身份替换为普通杀，不提供酒自救；虚拟酒及装备区材料解释待语义核对。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rejinjiu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。锁定技，你的【酒】均视为【杀】。其他角色不能于你的回合内使用【酒】。当你受到酒【杀】的伤害时，你令此伤害-X（X为影响过此【杀】的伤害值的【酒】的数量）。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadejinjiu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。锁定技。你的【酒】的牌名均视为【杀】且点数视为K；你的回合内，其他角色不能使用【酒】。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `jinjiu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，你的【酒】均视为【杀】。

**Test Requirements**：强制酒身份替换为普通杀，不提供酒自救；虚拟酒及装备区材料解释待语义核对。；平局为没赢；对其他人次数正常；仅杀次数；禁酒含自救酒；虚拟酒材料；回合清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_xun_you

| Field | Definition |
| --- | --- |
| General ID | yj2012_xun_you |
| Chinese Name | 荀攸 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | qice, zhiyu；获得后才可用： |
| Chinese Skill Names | 奇策, 智愚 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | REACTION, TARGET, VIEWAS, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | VERY HIGH；必须专项策略：奇策全部手牌视为非延时锦囊；智愚公开整个手牌 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_OPTION, CHOOSE_PLAYERS, YES_NO |
| Test Requirements | 手牌0不可奇策；多材料颜色；南蛮/借刀/铁索目标；无懈响应；智愚摸后颜色；无来源 |


### qice — 奇策 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以将你的所有手牌（至少一张）当任意一张非延时锦囊牌使用。

来源键 `qice`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：成本为使用提交时全部非空手牌；选非延时锦囊definition及合法目标；整组VirtualCard保留材料列表并按普通牌结算。

**UI/Decision**：CHOOSE_OPTION, CHOOSE_PLAYERS。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reqice`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限X次（X为你的“奇策”数+1），你可以将所有手牌当做任意一张普通锦囊牌使用。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `qice`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以将所有的手牌（至少一张）当做任意一张普通锦囊牌使用。

**Test Requirements**：成本为使用提交时全部非空手牌；选非延时锦囊definition及合法目标；整组VirtualCard保留材料列表并按普通牌结算。；手牌0不可奇策；多材料颜色；南蛮/借刀/铁索目标；无懈响应；智愚摸后颜色；无来源；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zhiyu — 智愚 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你受到伤害后，你可以摸一张牌：若如此做，你展示所有手牌。若你的手牌均为同一颜色，伤害来源弃置一张手牌。

来源键 `zhiyu`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：伤后可摸1并公开当前全部手牌；非空且颜色全同令存活来源弃手牌1；公开展示不永久开启观察权。

**UI/Decision**：YES_NO, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rezhiyu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你受到伤害后，你可以摸一张牌，然后展示所有手牌，令伤害来源弃置一张手牌。若你展示的牌颜色均相同，你获得1枚“奇策”直到下回合结束且获得来源弃置的牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zhiyu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你受到伤害后，你可以摸一张牌，然后展示所有手牌。若颜色均相同，你令伤害来源弃置一张手牌。

**Test Requirements**：伤后可摸1并公开当前全部手牌；非空且颜色全同令存活来源弃手牌1；公开展示不永久开启观察权。；手牌0不可奇策；多材料颜色；南蛮/借刀/铁索目标；无懈响应；智愚摸后颜色；无来源；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_wang_yi

| Field | Definition |
| --- | --- |
| General ID | yj2012_wang_yi |
| Chinese Name | 王异 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | wei；当前runtime映射 wei |
| Gender | female |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | zhenlie, miji；获得后才可用： |
| Chinese Skill Names | 贞烈, 秘计 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择贞烈目标防御与秘计分牌，避免采用初版判定替换再混入后期秘计。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | DISTRIBUTE, DYING, HPREWRITE, TARGET, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：贞烈失去体力后目标无效与弃牌；秘计摸至多已损HP再分等量 |
| UI/Decision Requirements | CHOOSE_CARDS, CHOOSE_OPTION, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 成本濒死/死亡后剩余效果；延时锦囊不可贞烈；秘计分多角色；混旧手牌；不足牌堆 |


### zhenlie — 贞烈 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你成为其他角色的【杀】或非延时锦囊牌的目标后，你可以失去1点体力：若如此做，你弃置该角色的一张牌，此牌对你无效。

来源键 `zhenlie`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：杀/非延时锦囊被指定后可失去1HP；完成濒死后若仍存活则弃来源牌并令该牌对自己无效；Q08裁顺序。

**UI/Decision**：YES_NO, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `noszhenlie`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当你的判定牌生效前，你可以亮出牌堆顶的一张牌代替之。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `oldzhenlie`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。在你的判定牌生效前，你可以亮出牌堆顶的一张牌代替之。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zhenlie`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你成为其他角色使用【杀】或普通锦囊牌的目标后，你可以失去1点体力并令此牌对你无效，然后弃置对方一张牌。

**Test Requirements**：杀/非延时锦囊被指定后可失去1HP；完成濒死后若仍存活则弃来源牌并令该牌对自己无效；Q08裁顺序。；成本濒死/死亡后剩余效果；延时锦囊不可贞烈；秘计分多角色；混旧手牌；不足牌堆；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### miji — 秘计 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 结束阶段开始时，若你已受伤，你可以摸至多X张牌，然后将等量的手牌任意分配给其他角色。（X为你已损失的体力值）

来源键 `miji`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：结束阶段受伤可选n∈[0,已损HP]摸n，随后从当前手牌分配实际获得数量给其他人；每张一次归属。

**UI/Decision**：YES_NO, CHOOSE_OPTION, CHOOSE_CARDS, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosmiji`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。回合开始或结束阶段开始时，若你已受伤，你可以进行判定：若结果为黑色，你观看牌堆顶的X张牌然后将之交给一名角色。（X为你已损失的体力值）

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `oldmiji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。准备/结束阶段开始时，若你已受伤，你可以判定，若判定结果为黑色，你观看牌堆顶的X张牌（X为你已损失的体力值），然后将这些牌交给一名角色。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `miji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。结束阶段，若你已受伤，则可以摸X张牌，然后可以将等量的牌交给其他角色（X为你已损失的体力值）。

**Test Requirements**：结束阶段受伤可选n∈[0,已损HP]摸n，随后从当前手牌分配实际获得数量给其他人；每张一次归属。；成本濒死/死亡后剩余效果；延时锦囊不可贞烈；秘计分多角色；混旧手牌；不足牌堆；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_cao_zhang

| Field | Definition |
| --- | --- |
| General ID | yj2012_cao_zhang |
| Chinese Name | 曹彰 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | jiangchi；获得后才可用： |
| Chinese Skill Names | 将驰 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | SCOPE, TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | MEDIUM；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | CHOOSE_OPTION |
| Test Requirements | 少摸为0；杀响应决斗也禁；雷火虚拟杀；额外阶段同回合；结束清理 |


### jiangchi — 将驰 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 摸牌阶段，你可以选择一项：1.少摸一张牌，然后本回合，你使用【杀】无距离限制，你可以额外使用一张【杀】；2.额外摸一张牌，且你不能使用或打出【杀】，直到回合结束。

来源键 `jiangchi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：摸牌数修改并加turn-scoped限制；多摸禁止use与respond所有杀，少摸+1次数且不限距离；默认不修改。

**UI/Decision**：CHOOSE_OPTION。choice_labels：`{"default": "正常摸牌", "jiang": "多摸一张，本回合不能使用或打出杀", "chi": "少摸一张，本回合杀不限距离且次数加一"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinjiangchi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段开始时，你可选择：①摸一张牌。②摸两张牌，然后本回合内不能使用或打出【杀】。③弃置一张牌，然后本回合内可以多使用一张【杀】，且使用【杀】无距离限制。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `jiangchi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。摸牌阶段摸牌时，你可以选择一项：1、额外摸一张牌，若如此做，你不能使用或打出【杀】直到回合结束。 2、少摸一张牌，若如此做，你使用【杀】无距离限制且可以多使用一张【杀】直到回合结束。

**Test Requirements**：摸牌数修改并加turn-scoped限制；多摸禁止use与respond所有杀，少摸+1次数且不限距离；默认不修改。；少摸为0；杀响应决斗也禁；雷火虚拟杀；额外阶段同回合；结束清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_zhong_hui

| Field | Definition |
| --- | --- |
| General ID | yj2012_zhong_hui |
| Chinese Name | 钟会 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | quanji, zili；获得后才可用：paiyi |
| Chinese Skill Names | 权计, 自立, 排异 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | QUESTION Q01；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 此项等待人工确认，不能视为最终官方版本锁。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | MAXHP, OWNERSHIP, PILE, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：权计每点伤害摸一存权；自立觉醒获得排异 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_OPTION, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己 |


### quanji — 权计 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 每当你受到1点伤害后，你可以摸一张牌，然后将一张手牌置于武将牌上，称为“权”。每有一张“权”，你的手牌上限+1。

来源键 `quanji`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：受到每1点伤害可摸1并从当前手牌置1权；特殊牌区权可见性需Q07；持权数增加手牌上限。

**UI/Decision**：YES_NO, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosquanji`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。其他角色的回合开始时，你可以与该角色拼点：若你赢，该角色跳过准备阶段和判定阶段。

- A_EARLY_PROMO_ARCHIVE `nosquanji / noszhenggong / nosbaijiang / nosyexin / noszili / nospaiyi`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。早期钟会：权计拼点跳准备/判定，争功夺装备，拜将3装备觉醒到野心，4权自立觉醒到末阶段排异。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinquanji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。①当你受到1点伤害后，或其他角色不因你的赠予或交给而得到你的牌后，你可以摸一张牌，然后将一张手牌置于武将牌上，称为“权”。②你的手牌上限+X（X为“权”的数量）。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `quanji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你受到1点伤害后，你可以摸一张牌，然后将一张手牌置于武将牌上，称为“权”；你的手牌上限+X（X为“权”的数量）。

**Test Requirements**：受到每1点伤害可摸1并从当前手牌置1权；特殊牌区权可见性需Q07；持权数增加手牌上限。；两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zili — 自立 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 觉醒技。准备阶段开始时，若“权”大于或等于三张，你失去1点体力上限，摸两张牌或回复1点体力，然后获得“排异”（阶段技。你可以将一张“权”置入弃牌堆并选择一名角色：若如此做，该角色摸两张牌：若其手牌多于你，该角色受到1点伤害）。

来源键 `zili`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：准备阶段权≥3且未觉醒：减maxHP1，选择摸2/回HP1，然后授予排异来源zili；不得预先拥有排异。

**UI/Decision**：CHOOSE_OPTION。choice_labels：`{"draw": "摸牌", "recover": "回复体力"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `noszili`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。觉醒技。准备阶段开始时，若你的“权”大于或等于四张，你失去1点体力上限，然后获得“排异”（结束阶段开始时，你可以将一张“权”移动至一名角色的手牌、装备区（若该“权”为装备牌）或判定区（若该“权”为延时锦囊牌）：若该角色不是你，你摸一张牌）。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinzili`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。觉醒技。准备阶段，若你的“权”数大于2，则你回复1点体力并摸两张牌，减1点体力上限并获得〖排异〗。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zili`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。觉醒技，准备阶段开始时，若“权”的数量不小于3，你减1点体力上限，然后选择一项：1、回复1点体力；2、摸两张牌。然后你获得技能“排异”。

**Test Requirements**：准备阶段权≥3且未觉醒：减maxHP1，选择摸2/回HP1，然后授予排异来源zili；不得预先拥有排异。；两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### paiyi — 排异 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 阶段技。你可以将一张“权”置入弃牌堆并选择一名角色：若如此做，该角色摸两张牌：若其手牌多于你，该角色受到1点伤害。

来源键 `paiyi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCMPackage.lua)。

**机制语义**：仅自立授予后，每出牌阶段1次弃1权，目标摸2后若手牌>自己的手牌，对其伤害1；可选自己。

**UI/Decision**：CHOOSE_CARD, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nospaiyi`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。结束阶段开始时，你可以将一张“权”移动至一名角色的手牌、装备区（若该“权”为装备牌）或判定区（若该“权”为延时锦囊牌）：若该角色不是你，你摸一张牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinpaiyi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段每项各限一次，你可移去一张“权”并选择一项：①令一名角色摸X张牌。②对至多X名角色各造成1点伤害。（X为“权”数）

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `paiyi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以移去一张“权”并选择一名角色，令其摸两张牌，然后若其手牌数大于你，你对其造成1点伤害。

**Test Requirements**：仅自立授予后，每出牌阶段1次弃1权，目标摸2后若手牌>自己的手牌，对其伤害1；可选自己。；两点两次；权实体唯一位置；3权边界；觉醒一次；HP上限先降；排异摸后比手牌含自己；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_liao_hua

| Field | Definition |
| --- | --- |
| General ID | yj2012_liao_hua |
| Chinese Name | 廖化 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | dangxian, fuli；获得后才可用： |
| Chinese Skill Names | 当先, 伏枥 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | COUNTER, DYING, PHASE；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | LOW |
| AI Complexity | HIGH；必须专项策略：当先额外出牌阶段独立阶段次数；伏枥回复到存活势力数并翻面 |
| UI/Decision Requirements | YES_NO |
| Test Requirements | 背面回合是否当先候选待卡面裁定；两次出牌计数隔离；势力随化身变化；神按现行群 |


### dangxian — 当先 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。回合开始时，你执行一个额外的出牌阶段。

来源键 `dangxian`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：回合开始插入PLAY阶段，独立phase_token，后续正常PLAY使用次数独立；背面跳回合顺序Q08。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xindangxian`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，回合开始时，你执行一个额外的出牌阶段。此阶段开始时，你失去1点体力并从牌堆/弃牌堆中获得一张【杀】（若你已发动过〖伏枥〗，则可以不发动此效果）。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `dangxian`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，回合开始时，你执行一个额外的出牌阶段。

**Test Requirements**：回合开始插入PLAY阶段，独立phase_token，后续正常PLAY使用次数独立；背面跳回合顺序Q08。；背面回合是否当先候选待卡面裁定；两次出牌计数隔离；势力随化身变化；神按现行群；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### fuli — 伏枥 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 限定技。每当你处于濒死状态时，你可以将回复至X点体力，然后将武将牌翻面。（X为现存势力数）

来源键 `fuli`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：限定濒死可回复到min(存活有效势力种数,maxHP)，然后翻面；不是额外回合；失败救起继续濒死。

**UI/Decision**：YES_NO。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinfuli`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。限定技，当你处于濒死状态时，可以将体力回复至X点并将手牌摸至X张（X为场上势力数）。若X大于2，你翻面。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `fuli`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。限定技，当你处于濒死状态时，你可以将体力回复至与场上势力数相同，然后翻面。

**Test Requirements**：限定濒死可回复到min(存活有效势力种数,maxHP)，然后翻面；不是额外回合；失败救起继续濒死。；背面回合是否当先候选待卡面裁定；两次出牌计数隔离；势力随化身变化；神按现行群；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_guan_xing_zhang_bao

| Field | Definition |
| --- | --- |
| General ID | yj2012_guan_xing_zhang_bao |
| Chinese Name | 关兴张苞 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | fuhun；获得后才可用： |
| Chinese Skill Names | 父魂 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择两手牌父魂普通杀造成伤害授予组合技能，避免初版翻两牌随机获得技能。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 4 |
| Engine Dependencies | OWNERSHIP, SCOPE, VIEWAS；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：父魂两手牌普通杀；出牌阶段造成伤害获武圣咆哮到回合末 |
| UI/Decision Requirements | CHOOSE_CARDS, RESPOND_WITH_CARD, USE_CARD |
| Test Requirements | 非出牌阶段不获；伤害被防不获；一阶段多次幂等；已有武圣不误移除；临时来源不夺 |


### fuhun — 父魂 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 你可以将两张手牌当普通【杀】使用或打出。每当你于出牌阶段内以此法使用【杀】造成伤害后，你拥有“武圣”、“咆哮”，直到回合结束。

来源键 `fuhun`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：两手牌普通杀ViewAs；该牌于PLAY造成实际伤害后授予wusheng,paoxiao到回合末，按来源回收。

**UI/Decision**：CHOOSE_CARDS, USE_CARD, RESPOND_WITH_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosfuhun`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。摸牌阶段开始时，你可以放弃摸牌，亮出牌堆顶的两张牌并获得之：若亮出的牌不为同一颜色，你拥有“武圣”、“咆哮”，直到回合结束。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `old_fuhun`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。摸牌阶段开始时，你可以放弃摸牌，改为从牌堆顶亮出两张牌并获得之，若亮出的牌颜色不同，你获得〖武圣〗和〖咆哮〗直到回合结束。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `fuhun`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。你可以将两张手牌当做【杀】使用或打出；当你于出牌阶段以此法使用的【杀】造成伤害后，你获得〖武圣〗和〖咆哮〗直到回合结束。

**Test Requirements**：两手牌普通杀ViewAs；该牌于PLAY造成实际伤害后授予wusheng,paoxiao到回合末，按来源回收。；非出牌阶段不获；伤害被防不获；一阶段多次幂等；已有武圣不误移除；临时来源不夺；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_ma_dai

| Field | Definition |
| --- | --- |
| General ID | yj2012_ma_dai |
| Chinese Name | 马岱 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | mashu, qianxi；获得后才可用： |
| Chinese Skill Names | 马术, 潜袭 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择判定限制手牌颜色的修订，不采用不可回复的早期体力上限削减，也不带新版摸弃奖励。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | JUDGMENT, SCOPE, TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：马术复用；潜袭判定后距离1颜色手牌使用/打出封锁 |
| UI/Decision Requirements | CHOOSE_PLAYER, YES_NO |
| Test Requirements | 只封手牌不封装备材料；有效颜色红颜；虚拟材料来源；判定改判；回合末解除；不减上限 |


### mashu — 马术 (REUSE)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。你与其他角色的距离-1。

来源键 `mashu`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/StandardGeneralPackage.lua)。

**机制语义**：语义复用已存在mashu，但当前distance.py直接查角色原生技能；动态获得/失效须接统一ownership。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：语义复用已存在mashu，但当前distance.py直接查角色原生技能；动态获得/失效须接统一ownership。；只封手牌不封装备材料；有效颜色红颜；虚拟材料来源；判定改判；回合末解除；不减上限；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### qianxi — 潜袭 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 准备阶段开始时，你可以进行判定：若如此做，你令一名距离1的角色不能使用或打出与判定牌颜色相同的手牌，直到回合结束。

来源键 `qianxi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：准备阶段判定，选有效距离1角色；本回合按判定最终颜色禁止其手牌使用/打出，逐材料按区域检查。

**UI/Decision**：YES_NO, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosqianxi`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当你使用【杀】对距离1的目标角色造成伤害时，你可以进行判定：若结果不为红桃，防止此伤害，该角色失去1点体力上限。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reqianxi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。准备阶段开始时，你可摸一张牌，然后弃置一张牌并选择一名距离为1的其他角色。该角色于本回合内：{不能使用或打出与此牌颜色相同的牌，且其装备区内与此牌颜色相同的防具牌无效，且当其回复体力时，你摸两张牌。}

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `oldqianxi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你使用【杀】对距离为1的目标角色造成伤害时，你可以进行一次判定，若判定结果不为红桃，你防止此伤害，令其减1点体力上限。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `qianxi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。准备阶段，你可以摸一张牌，并弃置一张牌，然后令一名距离为1的角色不能使用或打出与你弃置的牌颜色相同的手牌直到回合结束。

**Test Requirements**：准备阶段判定，选有效距离1角色；本回合按判定最终颜色禁止其手牌使用/打出，逐材料按区域检查。；只封手牌不封装备材料；有效颜色红颜；虚拟材料来源；判定改判；回合末解除；不减上限；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_bu_lianshi

| Field | Definition |
| --- | --- |
| General ID | yj2012_bu_lianshi |
| Chinese Name | 步练师 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | wu；当前runtime映射 wu |
| Gender | female |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | anxu, zhuiyi；获得后才可用： |
| Chinese Skill Names | 安恤, 追忆 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | DEATH, MOVE, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：安恤少牌者选多牌者未知手牌并公开获得；追忆排除杀手 |
| UI/Decision Requirements | CHOOSE_OPTION, CHOOSE_PLAYER, CHOOSE_PLAYERS, YES_NO |
| Test Requirements | 同手牌数不可；不选自己；黑桃不摸；选择者不是步练师；死亡补益；无杀手不排除 |


### anxu — 安恤 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以选择手牌数不等的两名其他角色：若如此做，手牌较少的角色正面朝上获得另一名角色的一张手牌。若此牌不为黑桃，你摸一张牌。

来源键 `anxu`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：一次出牌阶段选两其他人手牌不同，少者选多者背面手牌公开获得，非黑桃步练师摸1。

**UI/Decision**：CHOOSE_PLAYERS, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `dcanxu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限一次，你可以选择两名手牌数不同的其他角色，令其中手牌少的角色获得手牌多的角色的一张手牌并展示之。然后若此牌不为黑桃，则你摸一张牌；若这两名角色手牌数相等，则你回复1点体力。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `old_anxu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以选择两名手牌数不同的其他角色，令其中手牌少的角色获得手牌多的角色的一张手牌并展示之。然后若此牌不为黑桃，则你摸一张牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `anxu`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以选择两名手牌数不同的其他角色，令其中手牌多的角色将一张手牌交给手牌少的角色，然后若这两名角色手牌数相等，你摸一张牌或回复1点体力。

**Test Requirements**：一次出牌阶段选两其他人手牌不同，少者选多者背面手牌公开获得，非黑桃步练师摸1。；同手牌数不可；不选自己；黑桃不摸；选择者不是步练师；死亡补益；无杀手不排除；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zhuiyi — 追忆 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 你死亡时，你可以令一名其他角色（除杀死你的角色）摸三张牌并回复1点体力。

来源键 `zhuiyi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：死亡后允许该技能专用最后选择，目标其他存活者排除杀手，摸3再恢复1；无来源死亡不排除。

**UI/Decision**：YES_NO, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `dczhuiyi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你死亡时，你可以令一名不为击杀者的其他角色摸X张牌（X为存活角色数），然后其回复1点体力。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zhuiyi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你死亡时，你可以令一名其他角色（杀死你的角色除外）摸三张牌，然后其回复1点体力。

**Test Requirements**：死亡后允许该技能专用最后选择，目标其他存活者排除杀手，摸3再恢复1；无来源死亡不排除。；同手牌数不可；不选自己；黑桃不摸；选择者不是步练师；死亡补益；无杀手不排除；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_cheng_pu

| Field | Definition |
| --- | --- |
| General ID | yj2012_cheng_pu |
| Chinese Name | 程普 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | wu；当前runtime映射 wu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | lihuo, chunlao；获得后才可用： |
| Chinese Skill Names | 疠火, 醇醪 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | DYING, PILE, REACTION, TARGET, VIEWAS；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：疠火普通转火、多目标；一次杀有伤害后失去1HP；醇作濒死者酒 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_CARDS, CHOOSE_OPTION, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 铁索连伤只扣一次；原生火杀不扣HP；醇为空才补；多次救援；完杀；移去醇不是手牌酒 |


### lihuo — 疠火 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 你可以将一张普通【杀】当火【杀】使用。你以此法使用【杀】结算后，若此【杀】造成了伤害，你失去1点体力。你使用火【杀】可以额外选择一名目标。

来源键 `lihuo`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：普通杀可转火；所有火杀可增一个目标；只转换杀造成过伤害则整牌结算结束扣HP1一次。

**UI/Decision**：CHOOSE_OPTION, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadelihuo`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你声明使用普【杀】后，你可以将此【杀】改为火【杀】。当你使用火【杀】选择目标时，可以选择一个额外目标。你使用的火【杀】结算完成后，若此【杀】的目标数大于1且你因此【杀】造成过伤害，则你失去1点体力。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `ollihuo`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。你使用普通的【杀】可以改为火【杀】，若此【杀】造成过伤害，你失去1点体力；你使用火【杀】可以多选择一个目标。你每回合使用的第一张牌如果是【杀】，则此【杀】结算完毕后可置于你的武将牌上。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `lihuo`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你声明使用普通【杀】后，你可以将此【杀】改为火【杀】。若以此法使用的【杀】造成了伤害，则此【杀】结算后你失去1点体力；你使用火【杀】选择目标后，可以额外指定一个目标。

**Test Requirements**：普通杀可转火；所有火杀可增一个目标；只转换杀造成过伤害则整牌结算结束扣HP1一次。；铁索连伤只扣一次；原生火杀不扣HP；醇为空才补；多次救援；完杀；移去醇不是手牌酒；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### chunlao — 醇醪 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 结束阶段开始时，若你的武将牌上没有“醇”，你可以将至少一张【杀】置于武将牌上，称为“醇”。每当一名角色处于濒死状态时，你可以将一张“醇”置入弃牌堆，视为该角色使用一张【酒】。

来源键 `chunlao`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：结束阶段没有醇时可存至少一杀；濒死时消耗一醇视为濒死者用酒，通过标准酒自救与濒死管线。

**UI/Decision**：YES_NO, CHOOSE_CARDS, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rechunlao`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段结束时，若你没有“醇”，你可以将至少一张【杀】置于你的武将牌上，称为“醇”。当一名角色处于濒死状态时，你可以移去一张“醇”，视为该角色使用一张【酒】，然后若此“醇”的属性为：火，你回复1点体力、雷，你摸两张牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadechunlao`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。你可以对其他角色使用【酒（使用方法②）】。当你需要使用【酒】时，若你的武将牌未横置，则你可以将武将牌横置，然后视为使用【酒】。当你受到或造成伤害后，若伤害值大于1且你的武将牌横置，则你可以重置武将牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `chunlao`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。结束阶段开始时，若你没有“醇”，你可以将至少一张【杀】置于你的武将牌上，称为“醇”。当一名角色处于濒死状态时，你可以移去一张“醇”，视为该角色使用一张【酒】。

**Test Requirements**：结束阶段没有醇时可存至少一杀；濒死时消耗一醇视为濒死者用酒，通过标准酒自救与濒死管线。；铁索连伤只扣一次；原生火杀不扣HP；醇为空才补；多次救援；完杀；移去醇不是手牌酒；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_han_dang

| Field | Definition |
| --- | --- |
| General ID | yj2012_han_dang |
| Chinese Name | 韩当 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | wu；当前runtime映射 wu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | gongqi, jiefan；获得后才可用： |
| Chinese Skill Names | 弓骑, 解烦 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择一次无限攻击范围与限定解烦，避开旧濒死杀转桃的强依赖和后期首轮恢复限定技。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | SCOPE, SEQUENCE, TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：弓骑弃牌换无限范围；装备额外弃牌；解烦一次范围内依次弃武器或摸牌 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_OPTION, CHOOSE_PLAYER |
| Test Requirements | 攻击范围非距离；武器可来自手/装备；每次选择后重检存活；无武器摸；限定不可重复 |


### gongqi — 弓骑 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以弃置一张牌：若如此做，本回合你的攻击范围无限；若此牌为装备牌，你可以弃置一名其他角色的一张牌。

来源键 `gongqi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：一次出牌阶段弃任意一牌，本回合攻击范围无限，若装备可再弃其他人牌1；不改通用距离。

**UI/Decision**：CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosgongqi`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。你可以将一张装备牌当【杀】使用或打出。你以此法使用的【杀】无距离限制。

**Test Requirements**：一次出牌阶段弃任意一牌，本回合攻击范围无限，若装备可再弃其他人牌1；不改通用距离。；攻击范围非距离；武器可来自手/装备；每次选择后重检存活；无武器摸；限定不可重复；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### jiefan — 解烦 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 限定技。出牌阶段，你可以选择一名角色，然后攻击范围内包含该角色的所有角色选择一项：弃置一张武器牌，或令该角色摸一张牌。

来源键 `jiefan`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：限定PLAY选角色；按当前席位序依次询问攻击范围含目标者，弃一武器（手或装备）否则目标摸1。

**UI/Decision**：CHOOSE_PLAYER, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosjiefan`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。你的回合外，每当一名角色处于濒死状态时，你可以对当前回合角色使用一张【杀】：若此【杀】造成伤害，造成伤害时防止此伤害，视为对该濒死角色使用了一张【桃】。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinjiefan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。限定技，出牌阶段，你可以选择一名角色，令攻击范围内含有该角色的所有角色依次选择一项：1.弃置一张武器牌；2.令其摸一张牌。然后若游戏轮数为1，则你于此回合结束时恢复此技能。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `jiefan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。限定技，出牌阶段，你可以选择一名角色，令攻击范围内含有该角色的所有角色依次选择一项：1.弃置一张武器牌；2.令其摸一张牌。

**Test Requirements**：限定PLAY选角色；按当前席位序依次询问攻击范围含目标者，弃一武器（手或装备）否则目标摸1。；攻击范围非距离；武器可来自手/装备；每次选择后重检存活；无武器摸；限定不可重复；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_liu_biao

| Field | Definition |
| --- | --- |
| General ID | yj2012_liu_biao |
| Chinese Name | 刘表 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | qun；当前runtime映射 qun |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | zishou, zongshi；获得后才可用： |
| Chinese Skill Names | 自守, 宗室 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | QUESTION Q03；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 此项等待人工确认，不能视为最终官方版本锁。 |
| Estimated Power | C；BALANCE RISK：下限过弱；不要自行加强 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | PHASE, SCOPE；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | MEDIUM；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | YES_NO |
| Test Requirements | 满HP不自守；势力种数不是人数；神映射群；化身切换影响；不同原版修订另列 |


### zishou — 自守 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 摸牌阶段，若你已受伤，你可以额外摸X张牌，然后跳过出牌阶段。（X为你已损失的体力值）

来源键 `zishou`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：受伤摸牌阶段可增已损HP摸牌，并skip_play；非按势力数候选，禁止拼接新版。

**UI/Decision**：YES_NO。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rezishou`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。摸牌阶段，你可以多摸X张牌（X为存活势力数）。若如此做，本回合你对其他角色造成伤害时，防止此伤害。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadezishou`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。摸牌阶段，你可以多摸X张牌（X为存活势力数）；然后本回合你对其他角色造成伤害时，防止此伤害。结束阶段，若你本回合没有使用牌指定其他角色为目标，你可以弃置任意张花色不同的手牌，然后摸等量的牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zishou`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。摸牌阶段，你可以额外摸X张牌（X为场上势力数）。然后你于本回合的出牌阶段内使用的牌不能指定其他角色为目标。

**Test Requirements**：受伤摸牌阶段可增已损HP摸牌，并skip_play；非按势力数候选，禁止拼接新版。；满HP不自守；势力种数不是人数；神映射群；化身切换影响；不同原版修订另列；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zongshi — 宗室 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 锁定技。你的手牌上限+X。（X为现存势力数）

来源键 `zongshi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：锁定手牌上限+存活有效势力种数，化身势力经SkillRegistry.faction；神当前映射群不自加新势力。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rezongshi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。锁定技，你的手牌上限+X（X为存活势力数）。准备阶段，若你的手牌数大于体力值，则你本回合内使用【杀】无次数限制。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadezongshi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。锁定技，你的手牌上限+X（X为存活势力数）。你的回合外，若你的手牌数大于等于手牌上限，则当你成为延时类锦囊牌或无颜色的牌的目标后，你令此牌对你无效。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zongshi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，你的手牌上限+X（X为场上现存势力数）。

**Test Requirements**：锁定手牌上限+存活有效势力种数，化身势力经SkillRegistry.faction；神当前映射群不自加新势力。；满HP不自守；势力种数不是人数；神映射群；化身切换影响；不同原版修订另列；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2012_hua_xiong

| Field | Definition |
| --- | --- |
| General ID | yj2012_hua_xiong |
| Chinese Name | 华雄 |
| Expansion | yj2012 / 历史来源 yj2012 |
| Year | 2012 |
| Faction | qun；当前runtime映射 qun |
| Gender | male |
| Base HP | 6 |
| Max HP | 6 |
| Lord Skill? | False |
| Skill IDs | shiyong；获得后才可用： |
| Chinese Skill Names | 恃勇 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | C；BALANCE RISK：下限过弱；不要自行加强 |
| Implementation Complexity | Tier 1 |
| Engine Dependencies | MAXHP, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | LOW；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | 无需主动请求 |
| Test Requirements | 红酒杀仅一次；黑酒杀一次；多点仅一次；上限0死亡；无体力流失触发 |


### shiyong — 恃勇 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 锁定技。每当你受到一次红色【杀】或【酒】【杀】的伤害后，你失去1点体力上限。

来源键 `shiyong`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2012Package.lua)。

**机制语义**：实际红色杀或带wine标签杀伤后maxHP-1，每次伤害一次；红且酒不重复。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `shiyong`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，当你受到一次红色【杀】或【酒】【杀】造成的伤害后，须减1点体力上限。

**Test Requirements**：实际红色杀或带wine标签杀伤后maxHP-1，每次伤害一次；红且酒不重复。；红酒杀仅一次；黑酒杀一次；多点仅一次；上限0死亡；无体力流失触发；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_cao_chong

| Field | Definition |
| --- | --- |
| General ID | yj2013_cao_chong |
| Chinese Name | 曹冲 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | chengxiang, renxin；获得后才可用： |
| Chinese Skill Names | 称象, 仁心 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择称象≤13与弃装备防伤仁心，保持明确伤前救援；不混初版<13或全手牌濒死救。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | HPREWRITE, MOVE, SUBSET；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：称象四张总点数≤13非空子集；仁心HP1其他人伤前翻面弃装备防伤 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_CARDS, YES_NO |
| Test Requirements | 和=13允许14拒绝；装备在手或装备区；成本翻面顺序；零装备；多点伤害整体防止 |


### chengxiang — 称象 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你受到伤害后，你可以亮出牌堆顶的四张牌，然后获得其中至少一张点数之和小于或等于13的牌，并将其余的牌置入弃牌堆。

来源键 `chengxiang`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：伤后公开顶4，选择非空子集且rank总和≤13；选中获得余牌弃置，服务端计算不是仅计数检查。

**UI/Decision**：YES_NO, CHOOSE_CARDS。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `noschengxiang`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当你受到伤害后，你可以亮出牌堆顶的四张牌，然后获得其中至少一张点数之和小于13的牌，并将其余的牌置入弃牌堆。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rechengxiang`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你受到伤害后，你可以亮出牌堆顶的四张牌。然后获得其中任意数量点数之和不大于13的牌。若你得到的牌点数之和为13，你复原武将牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `oldchengxiang`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你受到伤害后，你可以亮出牌堆顶的四张牌。然后获得其中任意数量点数之和不大于12的牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `chengxiang`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你受到伤害后，你可以亮出牌堆顶的四张牌。然后获得其中任意数量点数之和不大于13的牌。

**Test Requirements**：伤后公开顶4，选择非空子集且rank总和≤13；选中获得余牌弃置，服务端计算不是仅计数检查。；和=13允许14拒绝；装备在手或装备区；成本翻面顺序；零装备；多点伤害整体防止；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### renxin — 仁心 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当一名体力值为1的其他角色受到伤害时，你可以将武将牌翻面并弃置一张装备牌：若如此做，防止此伤害。

来源键 `renxin`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：别人HP恰为1伤前可翻面、弃装备牌防整次伤害；费用可来自手或装备，所有移动副作用正常触发。

**UI/Decision**：YES_NO, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosrenxin`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当一名其他角色处于濒死状态时，若你有手牌，你可以将武将牌翻面并将所有手牌交给该角色：若如此做，该角色回复1点体力。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `oldrenxin`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。其他角色进入濒死状态时，你可以将所有手牌交给该角色并翻面，然后该角色回复1点体力。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `renxin`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当体力值为1的一名其他角色受到伤害时，你可以将武将牌翻面并弃置一张装备牌，然后防止此伤害。

**Test Requirements**：别人HP恰为1伤前可翻面、弃装备牌防整次伤害；费用可来自手或装备，所有移动副作用正常触发。；和=13允许14拒绝；装备在手或装备区；成本翻面顺序；零装备；多点伤害整体防止；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_guo_huai

| Field | Definition |
| --- | --- |
| General ID | yj2013_guo_huai |
| Chinese Name | 郭淮 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | jingce；获得后才可用： |
| Chinese Skill Names | 精策 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 1 |
| Engine Dependencies | COUNTER, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | LOW；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | YES_NO |
| Test Requirements | 打出不算使用；虚拟牌算一张；当先使用纳入回合；HP变化；不是结束阶段摸 |


### jingce — 精策 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 出牌阶段结束时，若你本回合已使用的牌数大于或等于你的体力值，你可以摸两张牌。

来源键 `jingce`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：每次PLAY结束时统计当前turn_token CardUsedEvent数量≥当前HP则可摸2；response不计，虚拟材料不多计。

**UI/Decision**：YES_NO。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `decadejingce`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。结束阶段，若你本回合使用过的牌数不小于你的体力值，则你可执行一个摸牌阶段或出牌阶段；若这些牌包含的花色数也不小于你的体力值，则你将“或”改为“并”。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinjingce`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。结束阶段，若你本回合使用的牌数量大于或等于你的当前体力值，你可以摸两张牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rejingce`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你于一回合内首次使用某种花色的手牌时，你的手牌上限+1。出牌阶段结束时，你可以摸X张牌（X为你本阶段内使用过的牌的类型数）。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `jingce`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段结束时，若你本回合使用的牌数量大于或等于你的当前体力值，你可以摸两张牌。

**Test Requirements**：每次PLAY结束时统计当前turn_token CardUsedEvent数量≥当前HP则可摸2；response不计，虚拟材料不多计。；打出不算使用；虚拟牌算一张；当先使用纳入回合；HP变化；不是结束阶段摸；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_man_chong

| Field | Definition |
| --- | --- |
| General ID | yj2013_man_chong |
| Chinese Name | 满宠 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | wei；当前runtime映射 wei |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | junxing, yuce；获得后才可用： |
| Chinese Skill Names | 峻刑, 御策 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | CATEGORY, SEQUENCE, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：峻刑多牌类型补集；御策公开一牌来源弃异类型否则回复 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_CARDS, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 基本/锦囊/装备三类延时属锦囊；三类全弃对方无法响应；御策无来源不回复；伤害濒死先救 |


### junxing — 峻刑 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以弃置任意数量的手牌并选择一名其他角色：若如此做，该角色须弃置一张与你弃置的牌类型均不同的手牌，否则将武将牌翻面并摸X张牌。（X为你弃置的牌的数量）

来源键 `junxing`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：一次PLAY至少1手牌弃置，按三大类型集计算补集，对方弃该补集类型手牌1，否则翻面摸成本张数。

**UI/Decision**：CHOOSE_CARDS, CHOOSE_PLAYER, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rejunxing`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限一次，你可以弃置任意张手牌并选择一名其他角色。该角色选择一项：1.弃置X张牌并失去1点体力。2.翻面并摸X张牌。（X为你弃置的牌数）

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinjunxing`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以弃置至少一张手牌并选择一名其他角色，该角色需弃置一张与你弃置的牌类别均不同的手牌，否则其先将其武将牌翻面，然后将手牌摸至四张。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `junxing`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以弃置至少一张手牌并选择一名其他角色，该角色需弃置一张与你弃置的牌类别均不同的手牌，否则其先将其武将牌翻面再摸X张牌（X为你以此法弃置的手牌数量）。

**Test Requirements**：一次PLAY至少1手牌弃置，按三大类型集计算补集，对方弃该补集类型手牌1，否则翻面摸成本张数。；基本/锦囊/装备三类延时属锦囊；三类全弃对方无法响应；御策无来源不回复；伤害濒死先救；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### yuce — 御策 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你受到伤害后，你可以展示一张手牌：若如此做且此伤害有来源，伤害来源须弃置一张与此牌类型不同的手牌，否则你回复1点体力。

来源键 `yuce`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：伤后可展示手牌1；有来源才请求来源弃一不同大类型手牌，否则受伤者回复1。

**UI/Decision**：YES_NO, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `yuce`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你受到伤害后，你可以展示一张手牌，并令伤害来源选择一项：弃置一张与此牌类型不同的手牌，或令你回复1点体力。

**Test Requirements**：伤后可展示手牌1；有来源才请求来源弃一不同大类型手牌，否则受伤者回复1。；基本/锦囊/装备三类延时属锦囊；三类全弃对方无法响应；御策无来源不回复；伤害濒死先救；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_guan_ping

| Field | Definition |
| --- | --- |
| General ID | yj2013_guan_ping |
| Chinese Name | 关平 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | longyin；获得后才可用： |
| Chinese Skill Names | 龙吟 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | COUNTER, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | LOW |
| AI Complexity | HIGH；必须专项策略：任意角色出牌用杀时弃一牌使本杀不计次数，红杀摸1 |
| UI/Decision Requirements | CHOOSE_CARD, YES_NO |
| Test Requirements | 火雷颜色；先合法用杀后龙吟不能先突破额度；一次杀多目标只触发一次；多关平叠次数不可负 |


### longyin — 龙吟 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当一名角色于出牌阶段内使用【杀】时，你可以弃置一张牌：若如此做，此【杀】不计入次数限制，若此【杀】为红色，你摸一张牌。

来源键 `longyin`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：PLAY合法使用杀时可付一牌，撤销本杀quota计入一次，红色则摸1；多角色发动不重复扣quota。

**UI/Decision**：YES_NO, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `relongyin`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当一名角色于其出牌阶段内使用【杀】时，你可弃置一张牌令此【杀】不计入出牌阶段使用次数。若此【杀】为红色，则你摸一张牌；若你以此法弃置的牌与此【杀】点数相同，则你重置“竭忠”。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `longyin`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当一名角色于其出牌阶段内使用【杀】时，你可弃置一张牌令此【杀】不计入出牌阶段使用次数，若此【杀】为红色，你摸一张牌。

**Test Requirements**：PLAY合法使用杀时可付一牌，撤销本杀quota计入一次，红色则摸1；多角色发动不重复扣quota。；火雷颜色；先合法用杀后龙吟不能先突破额度；一次杀多目标只触发一次；多关平叠次数不可负；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_jian_yong

| Field | Definition |
| --- | --- |
| General ID | yj2013_jian_yong |
| Chinese Name | 简雍 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | qiaoshui, zongshi_jianyong；获得后才可用： |
| Chinese Skill Names | 巧说, 纵适 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | MOVE, PINDIAN, SCOPE, TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | VERY HIGH；必须专项策略：巧说胜下一张基本/非延时锦囊加减目标；纵适获拼点牌 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_OPTION, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 平局没赢；延时锦囊失败禁用；单目标不能减为0；无距离但保留其他限制；借刀成对目标；牌已被取 |


### qiaoshui — 巧说 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 出牌阶段开始时，你可以与一名其他角色拼点：若你赢，本回合你使用的下一张基本牌或非延时锦囊牌可以增加一个额外目标（无距离限制）或减少一名目标（若原有至少两名目标）；若你没赢，你不能使用锦囊牌，直到回合结束。

来源键 `qiaoshui`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：PLAY开始拼点；胜利下一张基本/非延时锦囊可加一目标（忽略距离）/原有≥2减一；失败禁锦囊到回合末。

**UI/Decision**：YES_NO, CHOOSE_PLAYER, CHOOSE_CARD, CHOOSE_OPTION。choice_labels：`{"add": "增加一名目标", "remove": "减少一名目标", "keep": "保留原目标"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reqiaoshui`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段，你可与一名其他角色拼点。若你赢，你本回合使用下一张基本牌或普通锦囊牌时，可以为此牌增加或减少一个目标；若你没赢，你结束出牌阶段且本回合内锦囊牌不计入手牌上限。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `qiaoshui`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段开始时，你可与一名其他角色拼点。若你赢，你本回合使用下一张基本牌或普通锦囊牌时，可以为此牌增加或减少一个目标；若你没赢，你不能使用锦囊牌直到回合结束。

**Test Requirements**：PLAY开始拼点；胜利下一张基本/非延时锦囊可加一目标（忽略距离）/原有≥2减一；失败禁锦囊到回合末。；平局没赢；延时锦囊失败禁用；单目标不能减为0；无距离但保留其他限制；借刀成对目标；牌已被取；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zongshi_jianyong — 纵适 (SAME NAME / DIFFERENT SEMANTICS)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你拼点赢，你可以获得对方的拼点牌。每当你拼点没赢，你可以获得你的拼点牌。

来源键 `zongshih`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：纵适，拼点胜取对方牌，未胜取自己牌；需拼点揭示结果/弃置前取得窗口，不能等牌被他人获得再取。

**UI/Decision**：YES_NO。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：纵适，拼点胜取对方牌，未胜取自己牌；需拼点揭示结果/弃置前取得窗口，不能等牌被他人获得再取。；平局没赢；延时锦囊失败禁用；单目标不能减为0；无距离但保留其他限制；借刀成对目标；牌已被取；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_liu_feng

| Field | Definition |
| --- | --- |
| General ID | yj2013_liu_feng |
| Chinese Name | 刘封 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | shu；当前runtime映射 shu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | xiansi；获得后才可用： |
| Chinese Skill Names | 陷嗣 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | AUTHUSE, PILE, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | HIGH；必须专项策略：陷嗣1-2人各一牌公开逆；别人花两逆视为对刘封杀计次数 |
| UI/Decision Requirements | CHOOSE_OPTION, CHOOSE_PLAYERS, USE_CARD, YES_NO |
| Test Requirements | 可取自己按候选文本；手牌背面选择；两个逆不足无选项；杀范围与享乐/距离；移区触发；主人死清理 |


### xiansi — 陷嗣 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 准备阶段开始时，你可以将一至两名角色的各一张牌置于你的武将牌上，称为“逆”。其他角色可以将两张“逆”置入弃牌堆，视为对你使用一张【杀】（计入次数限制）。

来源键 `xiansi`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：准备阶段从1-2角色各取1手/装备牌置公开逆；其他人合法用杀窗口可消耗两逆视为对拥有者用普通杀且计次数。

**UI/Decision**：YES_NO, CHOOSE_PLAYERS, CHOOSE_OPTION, USE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rexiansi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。①准备阶段开始时，你可以将一至两名角色的各一张牌置于你的武将牌上，称为“逆”。②当一名角色需要对你使用【杀】时，其可以移去两张“逆”，然后视为对你使用一张【杀】。③若你的“逆”数大于体力值，则你可以移去一张“逆”并视为使用一张【杀】。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `xiansi`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。准备阶段开始时，你可以将一至两名角色的各一张牌置于你的武将牌上，称为“逆”；当一名角色需要对你使用【杀】时，其可以移去两张“逆”，然后视为对你使用了一张【杀】。

**Test Requirements**：准备阶段从1-2角色各取1手/装备牌置公开逆；其他人合法用杀窗口可消耗两逆视为对拥有者用普通杀且计次数。；可取自己按候选文本；手牌背面选择；两个逆不足无选项；杀范围与享乐/距离；移区触发；主人死清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_pan_zhang_ma_zhong

| Field | Definition |
| --- | --- |
| General ID | yj2013_pan_zhang_ma_zhong |
| Chinese Name | 潘璋马忠 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | wu；当前runtime映射 wu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | duodao, anjian；获得后才可用： |
| Chinese Skill Names | 夺刀, 暗箭 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 2 |
| Engine Dependencies | MOVE, REACTION, TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | LOW |
| Projection Risk | MEDIUM |
| AI Complexity | MEDIUM；可先通用heuristic：牌差、存活、身份收益、伤害成本；禁止随机发动 |
| UI/Decision Requirements | CHOOSE_CARD, YES_NO |
| Test Requirements | 虚拟杀；无来源/无武器；暗箭方向不能写反；武器变化重算；铁索继发不再增伤 |


### duodao — 夺刀 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你受到【杀】的伤害后，你可以弃置一张牌：若如此做，你获得伤害来源装备区的武器牌。

来源键 `duodao`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：杀伤后付一牌获得来源装备区武器（仍在该位置）；无来源/武器先不提供无意义发动。

**UI/Decision**：YES_NO, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reduodao`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你成为【杀】的目标后，你可以弃置一张牌。然后你获得此【杀】使用者装备区里的武器牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `duodao`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你受到【杀】造成的伤害后，你可以弃置一张牌，然后获得伤害来源装备区里的武器牌。

**Test Requirements**：杀伤后付一牌获得来源装备区武器（仍在该位置）；无来源/武器先不提供无意义发动。；虚拟杀；无来源/无武器；暗箭方向不能写反；武器变化重算；铁索继发不再增伤；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### anjian — 暗箭 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你使用【杀】对目标角色造成伤害时，若你不在其攻击范围内，此伤害+1。

来源键 `anjian`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：杀对目标伤害计算时source不在target攻击范围内则+1；继发铁索伤害不重新触发目标规则。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reanjian`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，当你使用【杀】指定目标后，若你不在其攻击范围内，则此【杀】伤害+1且无视其防具。若其因执行此【杀】的效果受到伤害而进入濒死状态，则其不能使用【桃】直到此濒死事件结算结束。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `anjian`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。锁定技，当你使用【杀】对目标角色造成伤害时，若你不在其攻击范围内，则此【杀】伤害+1。

**Test Requirements**：杀对目标伤害计算时source不在target攻击范围内则+1；继发铁索伤害不重新触发目标规则。；虚拟杀；无来源/无武器；暗箭方向不能写反；武器变化重算；铁索继发不再增伤；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_yu_fan

| Field | Definition |
| --- | --- |
| General ID | yj2013_yu_fan |
| Chinese Name | 虞翻 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | wu；当前runtime映射 wu |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | zongxuan, zhiyan；获得后才可用： |
| Chinese Skill Names | 纵玄, 直言 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | AUTHUSE, MOVE, ORDER, REACTION；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | VERY HIGH；必须专项策略：纵玄弃置牌重排顶；直言摸后公开装备回复并使用 |
| UI/Decision Requirements | CHOOSE_CARDS, CHOOSE_OPTION, CHOOSE_PLAYER, USE_CARD, YES_NO |
| Test Requirements | 已被落英获得不再置顶；选择顺序定义；直言装备槽替换触发；回合外装备使用；用前死亡 |


### zongxuan — 纵玄 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 当你的牌因弃置而置入弃牌堆时，你可以将其中至少一张牌依次置于牌堆顶。

来源键 `zongxuan`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：自己的弃置批次中仍在弃牌堆的牌可非空排序置顶，服务端保存ordered_card_ids与批次锁。

**UI/Decision**：YES_NO, CHOOSE_CARDS, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinzongxuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你的牌因弃置而进入弃牌堆后，你可将其中的任意张牌置于牌堆顶。若剩余的牌中有锦囊牌，则你可以令一名其他角色获得其中的一张。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zongxuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你的牌因弃置而进入弃牌堆后，你可以将其按任意顺序置于牌堆顶。

**Test Requirements**：自己的弃置批次中仍在弃牌堆的牌可非空排序置顶，服务端保存ordered_card_ids与批次锁。；已被落英获得不再置顶；选择顺序定义；直言装备槽替换触发；回合外装备使用；用前死亡；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zhiyan — 直言 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 结束阶段开始时，你可以令一名角色摸一张牌并展示之：若此牌为装备牌，该角色回复1点体力，然后使用之。

来源键 `zhiyan`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：结束阶段选角色摸1并公开该牌；若装备先恢复1再由该角色回合外使用该实体装备，合法槽规则照常。

**UI/Decision**：YES_NO, CHOOSE_PLAYER, USE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinzhiyan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。结束阶段开始时，你可令一名角色摸一张牌（正面朝上移动）。若此牌为基本牌，则你摸一张牌。若此牌为装备牌，则其回复1点体力并使用此装备牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zhiyan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。结束阶段，你可以令一名角色摸一张牌并展示之，若为装备牌，其使用此牌并回复1点体力。

**Test Requirements**：结束阶段选角色摸1并公开该牌；若装备先恢复1再由该角色回合外使用该实体装备，合法槽规则照常。；已被落英获得不再置顶；选择顺序定义；直言装备槽替换触发；回合外装备使用；用前死亡；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_zhu_ran

| Field | Definition |
| --- | --- |
| General ID | yj2013_zhu_ran |
| Chinese Name | 朱然 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | wu；当前runtime映射 wu |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | danshou；获得后才可用： |
| Chinese Skill Names | 胆守 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择阶梯成本胆守的历史修订，避开初版终止一切结算；不采用后期目标计数摸牌。 |
| Estimated Power | B；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | CATEGORY, COUNTER, SEQUENCE；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | HIGH；必须专项策略：选择阶梯弃牌胆守，不采用结束一切结算原版 |
| UI/Decision Requirements | CHOOSE_CARDS, CHOOSE_OPTION, CHOOSE_PLAYER |
| Test Requirements | X=1/2/3/4/5；攻击范围；新阶段重置；先成本再分支；不是死亡触发；无足牌不能发动 |


### danshou — 胆守 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 出牌阶段，你可以弃置X张牌并选择攻击范围内的一名角色：若X为1，你弃置该角色的一张牌；若X为2，你令该角色交给你一张牌；若X为3，你对该角色造成一点伤害；若X大于或等于4，你与该角色各摸两张牌。（X为本阶段你已发动“胆守”的次数+1）

来源键 `danshou`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：PLAY第k次发动付k牌并选范围内目标；k=1弃其1，2交给你1，3伤1，≥4双方摸2；成功付费再递增。

**UI/Decision**：CHOOSE_CARDS, CHOOSE_PLAYER, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosdanshou`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当你造成伤害后，你可以摸一张牌，然后结束当前回合并结束一切结算。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `olddanshou`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你造成伤害后，你可以摸一张牌。若如此做，终止一切结算，当前回合结束。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xindanshou`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。①每回合限一次，当你成为基本牌或锦囊牌的目标后，你可以摸X张牌（X为你本回合内成为过基本牌或锦囊牌的目标的次数）。②一名其他角色的结束阶段，若你本回合内没有发动过〖胆守①〗，则你可以弃置X张牌并对其造成1点伤害（X为其手牌数，无牌则不弃）。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `danshou`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段，你可以选择你攻击范围内的一名其他角色，然后弃置X张牌（X为此前你于此阶段你发动“胆守”的次数+1）。若X：为1，你弃置该角色的一张牌；为2，令该角色交给你一张牌；为3，你对该角色造成1点伤害；不小于4，你与该角色各摸两张牌。

**Test Requirements**：PLAY第k次发动付k牌并选范围内目标；k=1弃其1，2交给你1，3伤1，≥4双方摸2；成功付费再递增。；X=1/2/3/4/5；攻击范围；新阶段重置；先成本再分支；不是死亡触发；无足牌不能发动；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_fu_huanghou

| Field | Definition |
| --- | --- |
| General ID | yj2013_fu_huanghou |
| Chinese Name | 伏皇后 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | qun；当前runtime映射 qun |
| Gender | female |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | zhuikong, qiuyuan；获得后才可用： |
| Chinese Skill Names | 惴恐, 求援 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择限制目标惴恐与交闪求援，保留非跳过阶段的控制，不添加界版不响应或获得拼点牌。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | PINDIAN, SCOPE, SEQUENCE, TARGET；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | VERY HIGH；必须专项策略：惴恐赢限制他人目标；求援交闪否则追加目标 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 非跳阶段版本；无手不能拼；平局方向距离；追加不得重复；无手可选求援；闪给牌非打出闪 |


### zhuikong — 惴恐 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 一名其他角色的回合开始时，若你已受伤，你可以与其拼点：若你赢，本回合该角色使用牌不能选择除该角色外的角色为目标；若你没赢，该角色无视与你的距离，直到回合结束。

来源键 `zhuikong`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：其他人回合开始自己受伤可拼点；赢绑定target本回合只能以自己为角色目标；没赢target至自己的距离忽略。

**UI/Decision**：YES_NO, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `noszhuikong`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。一名其他角色的回合开始时，若你已受伤，你可以与其拼点：若你赢，该角色跳过出牌阶段；若你没赢，该角色无视与你的距离，直到回合结束。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rezhuikong`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。其他角色的回合开始时，若你已受伤，你可与其拼点：若你赢，本回合该角色只能对自己使用牌；若你没赢，你获得其拼点的牌，然后其视为对你使用一张【杀】。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `oldzhuikong`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。其他角色的准备阶段，若你已受伤，你可以与该角色拼点。若你赢，该角色跳过本回合的出牌阶段。若你没赢，其本回合至你的距离视为1。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `zhuikong`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。其他角色的准备阶段，若你已受伤，你可以与该角色拼点。若你赢，该角色本回合使用的牌不能指定除该角色外的角色为目标。若你没赢，其本回合至你的距离视为1。

**Test Requirements**：其他人回合开始自己受伤可拼点；赢绑定target本回合只能以自己为角色目标；没赢target至自己的距离忽略。；非跳阶段版本；无手不能拼；平局方向距离；追加不得重复；无手可选求援；闪给牌非打出闪；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### qiuyuan — 求援 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 每当你成为【杀】的目标时，你可以令一名除此【杀】使用者外的的其他角色交给你一张【闪】，否则该角色也成为此【杀】的目标。

来源键 `qiuyuan`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：被杀指定后选除杀使用者与自己外的其他人，其给闪则只转移实体牌，否则也加为杀目标；去重循环保护。

**UI/Decision**：YES_NO, CHOOSE_PLAYER, CHOOSE_CARD。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosqiuyuan`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。每当你成为【杀】的目标时，你可以令一名除此【杀】使用者外的有手牌的其他角色正面朝上交给你一张手牌：若此牌不为【闪】，该角色也成为此【杀】的目标。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `reqiuyuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。当你成为【杀】的目标时，你可选择另一名其他角色。除非该角色交给你一张除【杀】以外的基本牌，否则其也成为此【杀】的目标且该角色不能响应此【杀】。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `oldqiuyuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你成为【杀】的目标时，你可以令一名有手牌的其他角色正面朝上交给你一张牌。若此牌不为【闪】，则该角色也成为此【杀】的额外目标。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `qiuyuan`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你成为【杀】的目标时，你可以令一名其他角色选择一项：①、交给你一张【闪】；②、成为此【杀】的额外目标。

**Test Requirements**：被杀指定后选除杀使用者与自己外的其他人，其给闪则只转移实体牌，否则也加为杀目标；去重循环保护。；非跳阶段版本；无手不能拼；平局方向距离；追加不得重复；无手可选求援；闪给牌非打出闪；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## yj2013_li_ru

| Field | Definition |
| --- | --- |
| General ID | yj2013_li_ru |
| Chinese Name | 李儒 |
| Expansion | yj2013 / 历史来源 yj2013 |
| Year | 2013 |
| Faction | qun；当前runtime映射 qun |
| Gender | male |
| Base HP | 3 |
| Max HP | 3 |
| Lord Skill? | False |
| Skill IDs | juece, mieji, fencheng；获得后才可用： |
| Chinese Skill Names | 绝策, 灭计, 焚城 |
| Chosen Version | QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7 |
| Version Status | LOCKED_REFERENCE ；Q00 |
| Why This Version | 选择末阶段空手绝策、顶牌灭计、递增2火伤焚城的同一历史包，不混初版黑锦囊多目标与固定1伤。 |
| Estimated Power | S；BALANCE RISK：资源爆发/压制可能高于旧神将；五/八人分别验收 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | CATEGORY, ORDER, REACTION, SEQUENCE；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | VERY HIGH；必须专项策略：绝策末阶段空手伤害；灭计黑锦囊顶牌；焚城递增弃牌或2火伤 |
| UI/Decision Requirements | CHOOSE_CARD, CHOOSE_CARDS, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1 |


### juece — 绝策 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 结束阶段开始时，你可以对一名没有手牌的角色造成1点伤害。

来源键 `juece`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：FINISH开始选无手牌角色伤1；不是失去最后手牌即时触发候选。

**UI/Decision**：YES_NO, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosjuece`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。你的回合内，一名体力值大于0的角色失去最后的手牌后，你可以对其造成1点伤害。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `rejuece`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。结束阶段，你可以对一名本回合内失去过牌的角色造成1点伤害。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinjuece`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。结束阶段，你可以对一名没有手牌的角色造成1点伤害。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `juece`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当其他角色在你回合内失去最后的手牌后，你可以对其造成1点伤害。

**Test Requirements**：FINISH开始选无手牌角色伤1；不是失去最后手牌即时触发候选。；灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### mieji — 灭计 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 阶段技。你可以将一张黑色锦囊牌置于牌堆顶并选择一名有手牌的其他角色，该角色弃置一张锦囊牌，否则弃置两张非锦囊牌。

来源键 `mieji`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：一次PLAY将黑色锦囊手牌置顶，选有手牌他人；其弃1锦囊或2非锦囊，用约束choice不能混搭。

**UI/Decision**：CHOOSE_CARD, CHOOSE_PLAYER, CHOOSE_CARDS。choice_labels：`{"discard_trick": "弃置一张锦囊牌", "discard_two_nontricks": "弃置两张非锦囊牌"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosmieji`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。锁定技。你使用黑色非延时锦囊牌的目标数上限至少为二。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `remieji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限一次，你可以将一张黑色锦囊牌置于牌堆顶，然后令一名有牌的其他角色选择一项：交给你一张锦囊牌，或依次弃置两张非锦囊牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `dcmieji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。出牌阶段限一次，你可以展示一张武器牌或黑色锦囊牌。你将此牌置于牌堆顶，然后令一名有手牌的其他角色选择一项：⒈弃置一张锦囊牌；⒉依次弃置两张非锦囊牌。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinmieji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。出牌阶段限一次，你可以展示一张黑色锦囊牌并将之置于牌堆顶，然后令有手牌的一名其他角色选择一项：弃置一张锦囊牌；或依次弃置两张非锦囊牌。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `mieji`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。当你使用黑色普通锦囊牌选择目标后，若目标数为1，则你可以额外指定一个目标。

**Test Requirements**：一次PLAY将黑色锦囊手牌置顶，选有手牌他人；其弃1锦囊或2非锦囊，用约束choice不能混搭。；灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### fencheng — 焚城 (NEW)

**Exact Chosen Skill Text / FROZEN_REFERENCE_TEXT**

> 限定技。出牌阶段，你可以令所有其他角色：弃置至少X张牌，否则受到2点火焰伤害。（X为上一名进行选择的角色以此法弃置的牌数+1）

来源键 `fencheng`：[固定revision档案](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/YJCM2013Package.lua)。

**机制语义**：限定PLAY，其他存活人席位序；首人X=1，每人弃≥X或2火伤；下一阈值为上人实际弃数+1，伤害分支令下人X=1。

**UI/Decision**：YES_NO, CHOOSE_CARDS。choice_labels：`{"done": "确认选择", "take_fire_damage": "受到2点火焰伤害"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- A_INITIAL_ARCHIVE `nosfencheng`：[来源](https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/lang/zh_CN/Package/NostalgiaPackage.lua)。限定技。出牌阶段，你可以令所有其他角色弃置X张牌，否则你对该角色造成1点火焰伤害。（X为该角色装备区牌的数量且至少为1）

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `dcfencheng`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/refresh/translate.js)。限定技。出牌阶段，你可以指定一名其他角色，令从其开始的其他角色依次选择一项：⒈弃置至少X张牌（X为上一名角色弃置的牌数+1）。⒉你对其造成2点火焰伤害。

- C_EXCLUDED_MODERN_OR_OTHER_ARCHIVE `xinfencheng`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。限定技。出牌阶段，你可以令所有其他角色各选择一项：弃置至少X张牌(X为该角色的上家以此法弃置牌的数量+1)；或受到你对其造成的2点火焰伤害。

- OTHER_UNPREFIXED_ARCHIVE_NOT_AUTOMATICALLY_SAME_VERSION `fencheng`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/yijiang/translate.js)。限定技。出牌阶段，你可令所有其他角色依次选择一项：弃置X张牌；或受到1点火焰伤害。(X为该角色装备区里牌的数量且至少为1)

**Test Requirements**：限定PLAY，其他存活人席位序；首人X=1，每人弃≥X或2火伤；下一阈值为上人实际弃数+1，伤害分支令下人X=1。；灭计延时锦囊算锦囊；1锦囊或2非锦囊；焚城首人至少1拒绝后下人重置1；铁索/死亡后继续；不能固定伤害1；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## shadow_god_liubei

| Field | Definition |
| --- | --- |
| General ID | shadow_god_liubei |
| Chinese Name | 神刘备 |
| Expansion | new_gods / 历史来源 shadow |
| Year | 2018 |
| Faction | god；当前runtime映射 qun |
| Gender | male |
| Base HP | 6 |
| Max HP | 6 |
| Lord Skill? | False |
| Skill IDs | longnu, jieying_liubei；获得后才可用： |
| Chinese Skill Names | 龙怒, 结营 |
| Chosen Version | 候选：阴雷基础神将档案 @ e18a8256e01ab1357e4c7472349dceb3d0aa1a3a |
| Version Status | QUESTION Q04；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 此项等待人工确认，不能视为最终官方版本锁。 |
| Estimated Power | A；需五/八人身份适配；按官方候选保留数值 |
| Implementation Complexity | Tier 4 |
| Engine Dependencies | AURA, CONVERT, MAXHP, SCOPE, VIEWAS；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | MEDIUM |
| AI Complexity | VERY HIGH；必须专项策略：龙怒两个状态按出牌阶段切换；结营强制横置与共享上限 |
| UI/Decision Requirements | CHOOSE_PLAYER |
| Test Requirements | 阴阳标签/首态待确认；阴红手火杀不限距离；阳锦囊雷杀不限次数；不是桃转换；解链即重横；多源上限 |


### longnu — 龙怒 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 转换技，锁定技，阴：出牌阶段开始时，你失去1点体力并摸一张牌，然后本阶段内你的红色手牌均视为火【杀】且无距离限制。阳：出牌阶段开始时，你减1点体力上限并摸一张牌，然后本阶段内你的锦囊牌均视为雷【杀】且无使用次数限制。

来源键 `nzry_longnu`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：PLAY开始强制当前转换状态费用与摸1；阴红色手牌视火杀不限距离，阳锦囊视雷杀不限次数，phase末撤销，状态持久交替。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：PLAY开始强制当前转换状态费用与摸1；阴红色手牌视火杀不限距离，阳锦囊视雷杀不限次数，phase末撤销，状态持久交替。；阴阳标签/首态待确认；阴红手火杀不限距离；阳锦囊雷杀不限次数；不是桃转换；解链即重横；多源上限；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### jieying_liubei — 结营 (SAME NAME / DIFFERENT SEMANTICS)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 锁定技，游戏开始时或当你的武将牌重置时，你横置；所有已横置的角色手牌上限+2；结束阶段，你横置一名其他角色。

来源键 `nzry_jieying`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：神刘备结营，自己被重置即重新横置；所有横置角色上限+2为来源绑定光环；FINISH强制横置另一角色。

**UI/Decision**：CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：神刘备结营，自己被重置即重新横置；所有横置角色上限+2为来源绑定光环；FINISH强制横置另一角色。；阴阳标签/首态待确认；阴红手火杀不限距离；阳锦囊雷杀不限次数；不是桃转换；解链即重横；多源上限；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## shadow_god_luxun

| Field | Definition |
| --- | --- |
| General ID | shadow_god_luxun |
| Chinese Name | 神陆逊 |
| Expansion | new_gods / 历史来源 shadow |
| Year | 2018 |
| Faction | god；当前runtime映射 qun |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | junlve, cuike, zhanhuo；获得后才可用： |
| Chinese Skill Names | 军略, 摧克, 绽火 |
| Chosen Version | 候选：阴雷基础神将档案 @ e18a8256e01ab1357e4c7472349dceb3d0aa1a3a |
| Version Status | QUESTION Q04；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 此项等待人工确认，不能视为最终官方版本锁。 |
| Estimated Power | S；BALANCE RISK：资源爆发/压制可能高于旧神将；五/八人分别验收 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | COUNTER, REACTION, SEQUENCE；见mechanic_matrix接口字典 |
| Multiplayer Risk | MEDIUM |
| Projection Risk | MEDIUM |
| AI Complexity | VERY HIGH；必须专项策略：军略按伤害点累积；摧克奇偶/超过7清标群伤；绽火限一次 |
| UI/Decision Requirements | CHOOSE_OPTION, CHOOSE_PLAYER, CHOOSE_PLAYERS, YES_NO |
| Test Requirements | 0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导 |


### junlve — 军略 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 锁定技，当你受到或造成伤害后，你获得X个“军略”标记(X为伤害点数)。

来源键 `nzry_junlve`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：受到或造成实际伤害获得等量标记；若同时两身份均满足分别计入需Q08核对；HP流失不计。

**UI/Decision**：自动结算。choice_labels：`{}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：受到或造成实际伤害获得等量标记；若同时两身份均满足分别计入需Q08核对；HP流失不计。；0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### cuike — 摧克 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 出牌阶段开始时，若“军略”标记的数量为奇数，你可以对一名角色造成1点伤害；若“军略”标记的数量为偶数，你可以横置一名角色并弃置其区域内的一张牌。然后，若“军略”标记的数量超过7个，你可以移去全部“军略”标记并对所有其他角色造成1点伤害。

来源键 `nzry_cuike`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：PLAY开始军略奇数可伤1/偶数可横置角色并弃其区域1；后续军略>7可全移并对其他人伤1，逐个处理新增标记。

**UI/Decision**：YES_NO, CHOOSE_PLAYER, CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：PLAY开始军略奇数可伤1/偶数可横置角色并弃其区域1；后续军略>7可全移并对其他人伤1，逐个处理新增标记。；0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zhanhuo — 绽火 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 限定技，出牌阶段，你可以移去全部“军略”标记，令至多等量的已横置角色弃置所有装备区内的牌。然后，你对其中一名角色造成1点火焰伤害。

来源键 `nzry_dinghuo`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：限定PLAY消费全部军略，选至多等量横置角色全弃装备，再选其中一个火伤1；无标记不能形成非空目标。

**UI/Decision**：YES_NO, CHOOSE_PLAYERS, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：限定PLAY消费全部军略，选至多等量横置角色全弃装备，再选其中一个火伤1；无标记不能形成非空目标。；0为偶；7/8阈值；先单体可能改变标记；群伤又积军略；绽火限定标记与军略分离；铁索传导；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## thunder_god_ganning

| Field | Definition |
| --- | --- |
| General ID | thunder_god_ganning |
| Chinese Name | 神甘宁 |
| Expansion | new_gods / 历史来源 thunder |
| Year | 2018 |
| Faction | god；当前runtime映射 qun |
| Gender | male |
| Base HP | 3 |
| Max HP | 6 |
| Lord Skill? | False |
| Skill IDs | poxi, jieying_ganning；获得后才可用： |
| Chinese Skill Names | 魄袭, 劫营 |
| Chosen Version | 候选：阴雷基础神将档案 @ e18a8256e01ab1357e4c7472349dceb3d0aa1a3a |
| Version Status | QUESTION Q05；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 此项等待人工确认，不能视为最终官方版本锁。 |
| Estimated Power | S；BALANCE RISK：资源爆发/压制可能高于旧神将；五/八人分别验收 |
| Implementation Complexity | Tier 3 |
| Engine Dependencies | AURA, PHASE, SCOPE, SUBSET, VISIBILITY；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | VERY HIGH；必须专项策略：初始HP3上限6候选；魄袭私看并选双方4异花色；劫营营所有权 |
| UI/Decision Requirements | CHOOSE_CARDS, CHOOSE_PLAYER, YES_NO |
| Test Requirements | 0/1/2/3/4张自身分支；取消看牌后不弃；其他客户端不能看；营增益后夺手；持营死/神死清理 |


### poxi — 魄袭 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 出牌阶段限一次，你可以观看一名其他角色的手牌，然后你可以弃置你与其手牌中的四张花色不同的牌。若如此做，根据此次弃置你的牌的数量执行以下效果：零张，扣减1点体力上限；一张，你结束出牌阶段且本回合手牌上限-1；三张，你回复1点体力；四张，你摸四张牌。

来源键 `drlt_poxi`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：一次PLAY先建立仅发动者可看目标手牌grant，可取消；选择双方手牌四种不同花色各1一起弃，根据自弃0/1/2/3/4分支。

**UI/Decision**：CHOOSE_PLAYER, YES_NO, CHOOSE_CARDS。choice_labels：`{"done": "确认选择", "cancel_selection": "结束选牌"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：一次PLAY先建立仅发动者可看目标手牌grant，可取消；选择双方手牌四种不同花色各1一起弃，根据自弃0/1/2/3/4分支。；0/1/2/3/4张自身分支；取消看牌后不弃；其他客户端不能看；营增益后夺手；持营死/神死清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### jieying_ganning — 劫营 (SAME NAME / DIFFERENT SEMANTICS)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 回合开始时，若场上没有拥有“营”标记的角色，你获得1个“营”标记；结束阶段，你可以将你的一个“营”标记交给一名角色；有“营”标记的角色摸牌阶段多摸一张牌，出牌阶段使用【杀】的次数上限+1，手牌上限+1。有“营”的其他角色回合结束时，其移去“营”标记，然后你获得其所有手牌。

来源键 `drlt_jieying`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：神甘宁劫营，营为独立来源persistent effect；没人有营才回合开始自得，FINISH可给其他角色，持者回合末移营后夺其所有手牌。

**UI/Decision**：YES_NO, CHOOSE_PLAYER。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

未在本次检索的固定档案中确认独立初版/现代重做差异；不宣称不存在。没有证据时禁止自行补写“官方修订”。Q00补卡面出处后复核。

**Test Requirements**：神甘宁劫营，营为独立来源persistent effect；没人有营才回合开始自得，FINISH可给其他角色，持者回合末移营后夺其所有手牌。；0/1/2/3/4张自身分支；取消看牌后不弃；其他客户端不能看；营增益后夺手；持营死/神死清理；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

## thunder_god_zhangliao

| Field | Definition |
| --- | --- |
| General ID | thunder_god_zhangliao |
| Chinese Name | 神张辽 |
| Expansion | new_gods / 历史来源 thunder |
| Year | 2018 |
| Faction | god；当前runtime映射 qun |
| Gender | male |
| Base HP | 4 |
| Max HP | 4 |
| Lord Skill? | False |
| Skill IDs | duorui, zhiti；获得后才可用： |
| Chinese Skill Names | 夺锐, 止啼 |
| Chosen Version | 候选：阴雷基础神将档案 @ e18a8256e01ab1357e4c7472349dceb3d0aa1a3a |
| Version Status | QUESTION Q06；Q00 |
| Why This Version | 保留经典身份局辨识机制，固定历史来源，不增加档案之外摸牌、增伤或额外次数。 此项等待人工确认，不能视为最终官方版本锁。 |
| Estimated Power | S；BALANCE RISK：资源爆发/压制可能高于旧神将；五/八人分别验收 |
| Implementation Complexity | Tier 4 |
| Engine Dependencies | AURA, OWNERSHIP, PINDIAN, SLOT；见mechanic_matrix接口字典 |
| Multiplayer Risk | HIGH |
| Projection Risk | HIGH |
| AI Complexity | VERY HIGH；必须专项策略：夺锐临时借技能与独立失效；止啼受伤范围上限减1并恢复栏 |
| UI/Decision Requirements | CHOOSE_OPTION, YES_NO |
| Test Requirements | 出牌阶段伤害才夺；装备栏费用；目标下回合末/死亡；断肠多原因；化身/极略；拼点决斗胜利事件 |


### duorui — 夺锐 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 当你于出牌阶段内对一名其他角色造成伤害后，你可以废除你装备区内的一个装备栏（若已全部废除则可以跳过此步骤），然后获得该角色的一个技能直到其的下回合结束或其死亡(觉醒技，限定技，主公技，隐匿技，使命技等特殊技能除外)。若如此做，该角色该技能失效且你不能再发动〖夺锐〗直到你失去以此法获得的技能。

来源键 `drlt_duorui`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：PLAY实际对其他人伤后可废一装备栏并租借其一个合格武将技能，失效作用于指定ownership；目标下回合末/死亡回收；细则Q06。

**UI/Decision**：YES_NO, CHOOSE_OPTION。choice_labels：`{"slot_weapon": "废除武器栏", "slot_armor": "废除防具栏", "slot_offensive_horse": "废除进攻坐骑栏", "slot_defensive_horse": "废除防御坐骑栏"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_OL `olduorui`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。当你于出牌阶段内对一名角色造成伤害后，你可以选择该角色武将牌上的一个技能。若如此做，你结束出牌阶段，且你令此技能于其下个回合结束之前无效。

**Test Requirements**：PLAY实际对其他人伤后可废一装备栏并租借其一个合格武将技能，失效作用于指定ownership；目标下回合末/死亡回收；细则Q06。；出牌阶段伤害才夺；装备栏费用；目标下回合末/死亡；断肠多原因；化身/极略；拼点决斗胜利事件；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

### zhiti — 止啼 (NEW)

**Exact Chosen Skill Text / CANDIDATE_NOT_FINAL**

> 锁定技。①你攻击范围内已受伤的其他角色手牌上限-1；②当你和已受伤的角色拼点或【决斗】胜利/受到已受伤角色造成的伤害后，若对方/伤害来源在你的攻击范围内，则你恢复一个装备栏。

来源键 `drlt_zhiti`：[固定revision档案](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。

**机制语义**：范围内已伤他人上限-1；与范围内已伤者拼点/决斗胜或被其伤害后恢复一废栏；决斗胜不能只依据造成任意伤害。

**UI/Decision**：CHOOSE_OPTION。choice_labels：`{"decline": "放弃发动", "done": "确认选择"}`。tooltip metadata：名称、完整上文说明、版本、状态，值见catalog.json。

**Alternative Versions**：

- C_EXCLUDED_OL `olzhiti`：[来源](https://github.com/libccy/noname/blob/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a/character/extra/translate.js)。锁定技，你攻击范围内已受伤角色的手牌上限-1。若场上已受伤的角色数：不小于1，你的手牌上限+1；不小于3，你于摸牌阶段开始时令额定摸牌数+1；不小于5，回合结束时，你废除一名角色的一个随机装备栏。

**Test Requirements**：范围内已伤他人上限-1；与范围内已伤者拼点/决斗胜或被其伤害后恢复一废栏；决斗胜不能只依据造成任意伤害。；出牌阶段伤害才夺；装备栏费用；目标下回合末/死亡；断肠多原因；化身/极略；拼点决斗胜利事件；60秒timeout产生合法Decision；ACK重放不重复支付；request期间重连恢复同一frame；Web/PySide候选一致。

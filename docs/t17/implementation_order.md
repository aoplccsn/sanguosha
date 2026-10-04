# T17B/C/D/E 实现顺序

不要在T17A实现。先解除对应版本门禁，扩展通用引擎依赖，再分包验收。全项目按Tier 1→2→3→4；每个expansion仍独立milestone，不能把神将提前注入生产。

## Tier 1

| 阶段 | 武将 | 关键前置 |
| --- | --- | --- |
| T17B | [于禁](roster.md#yj2011_yu_jin) | TARGET；版本 LOCKED_REFERENCE |
| T17B | [徐盛](roster.md#yj2011_xu_sheng) | REACTION；版本 LOCKED_REFERENCE |
| T17C | [华雄](roster.md#yj2012_hua_xiong) | MAXHP, REACTION；版本 LOCKED_REFERENCE |
| T17D | [郭淮](roster.md#yj2013_guo_huai) | COUNTER, REACTION；版本 LOCKED_REFERENCE |


## Tier 2

| 阶段 | 武将 | 关键前置 |
| --- | --- | --- |
| T17B | [张春华](roster.md#yj2011_zhang_chunhua) | HPREWRITE, REACTION；版本 QUESTION |
| T17B | [徐庶](roster.md#yj2011_xu_shu) | HPREWRITE, MOVE, REACTION；版本 LOCKED_REFERENCE |
| T17B | [凌统](roster.md#yj2011_ling_tong) | MOVE, REACTION；版本 LOCKED_REFERENCE |
| T17C | [曹彰](roster.md#yj2012_cao_zhang) | SCOPE, TARGET；版本 LOCKED_REFERENCE |
| T17C | [马岱](roster.md#yj2012_ma_dai) | JUDGMENT, SCOPE, TARGET；版本 LOCKED_REFERENCE |
| T17C | [刘表](roster.md#yj2012_liu_biao) | PHASE, SCOPE；版本 QUESTION |
| T17D | [关平](roster.md#yj2013_guan_ping) | COUNTER, REACTION；版本 LOCKED_REFERENCE |
| T17D | [潘璋马忠](roster.md#yj2013_pan_zhang_ma_zhong) | MOVE, REACTION, TARGET；版本 LOCKED_REFERENCE |


## Tier 3

| 阶段 | 武将 | 关键前置 |
| --- | --- | --- |
| T17B | [曹植](roster.md#yj2011_cao_zhi) | DYING, MOVE, REACTION, VIEWAS；版本 LOCKED_REFERENCE |
| T17B | [法正](roster.md#yj2011_fa_zheng) | AUTHUSE, MOVE, REACTION, SEQUENCE, VISIBILITY；版本 LOCKED_REFERENCE |
| T17B | [马谡](roster.md#yj2011_ma_su) | DEATH, MOVE, ORDER, VISIBILITY；版本 LOCKED_REFERENCE |
| T17B | [吴国太](roster.md#yj2011_wu_guotai) | DYING, EXCHANGE, MOVE, VISIBILITY；版本 LOCKED_REFERENCE |
| T17B | [陈宫](roster.md#yj2011_chen_gong) | AUTHUSE, MOVE, SCOPE, TARGET；版本 LOCKED_REFERENCE |
| T17B | [高顺](roster.md#yj2011_gao_shun) | PINDIAN, SCOPE, TARGET, VIEWAS；版本 LOCKED_REFERENCE |
| T17C | [荀攸](roster.md#yj2012_xun_you) | REACTION, TARGET, VIEWAS, VISIBILITY；版本 LOCKED_REFERENCE |
| T17C | [王异](roster.md#yj2012_wang_yi) | DISTRIBUTE, DYING, HPREWRITE, TARGET, VISIBILITY；版本 LOCKED_REFERENCE |
| T17C | [钟会](roster.md#yj2012_zhong_hui) | MAXHP, OWNERSHIP, PILE, REACTION；版本 QUESTION |
| T17C | [廖化](roster.md#yj2012_liao_hua) | COUNTER, DYING, PHASE；版本 LOCKED_REFERENCE |
| T17C | [步练师](roster.md#yj2012_bu_lianshi) | DEATH, MOVE, VISIBILITY；版本 LOCKED_REFERENCE |
| T17C | [程普](roster.md#yj2012_cheng_pu) | DYING, PILE, REACTION, TARGET, VIEWAS；版本 LOCKED_REFERENCE |
| T17C | [韩当](roster.md#yj2012_han_dang) | SCOPE, SEQUENCE, TARGET；版本 LOCKED_REFERENCE |
| T17D | [曹冲](roster.md#yj2013_cao_chong) | HPREWRITE, MOVE, SUBSET；版本 LOCKED_REFERENCE |
| T17D | [满宠](roster.md#yj2013_man_chong) | CATEGORY, SEQUENCE, VISIBILITY；版本 LOCKED_REFERENCE |
| T17D | [简雍](roster.md#yj2013_jian_yong) | MOVE, PINDIAN, SCOPE, TARGET；版本 LOCKED_REFERENCE |
| T17D | [刘封](roster.md#yj2013_liu_feng) | AUTHUSE, PILE, VISIBILITY；版本 LOCKED_REFERENCE |
| T17D | [虞翻](roster.md#yj2013_yu_fan) | AUTHUSE, MOVE, ORDER, REACTION；版本 LOCKED_REFERENCE |
| T17D | [朱然](roster.md#yj2013_zhu_ran) | CATEGORY, COUNTER, SEQUENCE；版本 LOCKED_REFERENCE |
| T17D | [伏皇后](roster.md#yj2013_fu_huanghou) | PINDIAN, SCOPE, SEQUENCE, TARGET；版本 LOCKED_REFERENCE |
| T17D | [李儒](roster.md#yj2013_li_ru) | CATEGORY, ORDER, REACTION, SEQUENCE；版本 LOCKED_REFERENCE |
| T17E | [神陆逊](roster.md#shadow_god_luxun) | COUNTER, REACTION, SEQUENCE；版本 QUESTION |
| T17E | [神甘宁](roster.md#thunder_god_ganning) | AURA, PHASE, SCOPE, SUBSET, VISIBILITY；版本 QUESTION |


## Tier 4

| 阶段 | 武将 | 关键前置 |
| --- | --- | --- |
| T17C | [关兴张苞](roster.md#yj2012_guan_xing_zhang_bao) | OWNERSHIP, SCOPE, VIEWAS；版本 LOCKED_REFERENCE |
| T17E | [神刘备](roster.md#shadow_god_liubei) | AURA, CONVERT, MAXHP, SCOPE, VIEWAS；版本 QUESTION |
| T17E | [神张辽](roster.md#thunder_god_zhangliao) | AURA, OWNERSHIP, PINDIAN, SLOT；版本 QUESTION |

每包必须分别通过规则边界、AI、真人混合、5/8人、Projection、所有请求暂停点重连、ACK幂等、Web/PySide同规则。建议B先于禁/徐盛，再伤逝/无言/旋风，最后拼点授权与交换；C先华雄与将驰/潜袭/刘表，再请求与权/醇/额外阶段，最后父魂ownership；D先郭淮与夺刀暗箭/龙吟，再组合请求，最后巧说目标与焚城；E先军略框架与神陆逊，再神甘宁可见性和营，神刘备转换光环，最后神张辽。E的顺序不表示可跳过Tier4依赖。

美术只沿用未来resource_id=general.<stable_id>与现有fallback协议，不创建资源、不修改9套动态资产；四神Master/idle由用户后续制作。

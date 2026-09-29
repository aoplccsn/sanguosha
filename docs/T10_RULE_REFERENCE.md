# T10 Rule Reference: Myth Reborn

Classic identity-mode summaries for the 40 Feng Lin Huo Shan generals.

| Pack | ID | General | Faction | HP | Skills |
|---|---|---|---|---:|---|
| wind | `wind_xiahou_yuan` | 夏侯渊 | wei | 4 | shensu |
| wind | `wind_cao_ren` | 曹仁 | wei | 4 | jushou |
| wind | `wind_huang_zhong` | 黄忠 | shu | 4 | liegong |
| wind | `wind_wei_yan` | 魏延 | shu | 4 | kuanggu |
| wind | `wind_xiao_qiao` | 小乔 | wu | 3 | tianxiang、hongyan |
| wind | `wind_zhou_tai` | 周泰 | wu | 4 | bujqu |
| wind | `wind_zhang_jiao` | 张角 | qun | 3 | leiji、guidao、huangtian |
| wind | `wind_yuji` | 于吉 | qun | 3 | guhuo |
| wind | `wind_god_guanyu` | 神关羽 | qun | 5 | wushen、wuhun |
| wind | `wind_god_lvmeng` | 神吕蒙 | qun | 3 | shelie、gongxin |
| fire | `fire_dian_wei` | 典韦 | wei | 4 | qiangxi |
| fire | `fire_xun_yu` | 荀彧 | wei | 3 | quhu、jieming |
| fire | `fire_pang_tong` | 庞统 | shu | 3 | lianhuan、niepan |
| fire | `fire_wolong` | 卧龙诸葛亮 | shu | 3 | bazhen、huoji、kanpo |
| fire | `fire_taishi_ci` | 太史慈 | wu | 4 | tianyi |
| fire | `fire_pang_de` | 庞德 | qun | 4 | mashu、mengjin |
| fire | `fire_yan_liang_wen_chou` | 颜良文丑 | qun | 4 | shuangxiong |
| fire | `fire_yuan_shao` | 袁绍 | qun | 4 | luanji、xueyi |
| fire | `fire_god_zhouyu` | 神周瑜 | qun | 4 | qinyin、yeyan |
| fire | `fire_god_zhugeliang` | 神诸葛亮 | qun | 3 | qixing、kuangfeng、dawu |
| forest | `forest_caopi` | 曹丕 | wei | 3 | xingshang、fangzhu、songwei |
| forest | `forest_xuhuang` | 徐晃 | wei | 4 | duanliang |
| forest | `forest_menghuo` | 孟获 | shu | 4 | huoshou、zaiqi |
| forest | `forest_zhurong` | 祝融 | shu | 4 | juxiang、lieren |
| forest | `forest_sunjian` | 孙坚 | wu | 4 | yinghun |
| forest | `forest_lusu` | 鲁肃 | wu | 3 | haoshi、dimeng |
| forest | `forest_jia_xu` | 贾诩 | qun | 3 | wansha、luanwu、weimu |
| forest | `forest_dong_zhuo` | 董卓 | qun | 8 | jiuchi、roulin、benghuai、baonue |
| forest | `forest_god_caocao` | 神曹操 | qun | 3 | guixin、feiying |
| forest | `forest_god_lvbu` | 神吕布 | qun | 5 | kuangbao、wumou、wuwei、shenfen |
| mountain | `mountain_zhang_he` | 张郃 | wei | 4 | qiaobian |
| mountain | `mountain_deng_ai` | 邓艾 | wei | 4 | tuntian、zaoxian |
| mountain | `mountain_liushan` | 刘禅 | shu | 3 | xiangle、fangquan、ruoyu |
| mountain | `mountain_jiang_wei` | 姜维 | shu | 4 | tiaoxin、zhiji、guanxing |
| mountain | `mountain_sunce` | 孙策 | wu | 4 | jiang、hunzi、zhiba |
| mountain | `mountain_zhang_zhaozhang` | 张昭张纮 | wu | 3 | zhijian、guzheng |
| mountain | `mountain_zuoci` | 左慈 | qun | 3 | huashen、xinsheng |
| mountain | `mountain_cai_wenji` | 蔡文姬 | qun | 3 | beige、duanchang |
| mountain | `mountain_god_zhaoyun` | 神赵云 | qun | 2 | juejing、longhun |
| mountain | `mountain_god_simayi` | 神司马懿 | qun | 4 | renjie、baoyin、lianpo |

## Engine notes

- Skills are catalogued with concise summaries and are wired to existing card, damage, judgment, limited, and view-as pipelines as handlers land.
- God generals use the existing QUN faction value until a dedicated god faction is introduced; pack and resource_id remain authoritative.
- No official artwork or verbatim rule text is included.

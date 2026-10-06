# Sources and evidence limits

优先遵守docs/t17/final_version_lock.md、version_matrix.md、roster.md和当前catalogue的经典版本。钟会、神刘备、神张辽、刘表不改为现代版。

- 项目锁文档：../t17/final_version_lock.md、../t17/version_matrix.md、../t17/sources.md。
- 本轮化身池直接来源：用户2026-10-06补充要求，优先于社区实现不同禁将名单。
- 社区历史语义辅助：https://github.com/Mogara/QSanguosha-v2/blob/e8768851bd8054db9fd1b63cd6f1feca813590d7/src/package/mountain.cpp 。本轮联网只读核对化身获取/可见技能选择；语义记录huashen_source_notes.txt，没有引入第三方代码。
- YJ和四神历史来源固定revision清单沿用../t17/sources.md；不称其为官方出版商卡面。
- 官方长技能文字仅核验，项目保留原创简短中文说明。

尚未完成103将189技能及43卡定义逐项独立规则来源复核。无法用已有测试全绿替代；总矩阵的BLOCKED条目保留证据缺口。

本轮继续只读核对：固定revision StandardGeneralPackage.lua（SHA256 f84f161385faee2602df38b65faa76efd79757df1ecf975580cfb0570f6a1f48），武圣红色牌语义不限制为手牌；gamerule.cpp（SHA256 61abb19afc87756a113813ea5a1c007ffe0ba57fc1a520b50406e7494d168302），身份局主公误杀忠臣仅手牌和装备处罚。未下载保存第三方实现，也未复制到项目。

补核：QS-v2同一固定revision maneuvering.cpp（SHA256 f2daa267d50948dd36ec7c8c43780d823e0407652915bfda24100b8e9f8c0416）中零目标铁索走重铸原因并在普通锦囊使用前返回。重铸独立于使用/打出/弃置；项目使用RECAST移动原因，保留获得牌和失去牌反应，不触发使用/弃置专属反应。yjcm.cpp中权牌 addToPile 的默认公开语义与项目T17C权区公开验收一致；早期Q07待核文档不覆盖后续已验收裁定。网络读取仅辅助核对，未复制外部代码。

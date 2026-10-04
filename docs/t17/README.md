# T17A — New General Roster Version Lock & Mechanic Design

基线：88ca556。范围：版本参考文本、机制依赖、AI/多人/请求与测试规划；未实现技能、未改UI/规则/美术/部署。当前生产65，规划新增38，目标103。不是已可玩103将。

## 目录

- [完整38将定义与技能全文](roster.md)
- [非生产机器可读目录](catalog.json)
- [版本矩阵](version_matrix.md) / [人工版本与FAQ问题](version_questions.md)
- [机制与引擎接口矩阵](mechanic_matrix.md)
- [强度矩阵](balance_matrix.md) / [AI矩阵](ai_matrix.md)
- [多人和Projection](multiplayer_projection.md) / [PendingRequest设计](request_design.md)
- [实现顺序](implementation_order.md) / [神张辽ownership](god_zhangliao_risk.md)
- [来源](sources.md) / [摘要校验](sources_manifest.json)
- [专项验证器](validate_catalog.py) / [验证结果](validation.md)
- [完成报告](checkpoint_report.md)

## 阵容

2011（11）：魏张春华、于禁、曹植；蜀法正、马谡、徐庶；吴凌统、徐盛、吴国太；群陈宫、高顺。

2012（12，钟会归属Q01）：魏荀攸、王异、曹彰、钟会；蜀廖化、关兴张苞、马岱；吴步练师、程普、韩当；群刘表、华雄。

2013（11）：魏曹冲、郭淮、满宠；蜀关平、简雍、刘封；吴潘璋马忠、虞翻、朱然；群伏皇后、李儒。

神（4）：神刘备、神陆逊（阴包候选），神甘宁、神张辽（雷包候选）。

## 版本门禁

31条LOCKED_REFERENCE固定所引经典修订档案，7条QUESTION：张春华、钟会、刘表、四神。它们都满足“明确版本或明确进入问题表”的结构验收；不代表全部官方发行证据已核验。所有38条authority_status仍是社区档案、官方原始卡面未验证；Q00要求人工确认资料集或补官方卡面，Q07/Q08补可见性与规则FAQ。无现代版被确认为本项目最终版本，QUESTION候选可能带后期勘误，明确阻止实施。

T17B/C/D/E先版本确认再逐包实施、测试、AI、真人混合、重连、Projection、Web/PySide验收。本checkpoint后等待人工，不开始T17B。

# 来源与证据边界

审计日期：2026-10-04（用户Asia/Shanghai）。本地基线88ca556。

| 档案 | revision | 用途 |
| --- | --- | --- |
| [QSanguosha-v2](https://github.com/Mogara/QSanguosha-v2/tree/e8768851bd8054db9fd1b63cd6f1feca813590d7) | e8768851bd8054db9fd1b63cd6f1feca813590d7 | YJCM2011/2012/2013修订文本、Nostalgia早期差异、C++ General势力性别HP构造器 |
| [noname](https://github.com/libccy/noname/tree/e18a8256e01ab1357e4c7472349dceb3d0aa1a3a) | e18a8256e01ab1357e4c7472349dceb3d0aa1a3a | extra四神候选+角色3/6HP、refresh/yijiang后期同名对照 |

读取成功的原文节选已嵌入catalog/roster。sources_manifest.json记录所有下载文件SHA256用于复核（包括未用于最终结论的shenhua文件）；不提交整份第三方软件，也不声称这些hash能替代官方卡面。网络探测：Mogara/QSanguosha主仓库不是所需一将资料，切换v2；Fandom神张辽页面返回Cloudflare验证，未绕过验证，未用其内容作证；未取得官方出版社卡面/勘误。Q00逐项补证。

HP/阵容证据：yjcm.cpp前11人YJ001–011与2011名单一致，另外钟会YJ012，yjcm2012.cpp只有YJ101–111，钟会年份留Q01；2013为YJ201–211。同revision的src/core/general.h构造器明确int max_hp=4、male=true，构造器省略HP/性别可据此核对，female显式false。神甘宁extra_character为3/6，见Q05；God faction仅metadata，现行旧八神实际qun。马术文本来自同revision StandardGeneralPackage.lua，不自行改写成引文。

原文版本相互矛盾例：伤逝QS修订封顶2而当前无名杀原版无前缀不封顶；刘表自守QS按已损HP跳阶段而无名杀按势力数限制目标；李儒同名绝策一个即时最后手牌触发一个末阶段触发。因此不从搜索摘要拼出技能全文。C列包括“其他来源无前缀不同语义”，并非所有都已证明官方现代版。

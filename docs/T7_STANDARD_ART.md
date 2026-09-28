# T7 标准包武将美术

资源 ID 按 `general.<character_id>` 命名，供 `ResourceManager.general_portrait` 使用；同一武将定义在选将界面、牌桌和详情面板共享该 ID。

T7-A 五张原创半身像沿用原有资源：

| 资源 ID | 文件 |
| --- | --- |
| `general.caocao` | `assets/generals/wei/caocao.png` |
| `general.liubei` | `assets/generals/shu/liubei.png` |
| `general.sunquan` | `assets/generals/wu/sunquan.png` |
| `general.guanyu` | `assets/generals/shu/guanyu.png` |
| `general.lvbu` | `assets/generals/qun/lvbu.png` |

本阶段新增 20 张原创半身像，使用内置 ImageGen 逐将生成，不使用官方或商业客户端图像作参考、复制或描摹。统一提示规范为：三国古装单人腰部以上构图，中国水墨与工笔线描混合、宣纸肌理、克制的矿物色和金色点缀；每名武将另指定独立的服饰、器物、神态和配色。原始生成文件保留在 Codex 的 `generated_images` 目录；下表 PNG 为项目实际使用的副本。全部 25 个资源 ID 均已写入 `assets/manifest.json`。

| 武将 | 资源 ID | 文件 |
| --- | --- | --- |
| 司马懿 | `general.simayi` | `assets/generals/wei/simayi.png` |
| 夏侯惇 | `general.xiahou_dun` | `assets/generals/wei/xiahou_dun.png` |
| 张辽 | `general.zhangliao` | `assets/generals/wei/zhangliao.png` |
| 许褚 | `general.xuchu` | `assets/generals/wei/xuchu.png` |
| 郭嘉 | `general.guojia` | `assets/generals/wei/guojia.png` |
| 甄姬 | `general.zhenji` | `assets/generals/wei/zhenji.png` |
| 张飞 | `general.zhangfei` | `assets/generals/shu/zhangfei.png` |
| 诸葛亮 | `general.zhugeliang` | `assets/generals/shu/zhugeliang.png` |
| 赵云 | `general.zhaoyun` | `assets/generals/shu/zhaoyun.png` |
| 马超 | `general.machao` | `assets/generals/shu/machao.png` |
| 黄月英 | `general.huangyueying` | `assets/generals/shu/huangyueying.png` |
| 甘宁 | `general.ganning` | `assets/generals/wu/ganning.png` |
| 吕蒙 | `general.lvmeng` | `assets/generals/wu/lvmeng.png` |
| 黄盖 | `general.huanggai` | `assets/generals/wu/huanggai.png` |
| 周瑜 | `general.zhouyu` | `assets/generals/wu/zhouyu.png` |
| 大乔 | `general.daqiao` | `assets/generals/wu/daqiao.png` |
| 陆逊 | `general.luxun` | `assets/generals/wu/luxun.png` |
| 孙尚香 | `general.sunshangxiang` | `assets/generals/wu/sunshangxiang.png` |
| 华佗 | `general.huatuo` | `assets/generals/qun/huatuo.png` |
| 貂蝉 | `general.diaochan` | `assets/generals/qun/diaochan.png` |

画像完成仅代表资源验收；技能规则完成状态按测试和最终报告判断。

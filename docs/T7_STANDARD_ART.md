# T7 标准包武将美术进度

资源 ID 按 `general.<character_id>` 命名，供 `ResourceManager.general_portrait` 使用；同一武将定义在选将界面、牌桌和详情面板共享该 ID。

当前五张已完成原创半身像沿用 T7-A 资产：

| 资源 ID | 文件 |
| --- | --- |
| `general.caocao` | `assets/generals/wei/caocao.png` |
| `general.liubei` | `assets/generals/shu/liubei.png` |
| `general.sunquan` | `assets/generals/wu/sunquan.png` |
| `general.guanyu` | `assets/generals/shu/guanyu.png` |
| `general.lvbu` | `assets/generals/qun/lvbu.png` |

下列 20 个 ID 已进入武将名录，**尚无正式半身像，也没有加入 `assets/manifest.json`**。界面当前使用 `ResourceManager` 的确定性姓名占位图；它们不能计入 T7 美术验收：

| 势力 | 待制作资源 ID |
| --- | --- |
| 魏 | `general.simayi`, `general.xiahou_dun`, `general.zhangliao`, `general.xuchu`, `general.guojia`, `general.zhenji` |
| 蜀 | `general.zhangfei`, `general.zhugeliang`, `general.zhaoyun`, `general.machao`, `general.huangyueying` |
| 吴 | `general.ganning`, `general.lvmeng`, `general.huanggai`, `general.zhouyu`, `general.daqiao`, `general.luxun`, `general.sunshangxiang` |
| 群 | `general.huatuo`, `general.diaochan` |

后续 20 张应使用原创水墨与工笔混合风格，统一构图、适配竖向裁切，并逐项写入 manifest 后再标记为完成。

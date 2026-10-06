# T18B 最终103将验收

状态：COMPLETE。本地103将开发与验收已完成，未部署、未合并生产分支、未修改公网配置。验收依据保存在本目录及 docs/t17c。

1. **最终提交**：本报告所属提交，标题 `T18B complete 103-general roster and presentation`；实际提交哈希见最终交付消息或 `git log -1`。
2. **分支**：`t17c-remaining-generals`，从用户指定基线 `e34ae2e` 继续；保留原T18A.9功能。
3. **正式将池**：103/103，普通将91、神将12；四新神直接进入正常将池，未恢复God选择开关。
4. **YJ2012**：12/12，荀攸、王异、曹彰、钟会、廖化、关兴张苞、马岱、步练师、程普、韩当、刘表、华雄。
5. **YJ2013**：11/11，曹冲、郭淮、满宠、关平、简雍、刘封、潘璋马忠、虞翻、朱然、伏皇后、李儒。
6. **四神将**：4/4，神刘备、神陆逊、神甘宁、神张辽。
7. **技能**：50个条目（49个新增定义，马术复用；钟会觉醒获得排异）。逐将列表见下表，确定性规则测试与完整对局已通过。
8. **版本**：遵守T17A.1既有版本锁。钟会经典权计/自立/排异，刘表修订经典自守/宗室；神刘备6HP龙怒/结营，神陆逊军略/摧克/绽火，神甘宁初始3/上限6魄袭/劫营，神张辽经典夺技能夺锐/止啼。未单独锁定的普通将以冻结QSanguosha-v2 `e8768851bd8054db9fd1b63cd6f1feca813590d7` 的经典行为为参考；四神对照冻结Noname `e18a8256e01ab1357e4c7472349dceb3d0aa1a3a`。这些社区源码作为行为参考，不声称官方仲裁。UI说明已改为原创简明释义。
9. **重点风险**：装备废栏进入真实状态，装备移动、使用、距离、范围与技能均尊重废栏；夺锐借技/原主失效按到期及死亡归还，止啼恢复栏位。权计牌区、自立单次觉醒、排异移动与伤害可恢复。魄袭只对合法查看者展示手牌。求援共用杀目标队列和伤害流程；纵玄先预留再置顶，未选牌才进入弃牌触发；巧说共用实体/虚拟牌效果及目标调整。胆守成本排除支付后失去全部合法目标的组合，已验证原死循环种子14。Web高速AI通过已有预算分批发送，预算边界新的人类请求继续派发，原断线种子1已修复。
10. **普通立绘**：23/23原创静态立绘，源1024×1536 PNG、PySide768×1152 PNG、Web600×900 WebP，尺寸和源SHA256全部核对。
11. **设计表**：[portrait_design.md](portrait_design.md)，23张分别记录动作、镜头、色彩、道具、环境、光线与独立构图；参考项目张角和神诸葛亮既有风格。
12. **美术QA**：[portrait_qa.json](portrait_qa.json) 23项visual_pass；复查头部、主体大小、脸手、武器、额外肢体、盔甲、水印、现代物体与构图差异。关兴张苞、潘璋马忠各保持一张完整双人构图。拼图：[ordinary_contact_sheet.png](ordinary_contact_sheet.png)。
13. **四Master映射**：见下表及 [god_sources.json](god_sources.json)。四个源文件SHA256与接入前记录一致。
14. **Panel视频**：4/4，360×640，使用现有动态注册和播放器。
15. **Detail视频**：4/4，720×1280，H.264、24fps、yuv420p、无音频、faststart；仅尺寸/格式转码，保留用户动画与背景。
16. **回退**：四个对应Master首帧静态回退，播放前后人物一致；Web减少动态效果时回退、PySide沿用静态架构。手机拼图：[browser_gods_contact_sheet.png](browser_gods_contact_sheet.png)。
17. **注册一致性**：Python/Web HTTP/Worker/draft/PySide各103/103；源、Web public及dist三个manifest各103，200个固定种子选将覆盖103个ID，111个共享Python文件与Worker镜像一致。[registry_consistency.json](registry_consistency.json)。
18. **Projection**：依法可见的私有选牌和查看手牌使用现有投影/请求流程；权牌公开规则依冻结版本，普通对手手牌保持不透明。规则测试及AI对局共执行8723次投影检查，无崩溃；既有隐藏身份/手牌置换不影响AI目标的测试通过。
19. **reconnect**：多阶段选择、临时牌池、有序选牌、标记、觉醒与废栏保存于权威快照；AI对局执行97次中局快照恢复。浏览器刷新恢复纵玄已选顺序、魄袭授权手牌与夺锐选栏，未提交选择不会自动提交。
20. **AI**：延续既有AI，增添公开态度、体力、资源及技能成本的最小启发式；巧说增益优先友方、胆守使用合法成本。无需新搜索框架。
21. **五人AI**：30/30完整结束，正式103将池，固定种子17000–17029。
22. **八人AI**：30/30完整结束，固定种子18000–18029；27新将全覆盖，无挂起请求、决策错误、重复觉醒、非法装备栏或无限循环。[ai_acceptance.json](ai_acceptance.json)。
23. **full pytest**：1448 passed，409.33秒，[pytest_latest.log](../t17c/pytest_latest.log)。包含规则、UI、TCP、relay、FastAPI WebSocket、隐藏信息和Worker镜像回归。
24. **Vitest**：92 passed / 15 files，[vitest_latest.log](../t17c/vitest_latest.log)。
25. **Playwright**：新验收11/11，旧T18A.9回归10/10，实际安装Edge、FastAPI生产dist；全程使用正式103将HTTP目录。[playwright_report.json](playwright_report.json)、[t18a9_regression.log](t18a9_regression.log)。两套验收按顺序运行，使用独立输出，消除旧共享追踪目录冲突。
26. **TypeScript**：`tsc -b` 通过，构建命令退出成功。
27. **fresh Vite**：重新同步正式资源并构建成功，[build_latest.log](../t17c/build_latest.log)。
28. **production assets**：真实HTTP103/103立绘/回退、43/43卡牌、13套动态（旧9+新4，Panel与Detail）。图片200、非空、正确MIME；所有视频200和1024字节Range206检查通过。[production_asset_smoke.log](production_asset_smoke.log)，动态检查见Playwright首项。
29. **mobile**：390×844、430×932，两种尺寸覆盖全部23普通详情、四神播放/循环/缩放/回退、选将及复杂请求，无阻塞横向溢出。[browser/](browser/)。
30. **PySide**：55项专项验收通过：27将立绘/卡片/详情、27将真实十选一确认及开局、借技技能栏。既有魄袭私有牌面与纵玄顺序交互测试也通过；神将保持静态回退架构。
31. **remaining issues**：无已知阻塞问题。规则与美术自动验收的实际覆盖和日志如上；未进行公网部署、生产合并或下一批扩将。用户原有无关动画实验文件保持未纳入提交。

## 全部技能

| 将包 | 武将 | 已实现技能 |
|---|---|---|
| yj2012 | 荀攸 | 奇策（qice）、智愚（zhiyu） |
| yj2012 | 王异 | 贞烈（zhenlie）、秘计（miji） |
| yj2012 | 曹彰 | 将驰（jiangchi） |
| yj2012 | 钟会 | 权计（quanji）、自立（zili）、排异（paiyi） |
| yj2012 | 廖化 | 当先（dangxian）、伏枥（fuli） |
| yj2012 | 关兴张苞 | 父魂（fuhun） |
| yj2012 | 马岱 | 马术（mashu）、潜袭（qianxi） |
| yj2012 | 步练师 | 安恤（anxu）、追忆（zhuiyi） |
| yj2012 | 程普 | 疠火（lihuo）、醇醪（chunlao） |
| yj2012 | 韩当 | 弓骑（gongqi）、解烦（jiefan） |
| yj2012 | 刘表 | 自守（zishou）、宗室（zongshi） |
| yj2012 | 华雄 | 恃勇（shiyong） |
| yj2013 | 曹冲 | 称象（chengxiang）、仁心（renxin） |
| yj2013 | 郭淮 | 精策（jingce） |
| yj2013 | 满宠 | 峻刑（junxing）、御策（yuce） |
| yj2013 | 关平 | 龙吟（longyin） |
| yj2013 | 简雍 | 巧说（qiaoshui）、纵适（zongshi_jianyong） |
| yj2013 | 刘封 | 陷嗣（xiansi） |
| yj2013 | 潘璋马忠 | 夺刀（duodao）、暗箭（anjian） |
| yj2013 | 虞翻 | 纵玄（zongxuan）、直言（zhiyan） |
| yj2013 | 朱然 | 胆守（danshou） |
| yj2013 | 伏皇后 | 惴恐（zhuikong）、求援（qiuyuan） |
| yj2013 | 李儒 | 绝策（juece）、灭计（mieji）、焚城（fencheng） |
| new_gods | 神刘备 | 龙怒（longnu）、结营（jieying_liubei） |
| new_gods | 神陆逊 | 军略（junlve）、摧克（cuike）、绽火（zhanhuo） |
| new_gods | 神甘宁 | 魄袭（poxi）、劫营（jieying_ganning） |
| new_gods | 神张辽 | 夺锐（duorui）、止啼（zhiti） |

## 用户动画映射

| 武将ID | 用户Master | Panel | Detail |
|---|---|---|---|
| `shadow_god_liubei` | `god_liubei_idle.mp4` | 360×640 H.264 | 720×1280 H.264 |
| `shadow_god_luxun` | `god_luxun_idle.mp4` | 360×640 H.264 | 720×1280 H.264 |
| `thunder_god_ganning` | `god_ganning_idle.mp4` | 360×640 H.264 | 720×1280 H.264 |
| `thunder_god_zhangliao` | `god_zhangliao_idle.mp4` | 360×640 H.264 | 720×1280 H.264 |

## 可复现入口

`scripts/acceptance_ai_103.py`：正式池60场完整AI；`scripts/audit_103_roster.py`：目录、manifest、资源规格及Master校验；`scripts/smoke_production_assets.py`：生产HTTP图片。浏览器使用`web/playwright.t18b.config.ts`与既有Edge回归配置；本地audit服务只为测试创建受控房间，不属于部署。

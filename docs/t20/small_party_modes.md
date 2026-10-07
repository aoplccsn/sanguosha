# T20 少人数对战

- 创建房间可选军五、军八、1v1 对决、2v2 小队战。军五/军八继续使用原身份规则。
- 1v1：两座、单武将；玩家A/B公开，无主公技或主公体力加成。沿用标准初始四张手牌与全部现有牌/技能/距离规则，使用种子RNG随机先手。对手死亡获胜，已有死亡技能先按锁定时序结算，然后清空终局请求与行动栈。
- 2v2：四座，p1/p3为A队、p2/p4为B队，默认回合1→2→3→4。一名队友死亡继续战斗，整队阵亡才结束。没有身份奖惩、复活、换将。队伍绑定原玩家ID，榻谟可改座次但不能换队；势力与队伍独立。
- 加入顺序p1→p2→p3→p4；两个真人默认敌对。开始时仅空位补AI，支持1–4真人。合法队友目标不被服务器禁止。AI使用公开ALLY/ENEMY/SELF关系复用现有评分，救援队友、无懈、AOE与铁索考虑队伍收益；手牌仍私有。
- 正式选将复用十选一、5%超标位与原权重、全局去重和确定性RNG。测试入口仍须服务器验证SANGUOSHA_TEST_ACCESS_CODE；选择模式后自选108将之一，AI补位启动。
- 断线继续使用原宽限期、AI接管、令牌重连和夺回座位。恢复同一队伍、武将和先手；不重新开局。Web小桌使用本地玩家相对视角，沿用原手牌与装备布局；PySide本地模式下拉同步提供四种模式。

## 验证

- `.venv/Scripts/python.exe -m pytest tests/test_t20_small_party.py -q`
- `.venv/Scripts/python.exe scripts/acceptance_ai_t20.py`：各20场完整AI对局，覆盖108将，检查终局、胜者、请求清理、快照恢复。
- `cd web && npx playwright test e2e/t20-small-party.spec.ts`：真实WebSocket选将/开局、双真人敌对、刷新恢复、两个受保护测试模式。
- 完整pytest、Vitest、TypeScript、production Vite build、PySide smoke、Worker镜像一致性与生产HTTP资产检查详见release report。

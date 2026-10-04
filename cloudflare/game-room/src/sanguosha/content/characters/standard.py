"""Classic standard roster and original, concise presentation text.

Registration here describes characters. Rule handlers live in the engine; a
catalogue entry by itself must never be treated as an implemented skill.
"""

from sanguosha.content.characters.classic import CHARACTERS as FIRST_FIVE, SKILLS as FIRST_SKILLS
from sanguosha.model.character import CharacterDefinition
from sanguosha.model.enums import Gender, Kingdom, SkillType
from sanguosha.model.skill import SkillDefinition


ADDITIONAL_CHARACTERS = (
    CharacterDefinition('simayi', '司马懿', Kingdom.WEI, 3, Gender.MALE, ('fankui', 'guicai')),
    CharacterDefinition('xiahou_dun', '夏侯惇', Kingdom.WEI, 4, Gender.MALE, ('ganglie',)),
    CharacterDefinition('zhangliao', '张辽', Kingdom.WEI, 4, Gender.MALE, ('tuxi',)),
    CharacterDefinition('xuchu', '许褚', Kingdom.WEI, 4, Gender.MALE, ('luoyi',)),
    CharacterDefinition('guojia', '郭嘉', Kingdom.WEI, 3, Gender.MALE, ('tiandu', 'yiji')),
    CharacterDefinition('zhenji', '甄姬', Kingdom.WEI, 3, Gender.FEMALE, ('luoshen', 'qingguo')),
    CharacterDefinition('zhangfei', '张飞', Kingdom.SHU, 4, Gender.MALE, ('paoxiao',)),
    CharacterDefinition('zhugeliang', '诸葛亮', Kingdom.SHU, 3, Gender.MALE, ('guanxing', 'kongcheng')),
    CharacterDefinition('zhaoyun', '赵云', Kingdom.SHU, 4, Gender.MALE, ('longdan',)),
    CharacterDefinition('machao', '马超', Kingdom.SHU, 4, Gender.MALE, ('mashu', 'tieqi')),
    CharacterDefinition('huangyueying', '黄月英', Kingdom.SHU, 3, Gender.FEMALE, ('jizhi', 'qicai')),
    CharacterDefinition('ganning', '甘宁', Kingdom.WU, 4, Gender.MALE, ('qixi',)),
    CharacterDefinition('lvmeng', '吕蒙', Kingdom.WU, 4, Gender.MALE, ('keji',)),
    CharacterDefinition('huanggai', '黄盖', Kingdom.WU, 4, Gender.MALE, ('kurou',)),
    CharacterDefinition('zhouyu', '周瑜', Kingdom.WU, 3, Gender.MALE, ('yingzi', 'fanjian')),
    CharacterDefinition('daqiao', '大乔', Kingdom.WU, 3, Gender.FEMALE, ('guose', 'liuli')),
    CharacterDefinition('luxun', '陆逊', Kingdom.WU, 3, Gender.MALE, ('qianxun', 'lianying')),
    CharacterDefinition('sunshangxiang', '孙尚香', Kingdom.WU, 3, Gender.FEMALE, ('jieyin', 'xiaoji')),
    CharacterDefinition('huatuo', '华佗', Kingdom.QUN, 3, Gender.MALE, ('jijiu', 'qingnang')),
    CharacterDefinition('diaochan', '貂蝉', Kingdom.QUN, 3, Gender.FEMALE, ('lijian', 'biyue')),
)

ADDITIONAL_SKILLS = (
    SkillDefinition('fankui', '反馈', '受到伤害后，可取走伤害来源的一张牌。', SkillType.TRIGGERED),
    SkillDefinition('guicai', '鬼才', '判定牌生效前，可用一张手牌替换。', SkillType.TRIGGERED),
    SkillDefinition('ganglie', '刚烈', '受伤后可判定，令伤害来源弃牌或受伤。', SkillType.TRIGGERED),
    SkillDefinition('tuxi', '突袭', '摸牌阶段可改为取得其他角色的手牌。', SkillType.TRIGGERED),
    SkillDefinition('luoyi', '裸衣', '少摸一张牌，使本回合指定伤害增加。', SkillType.TRIGGERED),
    SkillDefinition('tiandu', '天妒', '自己的判定牌结算后可获得。', SkillType.TRIGGERED),
    SkillDefinition('yiji', '遗计', '每受到一点伤害，可摸牌并分配。', SkillType.TRIGGERED),
    SkillDefinition('luoshen', '洛神', '准备阶段可连续判定，获得黑色判定牌。', SkillType.TRIGGERED),
    SkillDefinition('qingguo', '倾国', '可将黑色手牌当闪打出。', SkillType.VIEW_AS),
    SkillDefinition('paoxiao', '咆哮', '出牌阶段使用杀不受次数限制。', SkillType.LOCKED),
    SkillDefinition('guanxing', '观星', '准备阶段可查看并调整牌堆顶的牌。', SkillType.TRIGGERED),
    SkillDefinition('kongcheng', '空城', '没有手牌时，不能成为杀或决斗的目标。', SkillType.LOCKED),
    SkillDefinition('longdan', '龙胆', '杀与闪可互相转化使用或打出。', SkillType.VIEW_AS),
    SkillDefinition('mashu', '马术', '计算与其他角色的距离时少一。', SkillType.LOCKED),
    SkillDefinition('tieqi', '铁骑', '使用杀指定目标后，可判定以限制其闪避。', SkillType.TRIGGERED),
    SkillDefinition('jizhi', '集智', '使用非延时锦囊时可摸一张牌。', SkillType.TRIGGERED),
    SkillDefinition('qicai', '奇才', '使用锦囊牌时不受距离限制。', SkillType.LOCKED),
    SkillDefinition('qixi', '奇袭', '可将黑色牌当过河拆桥使用。', SkillType.VIEW_AS),
    SkillDefinition('keji', '克己', '本回合未使用或打出杀时可跳过弃牌。', SkillType.TRIGGERED),
    SkillDefinition('kurou', '苦肉', '出牌阶段可失去一点体力并摸两张牌。', SkillType.ACTIVE),
    SkillDefinition('yingzi', '英姿', '摸牌阶段额外摸一张牌。', SkillType.LOCKED),
    SkillDefinition('fanjian', '反间', '每阶段一次，令目标猜花色并取得你的牌。', SkillType.ACTIVE),
    SkillDefinition('guose', '国色', '可将方块牌当乐不思蜀使用。', SkillType.VIEW_AS),
    SkillDefinition('liuli', '流离', '成为杀的目标时，可弃牌转移目标。', SkillType.TRIGGERED),
    SkillDefinition('qianxun', '谦逊', '不能成为顺手牵羊或乐不思蜀的目标。', SkillType.LOCKED),
    SkillDefinition('lianying', '连营', '失去最后一张手牌后可摸一张牌。', SkillType.TRIGGERED),
    SkillDefinition('jieyin', '结姻', '弃两张手牌，与受伤男性角色各恢复一点体力。', SkillType.ACTIVE),
    SkillDefinition('xiaoji', '枭姬', '失去装备区的牌后摸两张牌。', SkillType.TRIGGERED),
    SkillDefinition('jijiu', '急救', '回合外可将红色牌当桃使用。', SkillType.VIEW_AS),
    SkillDefinition('qingnang', '青囊', '弃一张手牌，令受伤角色恢复一点体力。', SkillType.ACTIVE),
    SkillDefinition('lijian', '离间', '弃一张牌，令两名男性角色进行决斗。', SkillType.ACTIVE),
    SkillDefinition('biyue', '闭月', '结束阶段可摸一张牌。', SkillType.TRIGGERED),
)

STANDARD_25_GENERAL_POOL = tuple(
    CharacterDefinition(c.id, c.name, c.kingdom, c.max_hp, c.gender, c.skill_ids,
                        {"pack": "standard", "implemented": True, "playable": True,
                         "portrait_mode": "static", "resource_id": f"general.{c.id}"})
    for c in FIRST_FIVE + ADDITIONAL_CHARACTERS
)
STANDARD_SKILL_CATALOGUE = FIRST_SKILLS + ADDITIONAL_SKILLS
assert len(STANDARD_25_GENERAL_POOL) == 25
assert len({character.id for character in STANDARD_25_GENERAL_POOL}) == 25

# T10 keeps the original constant for compatibility while exposing the full
# 65-general catalogue to draft, web, and desktop clients.
from sanguosha.content.characters.myth import MYTH_40_GENERAL_POOL, MYTH_SKILL_CATALOGUE
ALL_65_GENERAL_POOL = STANDARD_25_GENERAL_POOL + MYTH_40_GENERAL_POOL
ALL_SKILL_CATALOGUE = STANDARD_SKILL_CATALOGUE + MYTH_SKILL_CATALOGUE
PLAYABLE_57_GENERAL_POOL = tuple(c for c in ALL_65_GENERAL_POOL if '_god_' not in str(c.id))
GOD_GENERAL_POOL = tuple(c for c in ALL_65_GENERAL_POOL if '_god_' in str(c.id))
PLAYABLE_65_GENERAL_POOL = tuple(c for c in ALL_65_GENERAL_POOL if c.metadata.get('playable', True))
DISABLED_GOD_POOL = tuple(c for c in GOD_GENERAL_POOL if not c.metadata.get('playable', True))
assert len(ALL_65_GENERAL_POOL) == 65
assert len({character.id for character in ALL_65_GENERAL_POOL}) == 65
assert len(PLAYABLE_57_GENERAL_POOL) == 57
assert len(GOD_GENERAL_POOL) == 8
assert len(PLAYABLE_65_GENERAL_POOL) == 65
assert not DISABLED_GOD_POOL



# Historical 57/65 constants remain exact for earlier art/pack audits.
from sanguosha.content.characters.yj2011 import YJ2011_GENERAL_POOL, YJ2011_SKILL_CATALOGUE
ALL_GENERAL_POOL = ALL_65_GENERAL_POOL + YJ2011_GENERAL_POOL
PLAYABLE_GENERAL_POOL = tuple(c for c in ALL_GENERAL_POOL if c.metadata.get('playable', True))
ORDINARY_GENERAL_POOL = tuple(c for c in PLAYABLE_GENERAL_POOL if c not in GOD_GENERAL_POOL)
ALL_SKILL_CATALOGUE = ALL_SKILL_CATALOGUE + YJ2011_SKILL_CATALOGUE
assert len(ALL_GENERAL_POOL) == len(PLAYABLE_GENERAL_POOL) == 76
assert len(ORDINARY_GENERAL_POOL) == 68
assert len({c.id for c in ALL_GENERAL_POOL}) == 76

"""Five Standard-era characters. Descriptions are original short UI summaries."""
from sanguosha.model.character import CharacterDefinition
from sanguosha.model.skill import SkillDefinition
from sanguosha.model.enums import Gender, Kingdom, SkillType

CHARACTERS = (
    CharacterDefinition('caocao', '曹操', Kingdom.WEI, 4, Gender.MALE, ('jianxiong', 'hujia')),
    CharacterDefinition('liubei', '刘备', Kingdom.SHU, 4, Gender.MALE, ('rende', 'jijiang')),
    CharacterDefinition('sunquan', '孙权', Kingdom.WU, 4, Gender.MALE, ('zhiheng', 'jiuyuan')),
    CharacterDefinition('lvbu', '吕布', Kingdom.QUN, 4, Gender.MALE, ('wushuang',)),
    CharacterDefinition('guanyu', '关羽', Kingdom.SHU, 4, Gender.MALE, ('wusheng',)),
)

SKILLS = (
    SkillDefinition('jianxiong', '奸雄', '受到牌造成的伤害后，可获得仍可取得的材料牌。', SkillType.TRIGGERED),
    SkillDefinition('hujia', '护驾', '需要闪时，可请求其他魏势力角色代为提供。', SkillType.TRIGGERED, {'lord': True}),
    SkillDefinition('rende', '仁德', '出牌阶段交给其他角色手牌；本阶段累计交出两张后恢复一点体力。', SkillType.ACTIVE),
    SkillDefinition('jijiang', '激将', '需要杀时，可请求其他蜀势力角色代为提供。', SkillType.TRIGGERED, {'lord': True}),
    SkillDefinition('zhiheng', '制衡', '出牌阶段限一次，弃任意张牌并摸等量牌。', SkillType.ACTIVE),
    SkillDefinition('jiuyuan', '救援', '濒死时其他吴势力角色用桃救援，额外恢复一点体力。', SkillType.LOCKED, {'lord': True}),
    SkillDefinition('wusheng', '武圣', '红色牌可作为杀使用或打出。', SkillType.VIEW_AS),
    SkillDefinition('wushuang', '无双', '杀需两闪，决斗中对手每次需两杀。', SkillType.LOCKED),
)

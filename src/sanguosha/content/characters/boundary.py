"""First mobile boundary-break batch; rules locked in docs/t22/official_rules.md."""
from sanguosha.model.character import CharacterDefinition
from sanguosha.model.skill import SkillDefinition
from sanguosha.model.enums import Gender, Kingdom, SkillType

VERSION = '大陆三国杀移动版身份场官网口径（2026-10-11核对）'
def character(key, name, kingdom, hp, skills, page, **extra):
    return CharacterDefinition('boundary_' + key, '界' + name, kingdom, hp, Gender.MALE,
        skills, {'pack': 'boundary', 'expansion': '界限突破', 'implemented': True,
        'playable': True, 'development_only': False, 'portrait_mode': 'static',
        'resource_id': 'general.boundary_' + key, 'version': VERSION,
        'source_url': 'https://www.sanguosha.cn/pc/hero-detail-' + str(page) + '.html', **extra})
def skill(key, name, text, kind, page, **extra):
    return SkillDefinition(key, name, text, kind, {'pack': 'boundary', 'version': VERSION,
        'source_url': 'https://www.sanguosha.cn/pc/hero-detail-' + str(page) + '.html', **extra})

BOUNDARY_GENERAL_POOL = (
    character('xu_sheng', '徐盛', Kingdom.WU, 4, ('jie_pojun',), 356),
    character('ling_tong', '凌统', Kingdom.WU, 4, ('jie_xuanfeng',), 365),
    character('zhang_fei', '张飞', Kingdom.SHU, 4, ('jie_paoxiao', 'jie_tishen'), 154),
)
BOUNDARY_SKILL_CATALOGUE = (
    skill('jie_pojun', '破军', '使用杀指定目标后，可以扣置其手牌或装备，张数不超过其当前体力；当前回合结束归还其手牌区。杀造成伤害时，若目标的手牌数和装备数分别都不多于你，此伤害增加1。', SkillType.TRIGGERED, 356),
    skill('jie_xuanfeng', '旋风', '失去一次装备区的牌后，或弃牌阶段结束且本阶段弃置至少两张牌时，可以弃置其他角色共计至多两张牌，或将一名其他角色的一张装备移至另一名其他角色的对应空装备栏。', SkillType.TRIGGERED, 365),
    skill('jie_paoxiao', '咆哮', '锁定技。使用杀没有次数上限；本出牌阶段使用过杀后，本阶段后续杀不受距离限制。', SkillType.LOCKED, 154),
    skill('jie_tishen', '替身', '出牌阶段结束时，可以弃置自己全部锦囊和坐骑牌。直到下个自己的回合开始，获得以自己为目标且未对自己造成伤害的杀的可获得材料牌。', SkillType.TRIGGERED, 154),
)

BOUNDARY_GENERAL_POOL += (
    character('fa_zheng', '法正', Kingdom.SHU, 3, ('jie_enyuan', 'jie_xuanhuo'), 134),
    character('wei_yan', '魏延', Kingdom.SHU, 4, ('jie_kuanggu', 'jie_qimou'), 308),
    character('zhu_ran', '朱然', Kingdom.WU, 4, ('jie_danshou',), 389),
)
BOUNDARY_SKILL_CATALOGUE += (
    skill('jie_enyuan', '恩怨', '一次获得另一名角色至少两张牌后，可以令其摸一张；每受到一点伤害，可以令伤害来源交给你一张手牌，否则来源失去一点体力。', SkillType.TRIGGERED, 134),
    skill('jie_xuanhuo', '眩惑', '摸牌阶段可以替代正常摸牌，令另一名角色摸两张。由你选择其攻击范围内另一目标，令受益者使用一张杀；若不使用，你获得受益者两张牌。', SkillType.TRIGGERED, 134),
    skill('jie_kuanggu', '狂骨', '造成伤害时，在目标因该伤害扣减体力前检查距离；距离不大于1时，每一点伤害可以独立选择回复一点体力或摸一张牌。', SkillType.TRIGGERED, 308),
    skill('jie_qimou', '奇谋', '限定技。自己的出牌阶段，可以选择失去X点体力；当前回合到其他角色的距离减少X，杀次数上限增加X。失去体力不视为伤害。', SkillType.LIMITED, 308, limited=True),
    skill('jie_danshou', '胆守', '其他角色结束阶段，若本回合未成为其使用牌的目标，摸一张；否则可以弃置X张牌，对其造成一点伤害。X为本回合成为其使用牌目标的次数。', SkillType.TRIGGERED, 389),
)

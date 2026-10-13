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
    skill('jie_xuanfeng', '旋风', '失去一次装备区的牌后，或弃牌阶段结束且本阶段弃置至少两张牌时，可以弃置至多两名其他角色共计两张牌，或将一名其他角色的一张装备移至另一名其他角色的对应空装备栏。', SkillType.TRIGGERED, 365),
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

BOUNDARY_GENERAL_POOL += (
    character('zhong_hui', '钟会', Kingdom.WEI, 4, ('jie_quanji', 'jie_zili', 'jie_paiyi'), 368, derived_skills=('jie_paiyi',)),
    character('li_ru', '李儒', Kingdom.QUN, 3, ('jie_juece', 'jie_mieji', 'jie_fencheng'), 383),
    character('ju_shou', '沮授', Kingdom.QUN, 3, ('jie_jianying', 'jie_shibei'), 492, initial_hp=2, initial_shield=3, initial_state_source='https://www.sanguosha.cn/pc/news-detail-1445.html'),
    character('cao_xiu', '曹休', Kingdom.WEI, 4, ('jie_qianju', 'jie_qingxi'), 560),
)
BOUNDARY_SKILL_CATALOGUE += (
    skill('jie_quanji', '权计', '每受到一点伤害后，或出牌阶段结束时手牌数多于体力值，可以摸一张，再将一张手牌存为权。手牌上限增加权的数量。', SkillType.TRIGGERED, 368),
    skill('jie_zili', '自立', '觉醒技。准备阶段权至少三张时，先选择回复一点体力或摸两张，再减少一点体力上限并获得排异。每局只觉醒一次。', SkillType.AWAKENING, 368, awakening=True),
    skill('jie_paiyi', '排异', '每个出牌阶段一次。弃置一张权，令一名角色摸两张；若其手牌随后多于你，对其造成一点伤害。', SkillType.ACTIVE, 368),
    skill('jie_juece', '绝策', '结束阶段，可以选择本回合失去过牌的一名其他角色，对其造成一点伤害。', SkillType.TRIGGERED, 383),
    skill('jie_mieji', '灭计', '每个出牌阶段一次。展示一张黑色锦囊手牌置于牌堆顶，令有牌的其他角色交给你一张锦囊手牌，或依次弃置两张非锦囊牌；非锦囊不足两张则弃置现有的牌。', SkillType.ACTIVE, 383),
    skill('jie_fencheng', '焚城', '限定技。出牌阶段，从下家开始依座次令其他角色依次选择：弃置至少X张牌，或受到你造成的两点火焰伤害。X为上一目标实际弃牌数加一，首个目标X为一。', SkillType.LIMITED, 383, limited=True),
    skill('jie_jianying', '渐营', '出牌阶段使用的牌与本阶段前一使用牌花色或点数一致时，可以摸一张。每出牌阶段一次，可以将一张手牌或装备当任意基本牌使用；若前一使用牌有花色，转化牌继承其花色。', SkillType.VIEW_AS, 492),
    skill('jie_shibei', '矢北', '锁定技。每个回合内第一次受到伤害后，回复一点体力；此后每次受到伤害后，失去一点体力。次数按伤害事件计，不按伤害点数计。', SkillType.LOCKED, 492),
    skill('jie_qianju', '千驹', '锁定技。计算到其他角色的距离时，减去自己已损失的体力值。', SkillType.LOCKED, 560),
    skill('jie_qingxi', '倾袭', '每回合一次。对其他角色造成伤害时，可以令其弃置Y张手牌，否则该次伤害增加一。Y取一与四减去你到目标距离之中的较大值。', SkillType.TRIGGERED, 560),
)

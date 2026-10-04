"""Development-only locked YJ2011 metadata; never a production draft pool."""
from sanguosha.model.character import CharacterDefinition
from sanguosha.model.skill import SkillDefinition
from sanguosha.model.enums import Gender, Kingdom, SkillType

YJ2011_DEV_GENERALS = (
    CharacterDefinition('yj2011_zhang_chunhua', '张春华', Kingdom.WEI, 3, Gender.FEMALE, ('jueqing', 'shangshi'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_zhang_chunhua', 'portrait_mode': 'static', 'development_only': True, 'version': '经典OL/身份局张春华：绝情、伤逝（已损失体力，不设2张上限）'}),
    CharacterDefinition('yj2011_yu_jin', '于禁', Kingdom.WEI, 4, Gender.MALE, ('yizhong',), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_yu_jin', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_cao_zhi', '曹植', Kingdom.WEI, 3, Gender.MALE, ('luoying', 'jiushi'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_cao_zhi', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_fa_zheng', '法正', Kingdom.SHU, 3, Gender.MALE, ('enyuan', 'xuanhuo'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_fa_zheng', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_ma_su', '马谡', Kingdom.SHU, 3, Gender.MALE, ('xinzhan', 'huilei'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_ma_su', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_xu_shu', '徐庶', Kingdom.SHU, 3, Gender.MALE, ('wuyan', 'jujian'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_xu_shu', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_ling_tong', '凌统', Kingdom.WU, 4, Gender.MALE, ('xuanfeng',), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_ling_tong', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_xu_sheng', '徐盛', Kingdom.WU, 4, Gender.MALE, ('pojun',), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_xu_sheng', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_wu_guotai', '吴国太', Kingdom.WU, 3, Gender.FEMALE, ('ganlu', 'buyi'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_wu_guotai', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_chen_gong', '陈宫', Kingdom.QUN, 3, Gender.MALE, ('mingce', 'zhichi'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_chen_gong', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
    CharacterDefinition('yj2011_gao_shun', '高顺', Kingdom.QUN, 4, Gender.MALE, ('xianzhen', 'jinjiu'), {'pack': 'yj2011', 'expansion': '一将成名2011', 'implemented': False, 'playable': False, 'resource_id': 'general.yj2011_gao_shun', 'portrait_mode': 'static', 'development_only': True, 'version': 'QS-v2经典原版修订档案 @ e8768851bd8054db9fd1b63cd6f1feca813590d7'}),
)

YJ2011_DEV_SKILLS = (
    SkillDefinition('jueqing', '绝情', '锁定技。伤害结算开始前，你将要造成的伤害视为失去体力。', SkillType.LOCKED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('shangshi', '伤逝', '每当你的手牌数、体力值或体力上限改变后，若你的手牌数小于X，你可以将手牌补至X张。（X为你已损失的体力值）', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('yizhong', '毅重', '锁定技。若你的装备区没有防具牌，黑色【杀】对你无效。', SkillType.LOCKED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('luoying', '落英', '其他角色的牌因判定或弃置而置入弃牌堆时，你可以获得其中至少一张梅花牌。', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('jiushi', '酒诗', '若你的武将牌正面朝上，你可以将武将牌翻面，视为你使用了一张【酒】。每当你受到伤害扣减体力前，若武将牌背面朝上，你可以在伤害结算后将武将牌翻至正面朝上。', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('enyuan', '恩怨', '每当你获得一名其他角色的两张或更多的牌后，你可以令其摸一张牌。每当你受到1点伤害后，你可以令伤害来源选择一项：交给你一张手牌，或失去1点体力。', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('xuanhuo', '眩惑', '摸牌阶段开始时，你可以放弃摸牌并选择一名其他角色：若如此做，该角色摸两张牌，然后该角色可以对其攻击范围内由你选择的一名角色使用一张【杀】，否则令你获得其两张牌。', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('xinzhan', '心战', '阶段技。若你的手牌数大于你的体力上限，你可以观看牌堆顶的三张牌，然后你可以展示并获得其中至少一张红桃牌，然后将其余的牌置于牌堆顶。', SkillType.ACTIVE, {'pack':'yj2011','development_only':True}),
    SkillDefinition('huilei', '挥泪', '锁定技。你死亡时，杀死你的其他角色弃置其所有牌。', SkillType.LOCKED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('wuyan', '无言', '锁定技。每当你造成或受到伤害时，防止锦囊牌的伤害。', SkillType.LOCKED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('jujian', '举荐', '结束阶段开始时，你可以弃置一张非基本牌并选择一名其他角色：若如此做，该角色选择一项：摸两张牌，或回复1点体力，或重置武将牌并将其翻至正面朝上。', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('xuanfeng', '旋风', '每当你失去一次装备区的牌后，或弃牌阶段结束时若你于本阶段内弃置了至少两张你的牌，你可以弃置一名其他角色的一张牌，然后弃置一名其他角色的一张牌。', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('pojun', '破军', '每当你使用【杀】对目标角色造成伤害后，你可以令其摸X张牌，然后将其武将牌翻面。（X为该角色的体力值且至多为5）', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('ganlu', '甘露', '阶段技。你可以令装备区的牌数量差不超过你已损失体力值的两名角色交换他们装备区的装备牌。', SkillType.ACTIVE, {'pack':'yj2011','development_only':True}),
    SkillDefinition('buyi', '补益', '每当一名角色进入濒死状态时，你可以展示该角色的一张手牌：若此牌为非基本牌，该角色弃置此牌，然后回复1点体力。', SkillType.TRIGGERED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('mingce', '明策', '阶段技。你可以将一张装备牌或【杀】交给一名其他角色：若如此做，该角色可以视为对其攻击范围内由你选择的一名角色使用一张【杀】，否则其摸一张牌。', SkillType.ACTIVE, {'pack':'yj2011','development_only':True}),
    SkillDefinition('zhichi', '智迟', '锁定技。你的回合外，每当你受到伤害后，【杀】和非延时锦囊牌对你无效，直到回合结束。', SkillType.LOCKED, {'pack':'yj2011','development_only':True}),
    SkillDefinition('xianzhen', '陷阵', '阶段技。你可以与一名其他角色拼点：若你赢，本回合，该角色的防具无效，你无视与该角色的距离，你对该角色使用【杀】无次数限制；若你没赢，你不能使用【杀】，直到回合结束。', SkillType.ACTIVE, {'pack':'yj2011','development_only':True}),
    SkillDefinition('jinjiu', '禁酒', '锁定技。你的【酒】视为【杀】。', SkillType.LOCKED, {'pack':'yj2011','development_only':True}),
)

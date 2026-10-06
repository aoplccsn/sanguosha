"""T19 current mobile-server general metadata."""
from sanguosha.model.character import CharacterDefinition
from sanguosha.model.skill import SkillDefinition
from sanguosha.model.enums import Gender, Kingdom, SkillType

MOBILE_GENERAL_POOL = (
    CharacterDefinition('mobile_god_guojia', '神郭嘉', Kingdom.QUN, 3, Gender.MALE,
        ('huishi', 'tianyi_guojia', 'huishi_guojia'), {'pack': 'mobile_gods', 'god': True,
        'implemented': True, 'playable': True, 'huashen_eligible': False, 'overpowered': True,
        'resource_id': 'general.mobile_god_guojia', 'portrait_mode': 'static'}),
    CharacterDefinition('mobile_god_xunyu', '神荀彧', Kingdom.QUN, 3, Gender.MALE,
        ('tianzuo', 'lingce', 'dinghan'), {'pack': 'mobile_gods', 'god': True,
        'implemented': True, 'playable': True, 'huashen_eligible': False, 'overpowered': True,
        'resource_id': 'general.mobile_god_xunyu', 'portrait_mode': 'dynamic'}),
    CharacterDefinition('mobile_god_taishici', '神太史慈', Kingdom.QUN, 4, Gender.MALE,
        ('dulie', 'powei', 'shenzhu'), {'pack': 'mobile_gods', 'god': True,
        'implemented': True, 'playable': True, 'huashen_eligible': False, 'overpowered': True,
        'derived_skills': ('shenzhu',), 'resource_id': 'general.mobile_god_taishici', 'portrait_mode': 'dynamic'}),
    CharacterDefinition('mobile_god_sunce', '神孙策', Kingdom.QUN, 6, Gender.MALE,
        ('yingba', 'fuhai', 'pinghe'), {'pack': 'mobile_gods', 'god': True,
        'implemented': True, 'playable': True, 'huashen_eligible': False, 'overpowered': True,
        'initial_hp': 1, 'resource_id': 'general.mobile_god_sunce', 'portrait_mode': 'dynamic'}),
    CharacterDefinition('mobile_god_lusu', '神鲁肃', Kingdom.QUN, 3, Gender.MALE,
        ('tamo', 'dingzhou', 'zhimeng'), {'pack': 'mobile_gods', 'god': True,
        'implemented': True, 'playable': True, 'huashen_eligible': True,
        'resource_id': 'general.mobile_god_lusu', 'portrait_mode': 'dynamic'}),
)
MOBILE_SKILL_CATALOGUE = (
    SkillDefinition('huishi', '慧识', '出牌阶段限一次，上限小于十时连续判定；新花色可加一点上限并继续。最后可交出判定牌，若收牌者手牌最多，你减少一点上限。', SkillType.ACTIVE),
    SkillDefinition('tianyi_guojia', '天翊', '觉醒技，准备阶段全部存活角色都受过伤时，加两点上限、回复一点并令一名角色永久获得佐幸。', SkillType.AWAKENING, {'awakening': True}),
    SkillDefinition('huishi_guojia', '辉逝', '限定技，出牌阶段令一名角色摸四张；若你上限不少于存活人数且其有未觉醒技能，改为令其中一个无视觉醒条件。你减少两点上限。', SkillType.ACTIVE, {'limited': True}),
    SkillDefinition('zuoxing', '佐幸', '出牌阶段限一次，若授予者存活且上限大于一，令其减少一点上限，然后视为使用一张普通锦囊。', SkillType.ACTIVE),
    SkillDefinition('tianzuo', '天佐', '锁定技，游戏开始加入八张奇正相生；奇正相生对你无效。', SkillType.LOCKED),
    SkillDefinition('lingce', '灵策', '实体非转化锦囊被使用时，若是智囊、定汉记录牌或奇正相生，你摸一张牌。', SkillType.LOCKED),
    SkillDefinition('dinghan', '定汉', '未记录锦囊指定你为目标时，记录并取消目标。你的回合开始可增删一种锦囊牌名。', SkillType.TRIGGERED),
    SkillDefinition('dulie', '笃烈', '成为体力值大于你的其他角色使用杀的目标时，判定红桃则取消此目标。', SkillType.LOCKED),
    SkillDefinition('powei', '破围', '使命技：开局其他角色获得围；回合开始围迁往除你之外的下家，受伤移去围。有围角色回合开始，可弃手牌对其造成一点伤害，或其体力不高于你时获得其手牌；此回合你视为在其攻击范围内。你的回合开始无围则成功获得神著；成功前濒死则失败，回复至一、清围并弃装备。', SkillType.TRIGGERED, {'mission': True, 'nontransferable': True, 'transferable': False}),
    SkillDefinition('shenzhu', '神著', '实体非转化杀结算结束后，选择摸一张且本回合杀上限加一，或摸三张且本回合不能使用杀。', SkillType.LOCKED),
    SkillDefinition('yingba', '英霸', '出牌阶段限一次，令另一角色与你各减少一点体力上限，其获得一枚平定。你对有平定的角色使用牌无距离限制。', SkillType.ACTIVE),
    SkillDefinition('fuhai', '覆海', '平定角色不能响应你的牌；对平定角色使用牌摸一张，每回合至多两张。平定角色死亡时，你增加对应标记数的体力上限并摸等量牌。', SkillType.LOCKED),
    SkillDefinition('pinghe', '冯河', '手牌上限为已损失体力。受到其他角色伤害时，若有手牌且上限大于一，防止伤害，减一点上限并交一张手牌给另一角色；拥有英霸时伤害来源获得平定。', SkillType.LOCKED),
    SkillDefinition('tamo', '榻谟', '游戏开始时，可调整所有非主公角色的座次。', SkillType.TRIGGERED),
    SkillDefinition('dingzhou', '定州', '出牌阶段限一次，交给另一角色等同其场上牌数的牌，然后获得其全部场上牌。', SkillType.ACTIVE),
    SkillDefinition('zhimeng', '智盟', '你的回合结束后，可与另一角色将手牌随机均分，你获得向上取整的一半。', SkillType.TRIGGERED),
)

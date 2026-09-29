"""Stable definitions for the Standard + EX + Military physical prints.

Registration describes cards only; executable effects are registered separately.
"""

from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.model.card import CardDefinition
from sanguosha.model.enums import CardCategory, DamageNature, EquipmentSlot
from sanguosha.model.ids import CardDefinitionId


ADDITIONAL_BASICS = (
    ("basic.fire_slash", "火杀", DamageNature.FIRE),
    ("basic.thunder_slash", "雷杀", DamageNature.THUNDER),
    ("basic.wine", "酒", None),
)

TRICKS = (
    ("dismantlement", "过河拆桥"), ("snatch", "顺手牵羊"),
    ("ex_nihilo", "无中生有"), ("duel", "决斗"),
    ("savage_assault", "南蛮入侵"), ("archery_attack", "万箭齐发"),
    ("god_salvation", "桃园结义"), ("amazing_grace", "五谷丰登"),
    ("borrowed_sword", "借刀杀人"), ("nullification", "无懈可击"),
    ("fire_attack", "火攻"), ("iron_chain", "铁索连环"),
)

DELAYED = (
    ("indulgence", "乐不思蜀"), ("lightning", "闪电"),
    ("supply_shortage", "兵粮寸断"),
)

WEAPONS = (
    ("crossbow", "诸葛连弩", 1), ("double_sword", "雌雄双股剑", 2),
    ("qinggang_sword", "青釭剑", 2), ("green_dragon_blade", "青龙偃月刀", 3),
    ("serpent_spear", "丈八蛇矛", 3), ("rock_cleaving_axe", "贯石斧", 3),
    ("halberd", "方天画戟", 4), ("kylin_bow", "麒麟弓", 5),
    ("ice_sword", "寒冰剑", 2), ("ancient_blade", "古锭刀", 2),
    ("vermilion_fan", "朱雀羽扇", 4),
)

ARMORS = (
    ("eight_trigrams", "八卦阵"), ("renwang_shield", "仁王盾"),
    ("vine", "藤甲"), ("silver_lion", "白银狮子"),
)

HORSES = (
    ("jueying", "绝影", EquipmentSlot.DEFENSIVE_HORSE),
    ("zhaohuangfeidian", "爪黄飞电", EquipmentSlot.DEFENSIVE_HORSE),
    ("dilu", "的卢", EquipmentSlot.DEFENSIVE_HORSE),
    ("hualiu", "骅骝", EquipmentSlot.DEFENSIVE_HORSE),
    ("chitu", "赤兔", EquipmentSlot.OFFENSIVE_HORSE),
    ("dayuan", "大宛", EquipmentSlot.OFFENSIVE_HORSE),
    ("zixing", "紫骍", EquipmentSlot.OFFENSIVE_HORSE),
)

WEAPON_EFFECTS = {
    "crossbow": "出牌阶段使用【杀】不受通常次数限制。",
    "double_sword": "对异性目标使用【杀】时，可令其弃一张手牌或令你摸一张牌。",
    "qinggang_sword": "你的【杀】无视目标的防具。",
    "green_dragon_blade": "目标以【闪】抵消【杀】后，可对其继续出【杀】。",
    "serpent_spear": "可将两张手牌作为一张【杀】使用或打出。",
    "rock_cleaving_axe": "【杀】被闪避时，可弃两张牌令其仍造成伤害。",
    "halberd": "最后一张手牌为【杀】时，可额外指定目标。",
    "kylin_bow": "【杀】造成伤害时，可弃置目标的一张坐骑牌。",
    "ice_sword": "【杀】将造成伤害时，可改为弃置目标的牌。",
    "ancient_blade": "【杀】对没有手牌的目标造成伤害时，伤害增加。",
    "vermilion_fan": "普通【杀】可视为火【杀】。",
}
ARMOR_EFFECTS = {
    "eight_trigrams": "需要使用【闪】时，可判定并按结果视为提供【闪】。",
    "renwang_shield": "锁定技：黑色【杀】对你无效。",
    "vine": "锁定技：部分锦囊和普通【杀】对你无效；火焰伤害增加。",
    "silver_lion": "锁定技：单次受到的伤害至多为 1；失去此防具时恢复体力。",
}


def register_additional_definitions(definitions: CardDefinitionRegistry) -> None:
    for key, name, nature in ADDITIONAL_BASICS:
        definitions.register(CardDefinition(CardDefinitionId(key), name, CardCategory.BASIC, nature=nature))
    for key, name in TRICKS:
        definitions.register(CardDefinition(CardDefinitionId(f"trick.{key}"), name, CardCategory.TRICK))
    for key, name in DELAYED:
        definitions.register(CardDefinition(CardDefinitionId(f"delayed.{key}"), name, CardCategory.DELAYED_TRICK))
    for key, name, attack_range in WEAPONS:
        definitions.register(CardDefinition(CardDefinitionId(f"equipment.weapon.{key}"), name,
                                            CardCategory.EQUIPMENT, equipment_slot=EquipmentSlot.WEAPON,
                                            attack_range=attack_range,
                                            metadata={"effect_summary": WEAPON_EFFECTS[key]}))
    for key, name in ARMORS:
        definitions.register(CardDefinition(CardDefinitionId(f"equipment.armor.{key}"), name,
                                            CardCategory.EQUIPMENT, equipment_slot=EquipmentSlot.ARMOR,
                                            metadata={"effect_summary": ARMOR_EFFECTS[key]}))
    for key, name, slot in HORSES:
        definitions.register(CardDefinition(CardDefinitionId(f"equipment.horse.{key}"), name,
                                            CardCategory.EQUIPMENT, equipment_slot=slot,
                                            metadata={"effect_summary":
                                                "其他角色计算到你的距离时 +1。" if slot is EquipmentSlot.DEFENSIVE_HORSE
                                                else "你计算到其他角色的距离时 -1。"}))

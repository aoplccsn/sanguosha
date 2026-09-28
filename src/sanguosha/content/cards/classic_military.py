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
                                            attack_range=attack_range))
    for key, name in ARMORS:
        definitions.register(CardDefinition(CardDefinitionId(f"equipment.armor.{key}"), name,
                                            CardCategory.EQUIPMENT, equipment_slot=EquipmentSlot.ARMOR))
    for key, name, slot in HORSES:
        definitions.register(CardDefinition(CardDefinitionId(f"equipment.horse.{key}"), name,
                                            CardCategory.EQUIPMENT, equipment_slot=slot))

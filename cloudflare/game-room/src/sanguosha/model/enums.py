from enum import StrEnum


class Suit(StrEnum):
    SPADE = "spade"
    HEART = "heart"
    CLUB = "club"
    DIAMOND = "diamond"


class Color(StrEnum):
    RED = "red"
    BLACK = "black"


class CardCategory(StrEnum):
    BASIC = "basic"
    TRICK = "trick"
    DELAYED_TRICK = "delayed_trick"
    EQUIPMENT = "equipment"


class EquipmentSlot(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    OFFENSIVE_HORSE = "offensive_horse"
    DEFENSIVE_HORSE = "defensive_horse"


class DamageNature(StrEnum):
    NORMAL = "normal"
    FIRE = "fire"
    THUNDER = "thunder"


class Kingdom(StrEnum):
    WEI = "wei"
    SHU = "shu"
    WU = "wu"
    QUN = "qun"


class Identity(StrEnum):
    LORD = "lord"
    LOYALIST = "loyalist"
    REBEL = "rebel"
    RENEGADE = "renegade"


class PlayerStatus(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"


class Phase(StrEnum):
    START = "start"
    PREPARATION = "preparation"
    JUDGMENT = "judgment"
    DRAW = "draw"
    PLAY = "play"
    DISCARD = "discard"
    FINISH = "finish"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class SkillType(StrEnum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    LOCKED = "locked"
    VIEW_AS = "view_as"
    LIMITED = "limited"
    RULE_MODIFIER = "rule_modifier"

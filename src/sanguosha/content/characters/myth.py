"""Classic Myth Reborn (Feng Lin Huo Shan) catalogue.

This module intentionally keeps the catalogue data separate from rule handlers.
The metadata records the classic identity-mode wording used by T10 and gives
the UI a stable pack/resource identifier while individual handlers are added.
"""
from sanguosha.model.character import CharacterDefinition
from sanguosha.model.enums import Gender, Kingdom, SkillType
from sanguosha.model.skill import SkillDefinition

_G = Gender.MALE
_F = Gender.FEMALE
_W, _S, _U, _Q, _GOD = Kingdom.WEI, Kingdom.SHU, Kingdom.WU, Kingdom.QUN, Kingdom.QUN

def _c(cid, name, kingdom, hp, gender, skills):
    disabled = "_god_" in f"_{cid}_"
    return CharacterDefinition(cid, name, kingdom, hp, gender, tuple(skills), {
        "pack": cid.split("_", 1)[0], "resource_id": f"general.{cid}",
        "implemented": not disabled, "playable": not disabled,
        "portrait_mode": "animated" if disabled else "static",
    })

MYTH_CHARACTERS = (
    _c('wind_xiahou_yuan','夏侯渊',_W,4,_G,('shensu',)), _c('wind_cao_ren','曹仁',_W,4,_G,('jushou',)),
    _c('wind_huang_zhong','黄忠',_S,4,_G,('liegong',)), _c('wind_wei_yan','魏延',_S,4,_G,('kuanggu',)),
    _c('wind_xiao_qiao','小乔',_U,3,_F,('tianxiang','hongyan')), _c('wind_zhou_tai','周泰',_U,4,_G,('buqu',)),
    _c('wind_zhang_jiao','张角',_Q,3,_G,('leiji','guidao','huangtian')), _c('wind_yuji','于吉',_Q,3,_G,('guhuo',)),
    _c('wind_god_guanyu','神关羽',_GOD,5,_G,('wushen','wuhun')), _c('wind_god_lvmeng','神吕蒙',_GOD,3,_G,('shelie','gongxin')),
    _c('fire_dian_wei','典韦',_W,4,_G,('qiangxi',)), _c('fire_xun_yu','荀彧',_W,3,_G,('quhu','jieming')),
    _c('fire_pang_tong','庞统',_S,3,_G,('lianhuan','niepan')), _c('fire_wolong','卧龙诸葛亮',_S,3,_G,('bazhen','huoji','kanpo')),
    _c('fire_taishi_ci','太史慈',_U,4,_G,('tianyi',)), _c('fire_pang_de','庞德',_Q,4,_G,('mashu','mengjin')),
    _c('fire_yan_liang_wen_chou','颜良文丑',_Q,4,_G,('shuangxiong',)), _c('fire_yuan_shao','袁绍',_Q,4,_G,('luanji','xueyi')),
    _c('fire_god_zhouyu','神周瑜',_GOD,4,_G,('qinyin','yeyan')), _c('fire_god_zhugeliang','神诸葛亮',_GOD,3,_G,('qixing','kuangfeng','dawu')),
    _c('forest_caopi','曹丕',_W,3,_G,('xingshang','fangzhu','songwei')), _c('forest_xuhuang','徐晃',_W,4,_G,('duanliang',)),
    _c('forest_menghuo','孟获',_S,4,_G,('huoshou','zaiqi')), _c('forest_zhurong','祝融',_S,4,_F,('juxiang','lieren')),
    _c('forest_sunjian','孙坚',_U,4,_G,('yinghun',)), _c('forest_lusu','鲁肃',_U,3,_G,('haoshi','dimeng')),
    _c('forest_jia_xu','贾诩',_Q,3,_G,('wansha','luanwu','weimu')), _c('forest_dong_zhuo','董卓',_Q,8,_G,('jiuchi','roulin','benghuai','baonue')),
    _c('forest_god_caocao','神曹操',_GOD,3,_G,('guixin','feiying')), _c('forest_god_lvbu','神吕布',_GOD,5,_G,('kuangbao','wumou','wuwei','shenfen')),
    _c('mountain_zhang_he','张郃',_W,4,_G,('qiaobian',)), _c('mountain_deng_ai','邓艾',_W,4,_G,('tuntian','zaoxian')),
    _c('mountain_liushan','刘禅',_S,3,_G,('xiangle','fangquan','ruoyu')), _c('mountain_jiang_wei','姜维',_S,4,_G,('tiaoxin','zhiji','guanxing')),
    _c('mountain_sunce','孙策',_U,4,_G,('jiang','hunzi','zhiba')), _c('mountain_zhang_zhaozhang','张昭张纮',_U,3,_G,('zhijian','guzheng')),
    _c('mountain_zuoci','左慈',_Q,3,_G,('huashen','xinsheng')), _c('mountain_cai_wenji','蔡文姬',_Q,3,_F,('beige','duanchang')),
    _c('mountain_god_zhaoyun','神赵云',_GOD,2,_G,('juejing','longhun')), _c('mountain_god_simayi','神司马懿',_GOD,4,_G,('renjie','baoyin','lianpo')),
)

_NAMES = {
    'kuangbao':'狂暴','wumou':'无谋','wuwei':'无前','shenfen':'神愤','shensu':'神速','jushou':'据守','liegong':'烈弓','kuanggu':'狂骨','tianxiang':'天香','hongyan':'红颜','buqu':'不屈','leiji':'雷击','guidao':'鬼道','huangtian':'黄天','guhuo':'蛊惑',
}
_WIND_DESCRIPTIONS = {
    'shensu': '你可跳过判定阶段和摸牌阶段，视为使用一张无距离限制的杀；亦可跳过出牌阶段并弃置一张装备牌，视为使用一张无距离限制的杀。两项可分别发动。',
    'jushou': '结束阶段开始时，你可以摸三张牌，然后将武将牌翻面。背面朝上时跳过下个自己的回合并翻回正面。',
    'liegong': '出牌阶段使用杀指定目标后，若其手牌数不小于你的体力值，或不大于你的攻击范围，你可以令其不能以闪响应此杀。',
    'kuanggu': '锁定技。你对距离一以内的角色每造成一点伤害后，回复一点体力。',
    'hongyan': '锁定技。你的黑桃牌视为红桃牌。',
    'tianxiang': '受到伤害前，你可以弃置一张红桃手牌并选择一名其他角色，将此次伤害转移给该角色；结算后其摸等同于已损失体力值的牌。',
    'buqu': '锁定技。濒死时亮出牌堆顶一张牌作为不屈牌；若点数与已有不屈牌均不同，回复至一点体力，否则弃置并继续濒死流程。有不屈牌时手牌上限等于其数量。',
    'leiji': '使用或打出闪时，你可以令一名其他角色判定：黑桃则对其造成两点雷电伤害；梅花则你回复一点体力，再对其造成一点雷电伤害。',
    'guidao': '任意角色的判定牌生效前，你可以打出一张黑色牌替换之。',
    'huangtian': '主公技。其他群势力角色在各自出牌阶段限一次，可以将一张闪或闪电交给你。',
    'guhuo': '你可以扣置一张手牌，声明为基本牌或非延时锦囊牌使用或打出。其他角色依次可质疑；被质疑时展示实体牌，并按真伪结算质疑者失去体力或摸牌。仅真牌且实体牌为红桃时继续生效。',
}
_WIND_TYPES = {
    'jushou': SkillType.TRIGGERED, 'liegong': SkillType.TRIGGERED,
    'kuanggu': SkillType.LOCKED, 'hongyan': SkillType.LOCKED,
    'tianxiang': SkillType.TRIGGERED, 'buqu': SkillType.LOCKED,
    'leiji': SkillType.TRIGGERED, 'guidao': SkillType.TRIGGERED,
    'guhuo': SkillType.VIEW_AS,
}
_FOREST_NAMES = {
    'xingshang': '行殇', 'fangzhu': '放逐', 'songwei': '颂威',
    'duanliang': '断粮', 'huoshou': '祸首', 'zaiqi': '再起',
    'juxiang': '巨象', 'lieren': '烈刃', 'yinghun': '英魂',
    'haoshi': '好施', 'dimeng': '缔盟', 'wansha': '完杀',
    'luanwu': '乱武', 'weimu': '帷幕', 'jiuchi': '酒池',
    'roulin': '肉林', 'benghuai': '崩坏', 'baonue': '暴虐',
}
_FOREST_DESCRIPTIONS = {
    'xingshang': '其他角色死亡时，你可以获得其此时仍拥有的所有牌。',
    'fangzhu': '每受到一次伤害后，你可以令一名其他角色摸等同于你已损失体力值的牌，然后将其武将牌翻面。',
    'songwei': '主公技。其他魏势力角色的黑色判定牌生效后，其可以令你摸一张牌。',
    'duanliang': '你可以将一张黑色基本牌或装备牌当兵粮寸断使用；你使用兵粮寸断的距离限制为二。',
    'huoshou': '锁定技。南蛮入侵对你无效；其他角色使用的南蛮入侵造成伤害时，伤害来源改为你。',
    'zaiqi': '摸牌阶段，若你已受伤，你可以改为亮出等同于已损失体力值的牌；每有一张红桃牌，你回复一点体力，然后获得其余的牌。',
    'juxiang': '锁定技。南蛮入侵对你无效；其他角色使用的南蛮入侵结算结束后，你获得此牌。',
    'lieren': '你使用杀对目标角色造成伤害后，可以与其拼点；若你赢，获得其一张牌。',
    'yinghun': '准备阶段，若你已受伤，你可以令一名其他角色摸X张牌并弃一张牌，或摸一张牌并弃X张牌（X为你已损失体力值）。',
    'haoshi': '摸牌阶段，你可以额外摸两张牌；若摸牌结束后你的手牌数大于五，你须将一半手牌交给一名手牌最少的其他角色。',
    'dimeng': '出牌阶段限一次，你可以弃置等同于两名其他角色手牌数差的牌，令他们交换手牌。',
    'wansha': '锁定技。你的回合内有角色处于濒死状态时，除你和该角色外，其他角色不能使用桃救援。',
    'weimu': '锁定技。你不能成为黑色锦囊牌的目标。',
    'benghuai': '结束阶段开始时，若你的体力值不是全场最低，你须选择失去一点体力或减少一点体力上限。',
    'baonue': '主公技。其他群势力角色造成伤害后，其可以进行判定；若结果为黑桃，你回复一点体力。',
    'luanwu': '限定技。出牌阶段，你可以令其他角色依次对距离最近的合法角色使用一张杀，否则失去一点体力。',
    'jiuchi': '你可以将一张黑桃手牌当酒使用或用于自己濒死时自救。',
    'roulin': '锁定技。你对女性角色使用杀，或女性角色对你使用杀时，目标角色须连续使用两张闪才能抵消。',
}
_FOREST_TYPES = {
    'xingshang': SkillType.TRIGGERED, 'fangzhu': SkillType.TRIGGERED,
    'songwei': SkillType.TRIGGERED, 'duanliang': SkillType.VIEW_AS,
    'huoshou': SkillType.LOCKED, 'zaiqi': SkillType.TRIGGERED,
    'juxiang': SkillType.LOCKED, 'lieren': SkillType.TRIGGERED,
    'yinghun': SkillType.TRIGGERED, 'haoshi': SkillType.TRIGGERED,
    'dimeng': SkillType.ACTIVE, 'wansha': SkillType.LOCKED,
    'luanwu': SkillType.LIMITED, 'weimu': SkillType.LOCKED,
    'jiuchi': SkillType.VIEW_AS, 'roulin': SkillType.LOCKED,
    'benghuai': SkillType.LOCKED, 'baonue': SkillType.TRIGGERED,
}
_MOUNTAIN_NAMES = {
    'qiaobian': '巧变', 'tuntian': '屯田', 'zaoxian': '凿险',
    'xiangle': '享乐', 'fangquan': '放权', 'ruoyu': '若愚',
    'tiaoxin': '挑衅', 'zhiji': '志继', 'jiang': '激昂',
    'hunzi': '魂姿', 'zhiba': '制霸', 'zhijian': '直谏',
    'guzheng': '固政', 'huashen': '化身', 'xinsheng': '新生',
    'beige': '悲歌', 'duanchang': '断肠', 'guanxing': '观星',
}
_MOUNTAIN_DESCRIPTIONS = {
    'qiaobian': '你可以弃置一张手牌跳过判定、摸牌、出牌或弃牌阶段。跳过摸牌阶段时可从至多两名其他角色各获得一张手牌；跳过出牌阶段时可移动场上的一张装备牌或延时锦囊牌。',
    'tuntian': '回合外失去牌后，你可以判定；若结果不为红桃，将判定牌置于武将牌上作为田。你与其他角色的距离减少田的数量。',
    'zaoxian': '觉醒技，准备阶段若田不少于三张，减少一点体力上限并获得急袭。',
    'xiangle': '锁定技，其他角色使用杀指定你为目标时，须额外弃置一张基本牌，否则此杀对你无效。',
    'fangquan': '你可以跳过出牌阶段；若如此，回合结束时可弃置一张手牌，令一名其他角色进行一个额外回合。',
    'ruoyu': '主公技、觉醒技，准备阶段若你的体力值为全场最低，增加一点体力上限、回复一点体力并获得激将。',
    'tiaoxin': '出牌阶段限一次，选择攻击范围内一名其他角色，其须对你使用一张杀，否则你弃置其一张牌。',
    'zhiji': '觉醒技，准备阶段若你没有手牌，选择回复一点体力或摸两张牌，然后减少一点体力上限并获得观星。',
    'jiang': '使用或成为红色杀、决斗的目标时，你可以摸一张牌。',
    'hunzi': '觉醒技，准备阶段若你的体力值为一，减少一点体力上限并获得英姿、英魂。',
    'zhiba': '主公技，其他吴势力角色出牌阶段限一次可与你拼点；你觉醒后可拒绝。若你未赢，可获得双方拼点牌。',
    'zhijian': '出牌阶段，你可以将手牌中的一张装备牌置入其他角色装备区，然后摸一张牌。',
    'guzheng': '其他角色弃牌阶段结束后，你可以将其此阶段因规则弃置的一张牌归还，然后获得其余这些牌。',
    'huashen': '游戏开始获得两张未登场武将牌；准备阶段及结束阶段可选择一张化身及其一项允许的技能，并改变性别和势力。',
    'xinsheng': '受到伤害后，你可以按伤害点数获得新的未登场武将牌。',
    'beige': '其他角色受到杀造成的伤害后，你可以弃置一张牌令其判定：红桃回复，方块摸牌，梅花伤害来源弃牌，黑桃伤害来源翻面。',
    'duanchang': '锁定技，你死亡时，杀死你的角色失去其武将技能。',
    'guanxing': '准备阶段可查看并调整牌堆顶的牌。',
}
_MOUNTAIN_TYPES = {
    'qiaobian': SkillType.TRIGGERED, 'tuntian': SkillType.TRIGGERED,
    'zaoxian': SkillType.TRIGGERED, 'xiangle': SkillType.LOCKED,
    'fangquan': SkillType.TRIGGERED, 'ruoyu': SkillType.TRIGGERED,
    'tiaoxin': SkillType.ACTIVE, 'zhiji': SkillType.TRIGGERED,
    'jiang': SkillType.TRIGGERED, 'hunzi': SkillType.TRIGGERED,
    'zhiba': SkillType.ACTIVE, 'zhijian': SkillType.ACTIVE,
    'guzheng': SkillType.TRIGGERED, 'huashen': SkillType.TRIGGERED,
    'xinsheng': SkillType.TRIGGERED, 'beige': SkillType.TRIGGERED,
    'duanchang': SkillType.LOCKED, 'guanxing': SkillType.TRIGGERED,
}
MYTH_SKILL_CATALOGUE = tuple(SkillDefinition(
    s, _NAMES.get(s, _FOREST_NAMES.get(s, _MOUNTAIN_NAMES.get(s, s))),
    _WIND_DESCRIPTIONS.get(s, _FOREST_DESCRIPTIONS.get(s,
                           _MOUNTAIN_DESCRIPTIONS.get(s, '经典神话再临规则摘要。'))),
    _WIND_TYPES.get(s, _FOREST_TYPES.get(s, _MOUNTAIN_TYPES.get(s, SkillType.ACTIVE))),
    {key: True for key, enabled in (
        ('lord', s in ('huangtian', 'songwei', 'baonue', 'ruoyu', 'zhiba')),
        ('awakening', s in ('zaoxian', 'zhiji', 'hunzi', 'ruoyu', 'baoyin')),
        ('limited', s in ('luanwu', 'niepan', 'yeyan')),
    ) if enabled})
    for c in MYTH_CHARACTERS for s in c.skill_ids) + (
        SkillDefinition('jixi', '急袭', '你可以将一张田当【顺手牵羊】使用。', SkillType.VIEW_AS),
        SkillDefinition('jilue', '极略', '你可以弃一枚忍标记，发动鬼才、放逐、集智、制衡或完杀对应效果。', SkillType.ACTIVE),
    )
MYTH_40_GENERAL_POOL = MYTH_CHARACTERS

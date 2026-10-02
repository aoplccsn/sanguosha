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
MYTH_SKILL_CATALOGUE = tuple(SkillDefinition(s, _NAMES.get(s, s), _WIND_DESCRIPTIONS.get(s, '经典神话再临规则摘要。'), _WIND_TYPES.get(s, SkillType.ACTIVE),
    {'lord': True} if s == 'huangtian' else {}) for c in MYTH_CHARACTERS for s in c.skill_ids)
MYTH_40_GENERAL_POOL = MYTH_CHARACTERS

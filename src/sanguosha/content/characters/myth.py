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
    return CharacterDefinition(cid, name, kingdom, hp, gender, tuple(skills), {"pack": cid.split("_", 1)[0], "resource_id": f"general.{cid}"})

MYTH_CHARACTERS = (
    _c('wind_xiahou_yuan','夏侯渊',_W,4,_G,('shensu',)), _c('wind_cao_ren','曹仁',_W,4,_G,('jushou',)),
    _c('wind_huang_zhong','黄忠',_S,4,_G,('liegong',)), _c('wind_wei_yan','魏延',_S,4,_G,('kuanggu',)),
    _c('wind_xiao_qiao','小乔',_U,3,_F,('tianxiang','hongyan')), _c('wind_zhou_tai','周泰',_U,4,_G,('buj屈'.replace('屈','qu'),)),
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
    _c('mountain_sunce','孙策',_U,4,_G,('jiang','hunzi','zhi霸'.replace('霸','ba'))), _c('mountain_zhang_zhaozhang','张昭张纮',_U,3,_G,('zhijian','guzheng')),
    _c('mountain_zuoci','左慈',_Q,3,_G,('huashen','xinsheng')), _c('mountain_cai_wenji','蔡文姬',_Q,3,_F,('beige','duanchang')),
    _c('mountain_god_zhaoyun','神赵云',_GOD,2,_G,('juejing','longhun')), _c('mountain_god_simayi','神司马懿',_GOD,4,_G,('renjie','baoyin','lianpo')),
)

_NAMES = {
    'shensu':'神速','jushou':'据守','liegong':'烈弓','kuanggu':'狂骨','tianxiang':'天香','hongyan':'红颜','qu':'不屈','leiji':'雷击','guidao':'鬼道','huangtian':'黄天','guhuo':'蛊惑',
}
MYTH_SKILL_CATALOGUE = tuple(SkillDefinition(s, _NAMES.get(s, s), '经典神话再临规则摘要。', SkillType.ACTIVE) for c in MYTH_CHARACTERS for s in c.skill_ids)
MYTH_40_GENERAL_POOL = MYTH_CHARACTERS

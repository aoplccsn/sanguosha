const skillTypes: Record<string, string> = {
  active: '主动技', triggered: '触发技', locked: '锁定技', view_as: '转换技',
  awakening: '觉醒技', limited: '限定技', rule_modifier: '规则技', lord: '主公技',
}
export const skillTypeLabel = (value: string) => skillTypes[value] ?? '技能'

const marks: Record<string, string> = {
  qiaoshui_success:'巧说待用', qiaoshui_trick_lock:'巧说禁锦囊', zhuikong_self_only:'惴恐限自身',
  junlve:'军略', zhanhuo_used:'绽火已用', longnu_form:'龙怒形态', longnu_next:'下次龙怒', poxi_hand_limit:'魄袭减上限', camp:'营',
  yj_gongqi: '弓骑', yj_zishou: '自守', zili_awakened: '自立已觉醒',
  fuli_used: '伏枥已用', jiefan_used: '解烦已用',
  rage: '怒', ren: '忍', wine: '酒', luoyi: '裸衣', hunzi: '魂姿',
  zaoxian: '凿险', zhiji: '志继', ruoyu: '若愚', lianpo: '连破',
  yeyan_used: '业炎已用', niepan_used: '涅槃已用',
}
export const markLabel = (value: string) => marks[value] ?? (value.startsWith('wind:')
  ? '狂风' : value.startsWith('fog:') ? '大雾' : '标记')

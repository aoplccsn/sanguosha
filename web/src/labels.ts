const skillTypes: Record<string, string> = {
  active: '主动技', triggered: '触发技', locked: '锁定技', view_as: '转换技',
  limited: '限定技', rule_modifier: '规则技', lord: '主公技',
}
export const skillTypeLabel = (value: string) => skillTypes[value] ?? '技能'

const marks: Record<string, string> = {
  rage: '怒', ren: '忍', wine: '酒', luoyi: '裸衣', hunzi: '魂姿',
  zaoxian: '凿险', zhiji: '志继', ruoyu: '若愚', lianpo: '连破',
  yeyan_used: '业炎已用', niepan_used: '涅槃已用',
}
export const markLabel = (value: string) => marks[value] ?? (value.startsWith('wind:')
  ? '狂风' : value.startsWith('fog:') ? '大雾' : '标记')

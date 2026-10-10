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

// Reuse battle names and existing server choice labels; never display wire enums.
export function battlePrompt(request: import('./types').PendingRequest, names: Record<string,string>, skills: Record<string,string>, responseTo?:string) {
  const required=request.required_definition_id
  if (request.request_type==='respond_with_card' && required) {
    if (required==='trick.nullification') return '是否使用【无懈可击】？'
    if (required==='basic.peach') return '请使用一张【桃】救援'
    const source=responseTo && names[responseTo]
    return `请打出一张【${names[required] ?? '响应牌'}】${source ? `响应【${source}】` : ''}`
  }
  let prompt=request.prompt
  for (const [id,name] of [...Object.entries(names),...Object.entries(skills)].sort((a,b)=>b[0].length-a[0].length)) prompt=prompt.replaceAll(id,name)
  prompt=prompt.replace(/ViewAs/g,'转换牌').replace(/PendingRequest/g,'等待操作')
  if (!/[a-zA-Z_]{2,}/.test(prompt)) return prompt
  const fallback: Record<string,string> = {yes_no:'是否发动当前技能？',choose_option:'请选择出牌操作，或结束出牌阶段',choose_player:'请选择一名目标角色',choose_players:`请选择 ${request.min_count}～${request.max_count} 名目标角色`,choose_card:'请选择一张牌',choose_cards:`请选择 ${request.min_count} 张牌弃置`,respond_with_card:'请打出响应牌，或选择不出'}
  return fallback[request.request_type] ?? '请完成当前操作'
}

export const phaseNames: Record<string, string> = {
  '—': '回合观察', start: '开始', judgment: '判定', draw: '摸牌', play: '出牌', discard: '弃牌', finish: '结束',
}

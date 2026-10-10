import type { CardView } from '../types'
import { cardImage, defaultCardImage } from '../assets'

export function assetForCard(card: CardView) {
  if (card.definition_id === 'basic.slash') return cardImage('basic/slash')
  if (card.definition_id === 'basic.dodge') return cardImage('basic/dodge')
  if (card.definition_id === 'basic.peach') return cardImage('basic/peach')
  if (/^(basic|trick|delayed)\./.test(card.definition_id)) {
    return cardImage('military/' + card.definition_id)
  }
  if (card.definition_id.startsWith('equipment.')) {
    return cardImage('military/' + card.definition_id + '-v2')
  }
  return defaultCardImage
}

export const cardNames: Record<string, string> = {
  'basic.slash': '杀', 'basic.fire_slash': '火杀', 'basic.thunder_slash': '雷杀',
  'basic.dodge': '闪', 'basic.peach': '桃', 'basic.wine': '酒',
  'trick.nullification': '无懈可击', 'trick.ex_nihilo': '无中生有',
  'trick.dismantlement': '过河拆桥', 'trick.snatch': '顺手牵羊',
  'trick.duel': '决斗', 'trick.fire_attack': '火攻', 'trick.iron_chain': '铁索连环',
  'trick.savage_assault': '南蛮入侵', 'trick.archery_attack': '万箭齐发',
  'trick.god_salvation': '桃园结义', 'trick.amazing_grace': '五谷丰登',
  'trick.borrowed_sword': '借刀杀人',
}

export const equipmentSign = (card: Pick<CardView, 'equipment_slot'>) =>
  card.equipment_slot === 'defensive_horse' ? ' +1' : card.equipment_slot === 'offensive_horse' ? ' -1' : ''

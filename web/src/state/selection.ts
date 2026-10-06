import type { PendingRequest } from '../types'
export interface Selection { requestId: string; cards: string[]; targets: string[]; option: string; mode?: string }
export const emptySelection = (requestId: string): Selection => ({requestId,cards:[],targets:[],option:'',mode:''})
export function virtualOptions(request: PendingRequest | null) {
 return [...new Set([...(request?.choices ?? []),...(request?.eligible_card_ids ?? [])])].filter(o=>o.startsWith('virtual:'))
}
export const materials = (option: string, cardIds: Set<string>) => option.split(':').slice(2).filter(id=>cardIds.has(id))
export function effectiveSelection(saved: Selection, key: string, request: PendingRequest | null, cardIds: Set<string>): Selection {
 if (!request || saved.requestId !== key) return emptySelection(key)
 const options=virtualOptions(request)
 const mode=saved.mode && options.some(o=>o.split(':')[1]===saved.mode) ? saved.mode : ''
 if (saved.mode && !mode) return emptySelection(key)
 const validOptions=[...request.choices,...request.eligible_card_ids]
 let option=validOptions.includes(saved.option) ? saved.option : ''
 const legal=mode ? new Set(options.filter(o=>o.split(':')[1]===mode).flatMap(o=>materials(o,cardIds)))
  : new Set(request.request_type==='choose_option' ? request.choices.filter(o=>o.startsWith('use:')).map(o=>o.slice(4)) : request.eligible_card_ids)
 const cards=saved.cards.filter(id=>legal.has(id))
 if (mode && option && (materials(option,cardIds).length!==cards.length || !materials(option,cardIds).every(c=>cards.includes(c)))) option=''
 const spec=request.play_card_targets?.[option]
 const targets=option===saved.option ? saved.targets.filter(id=>(spec?.targets ?? request.allowed_player_ids).includes(id)) : []
 return {requestId:key,mode,option,cards,targets}
}

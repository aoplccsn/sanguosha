import type { ReactNode } from 'react'
import type { PendingRequest, Projection } from '../types'
import { HandCard } from './GamePage'
import { assetUrl } from '../assets'
import { Timer } from './Timer'

export function TemporaryInteractionPanel({ projection, request, seatId, connected, processing, selected, canConfirm, onSelect, onConfirm, onPass, requestControls }: {
  projection: Projection; request: PendingRequest | null; seatId: string; connected: boolean; processing: boolean
  requestControls?: ReactNode
  selected: string[]; canConfirm: boolean; onSelect(id: string): void; onConfirm(): void; onPass(): void
}) {
  const harvest = projection.shared_cards.length > 0
  const target = projection.players.find(p => p.player_id === request?.subject_player_id)
  const chooser = projection.players.find(p => p.player_id === (harvest ? projection.waiting?.player_id ?? request?.player_id : request?.player_id))
  const active = connected && !processing && request?.player_id === seatId && request.request_type === 'choose_card'
  const eligible = new Set(connected && !processing && request?.player_id === seatId ? request.eligible_card_ids : [])
  const skill = request?.prompt?.match(/【([^】]+)】/)?.[1]
  const title = harvest ? '五谷丰登' : skill ?? (projection.combat?.definition_id === 'trick.dismantlement' ? '过河拆桥' : '顺手牵羊')
  const groups = harvest ? [{ name: '公共牌池', cards: projection.shared_cards }] : [
    { name: '手牌', cards: (target?.revealed_hand ?? []).filter(c => eligible.has(c.card_id)) },
    { name: '装备', cards: target?.equipment ?? [] }, { name: '判定', cards: target?.judgments ?? [] },
  ]
  if (requestControls) groups.push({name:'当前响应手牌', cards:projection.hand.filter(c=>eligible.has(c.card_id))})
  return <div className="temporary-backdrop"><section role="dialog" aria-modal="true" aria-label={title} className="temporary-panel">
    <header><h2>【{title}】</h2><p>{harvest ? `当前选择：${chooser?.name ?? '等待服务器'}` : skill ? request?.prompt : `请选择${title === '过河拆桥' ? '弃置' : '获得'}的一张牌 · 目标：${target?.name ?? ''}`}</p>
      <small>当前回合：{projection.players.find(p => p.active)?.character_name} · 当前响应：{chooser?.character_name ?? '等待服务器'}</small>
      {(request || projection.waiting) && <Timer key={request?.request_id ?? projection.waiting?.key} remainingMs={request?.remaining_ms ?? projection.waiting?.remaining_ms ?? 0} />}
    </header>
    <div className="temporary-content">{groups.map(group => <section key={group.name}><h3>{group.name}</h3><div className="temporary-cards">
      {group.name === '手牌' && request?.eligible_card_ids.filter(id => id.startsWith('hidden-hand:')).map((id, index) => <button key={id} disabled={!active} aria-label={`暗置手牌 ${index + 1}`} className={'hidden-choice' + (selected.includes(id) ? ' selected' : '')} onClick={() => onSelect(id)}><img src={assetUrl('card_back')} alt="牌背" /></button>)}
      {group.cards.map(card => <HandCard key={card.card_id} card={card} selected={selected.includes(card.card_id)} eligible={eligible.has(card.card_id)} onClick={() => eligible.has(card.card_id) && onSelect(card.card_id)} />)}
    </div></section>)}</div>
    <footer>{requestControls ?? (active ? <><button disabled={!canConfirm} onClick={onConfirm}>确认</button>{request?.allow_pass && <button onClick={onPass}>取消</button>}</> : <span>{processing ? '正在提交…' : connected ? '等待当前选择者' : '连接恢复中…'}</span>)}</footer>
  </section></div>
}

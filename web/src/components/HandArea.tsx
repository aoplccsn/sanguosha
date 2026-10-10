import { useState } from 'react'
import type { CardView } from '../types'
import { SuitText } from './SuitText'
import { assetForCard, equipmentSign } from './cardUtil'

export function HandCard({ card, selected, eligible, onClick }: { card: CardView; selected: boolean; eligible: boolean; onClick(): void }) {
  const [showTooltip,setShowTooltip]=useState(false)
  return <button
    onMouseEnter={()=>setShowTooltip(true)} onMouseLeave={()=>setShowTooltip(false)} onFocus={()=>setShowTooltip(true)} onBlur={()=>setShowTooltip(false)}
    className={'hand-card' + (selected ? ' selected' : '') + (!eligible ? ' disabled' : '')}
    data-card-id={card.card_id}
    aria-disabled={!eligible}
    onClick={onClick}
    title={card.details || card.name + ' · ' + card.suit + card.rank}
    aria-label={card.name + ' ' + card.suit + card.rank}
  >
    <img src={assetForCard(card)} alt="" />
    <span className="card-corner"><SuitText suit={card.suit} rank={card.rank} /></span>
    {showTooltip && <span className="hand-card-tooltip" role="tooltip"><SuitText suit={card.suit} rank={card.rank} /> <small>{card.details}</small></span>}
    <strong>{card.name}{equipmentSign(card)}</strong>
  </button>
}

export function SharedCards({ cards, selected, eligible, onSelect }: { cards: CardView[]; selected: string[]; eligible: Set<string>; onSelect(id: string): void }) {
  if (!cards.length) return null
  return <section className="shared-card-pool"><p>五谷公共牌池</p><div>{cards.map((card) =>
    <HandCard key={card.card_id} card={card} selected={selected.includes(card.card_id)} eligible={eligible.has(card.card_id)} onClick={() => onSelect(card.card_id)} />)}</div></section>
}

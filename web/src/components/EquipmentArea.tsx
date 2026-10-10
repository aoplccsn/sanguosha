import type { PlayerView } from '../types'
import { SuitText } from './SuitText'
import { equipmentSign } from './cardUtil'

const slots = [['weapon', '武器'], ['armor', '防具'], ['defensive_horse', '+1马'], ['offensive_horse', '-1马'], ['treasure', '宝物']] as const

// Local equipment, judgment cards and (during ViewAs) the skill-zone materials, kept beside the hand.
export function EquipmentArea({ player, selectedCards, mode, eligible, onToggle }: {
  player: PlayerView; selectedCards: string[]; mode: boolean; eligible(id: string): boolean; onToggle(id: string): void
}) {
  return <section className="equipment-area" aria-label="装备与判定区">
    <div className="equipment-slots">{slots.map(([slot, label]) => {
      const card = player.equipment.find(c => c.equipment_slot === slot)
      if (!card) {
        const abolished = player.abolished_equipment_slots?.includes(slot as never)
        return <div key={slot} className={'equipment-empty slot-' + slot + (abolished ? ' abolished' : '')}>{label}{abolished && <small>已废除</small>}</div>
      }
      const selected = selectedCards.includes(card.card_id), ok = eligible(card.card_id)
      return <button key={slot} aria-label={'装备 ' + card.name} aria-pressed={selected} aria-disabled={!ok}
        className={'equipment-token equipment-choice slot-' + slot + (selected ? ' selected' : '') + (ok ? ' selectable' : ' unavailable')}
        onClick={() => onToggle(card.card_id)} title={card.details}>
        <small>{label}</small><b>{card.name}{equipmentSign(card)}</b><SuitText suit={card.suit} rank={card.rank} />{selected && <span className="selected-check">✓</span>}
      </button>
    })}</div>
    <div className="local-judgments">判定：{player.judgments.length ? player.judgments.map(card => <span key={card.card_id} title={card.details}>{card.name} <SuitText suit={card.suit} rank={card.rank} /></span>) : '无'}</div>
    {mode && <div className="view-as-materials" aria-label="技能区域材料">{Object.values(player.special_piles ?? {}).flat().filter(c => eligible(c.card_id)).map(card =>
      <button key={card.card_id} aria-pressed={selectedCards.includes(card.card_id)} className={selectedCards.includes(card.card_id) ? 'selected' : ''} onClick={() => onToggle(card.card_id)}>{card.name} <SuitText suit={card.suit} rank={card.rank} /></button>)}</div>}
  </section>
}

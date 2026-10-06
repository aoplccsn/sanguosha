import type { PublicEvent } from '../types'
export type GameSpeed = 'slow' | 'normal' | 'fast'
const normal = { ordinary: 4500, key: 4500, impact: 2500, turn: 0, target: 0, skill: 5000 }
const scaled = (factor: number) => Object.fromEntries(Object.entries(normal).map(([key, ms]) => [key, Math.round(ms * factor)])) as typeof normal
export const presentationPacing = { slow: scaled(1.4), normal, fast: scaled(.55) }
export function readGameSpeed(): GameSpeed {
  const value = localStorage.getItem('sanguosha.web.speed')
  return value === 'slow' || value === 'fast' ? value : 'normal'
}
export function eventDuration(event: PublicEvent | null, speed: GameSpeed) {
  const kind = String(event?.kind ?? '')
  if (kind === 'AIThinkingEvent') {
    const base = Number(event?.thinking_ms ?? (event?.complexity === 'simple' ? 1800 : event?.complexity === 'complex' ? 3000 : 2400))
    return Math.round(base * (speed === 'slow' ? 1.4 : speed === 'fast' ? .55 : 1))
  }
  const config = presentationPacing[speed]
  const factor = speed === 'slow' ? 1.4 : speed === 'fast' ? .55 : 1
  if (/^(CardRevealedEvent|DiscardEvent|JudgmentRevealedEvent)$/.test(kind)) return Math.round(2000 * factor)
  if (kind === 'FireAttackResultEvent') return Math.round(1300 * factor)
  if (kind === 'ChainPropagationEvent') return Math.round(900 * factor)
  if (kind === 'EffectTargetEvent') return Math.round(700 * factor)
  if (/Skill|Guhuo/.test(kind)) return Math.round(config.skill * (1 + Math.min(3, Number(event?.level ?? 0)) * .04))
  if (/^(BeforeDamage|AfterDamage|Phase|CardResolved)/.test(kind)) return 0
  if (/DamageDealt|Recovered|Judgment|Skill|Dying|Died|Death/.test(kind)) return Math.round(config.impact * (1 + Math.min(3, Math.max(0, Number(event?.amount ?? 1) - 1)) * .08))
  if (/TurnStarted|TurnEnded/.test(kind)) return config.turn
  if (kind === 'CardUsedEvent' && String(event?.definition_id ?? '').startsWith('equipment.')) return Math.round(3500 * (speed === 'slow' ? 1.4 : speed === 'fast' ? .55 : 1))
  if (/CardUsed|TrickTargetsDeclared/.test(kind)) return config.key
  if (/Responded|VirtualResponse/.test(kind)) return config.ordinary
  if (/Discard|Guhuo/.test(kind)) return config.ordinary
  if (/CardMoved/.test(kind) && /discard/i.test(String(event?.to_zone ?? event?.destination ?? ''))) return config.ordinary
  return 0
}

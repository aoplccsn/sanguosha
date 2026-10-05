import type { PublicEvent } from '../types'
export type GameSpeed = 'slow' | 'normal' | 'fast'
const normal = { ordinary: 1200, key: 1400, impact: 1000, turn: 0, target: 850, skill: 1500 }
const scaled = (factor: number) => Object.fromEntries(Object.entries(normal).map(([key, ms]) => [key, Math.round(ms * factor)])) as typeof normal
export const presentationPacing = { slow: scaled(1.4), normal, fast: scaled(.65) }
export function readGameSpeed(): GameSpeed {
  const value = localStorage.getItem('sanguosha.web.speed')
  return value === 'slow' || value === 'fast' ? value : 'normal'
}
export function eventDuration(event: PublicEvent | null, speed: GameSpeed) {
  const kind = String(event?.kind ?? '')
  if (kind === 'AIThinkingEvent') {
    const base = Number(event?.thinking_ms ?? (event?.complexity === 'simple' ? 2800 : event?.complexity === 'complex' ? 5500 : 4000))
    return Math.round(base * (speed === 'slow' ? 1.4 : speed === 'fast' ? .65 : 1))
  }
  const config = presentationPacing[speed]
  const targets = Array.isArray(event?.target_ids) ? event.target_ids.length : 0
  if (event?.presentation_phase === 'target') return Math.round(config.target * (1 + Math.min(3, Math.max(0, targets - 1)) * .07))
  if (/Skill|Guhuo/.test(kind)) return Math.round(config.skill * (1 + Math.min(3, Number(event?.level ?? 0)) * .04))
  if (/^(BeforeDamage|AfterDamage|Phase|CardResolved)/.test(kind)) return 0
  if (/DamageDealt|Recovered|Judgment|Skill|Dying|Died|Death/.test(kind)) return Math.round(config.impact * (1 + Math.min(3, Math.max(0, Number(event?.amount ?? 1) - 1)) * .08))
  if (/TurnStarted|TurnEnded/.test(kind)) return config.turn
  if (/CardUsed|TrickTargetsDeclared/.test(kind)) return Math.round(config.key * (targets > 2 ? 1.15 : 1))
  if (/Responded|VirtualResponse/.test(kind)) return Math.round(config.ordinary * (Number(event?.response_total ?? 1) > 1 ? (event?.response_number === event?.response_total ? 1.08 : .92) : 1))
  if (/Discard|Guhuo/.test(kind)) return config.ordinary
  if (/CardMoved/.test(kind) && /discard/i.test(String(event?.to_zone ?? event?.destination ?? ''))) return config.ordinary
  return 0
}

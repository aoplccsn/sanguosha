import type { PublicEvent } from '../types'
export type GameSpeed = 'slow' | 'normal' | 'fast'
export const presentationPacing = {
  slow: { ordinary: 2200, key: 3000, impact: 3200, turn: 2600 },
  normal: { ordinary: 1400, key: 2000, impact: 2100, turn: 1700 },
  fast: { ordinary: 600, key: 900, impact: 950, turn: 800 },
} as const
export function readGameSpeed(): GameSpeed {
  const value = localStorage.getItem('sanguosha.web.speed')
  return value === 'slow' || value === 'fast' ? value : 'normal'
}
export function eventDuration(event: PublicEvent | null, speed: GameSpeed) {
  const kind = String(event?.kind ?? '')
  if (kind === 'AIThinkingEvent') {
    const base = event?.complexity === 'simple' ? 1500 : event?.complexity === 'complex' ? 3600 : 2400
    return Math.round(base * (speed === 'slow' ? 1.5 : speed === 'fast' ? .6 : 1))
  }
  const config = presentationPacing[speed]
  if (/^(BeforeDamage|AfterDamage|Phase|CardResolved|TrickTargetsDeclared)/.test(kind)) return 0
  if (/DamageDealt|Recovered|Judgment|Skill|Dying|Died|Death/.test(kind)) return config.impact
  if (/TurnStarted|TurnEnded/.test(kind)) return config.turn
  if (/CardUsed/.test(kind)) return config.key
  if (/Responded|VirtualResponse|Discard|Guhuo/.test(kind)) return config.ordinary
  if (/CardMoved/.test(kind) && /discard/i.test(String(event?.to_zone ?? event?.destination ?? ''))) return config.ordinary
  return 0
}

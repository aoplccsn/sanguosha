import type { PublicEvent } from '../types'
export type GameSpeed = 'slow' | 'normal' | 'fast'
export const presentationPacing = {
  slow: { ordinary: 1050, key: 1450, impact: 1550, turn: 1050 },
  normal: { ordinary: 725, key: 1025, impact: 1100, turn: 725 },
  fast: { ordinary: 300, key: 475, impact: 550, turn: 300 },
} as const
export function readGameSpeed(): GameSpeed {
  const value = localStorage.getItem('sanguosha.web.speed')
  return value === 'slow' || value === 'fast' ? value : 'normal'
}
export function eventDuration(event: PublicEvent | null, speed: GameSpeed) {
  const kind = String(event?.kind ?? '')
  const config = presentationPacing[speed]
  if (/^(BeforeDamage|AfterDamage|Phase|CardResolved|TrickTargetsDeclared)/.test(kind)) return 0
  if (/DamageDealt|Recovered|Judgment|Skill|Dying|Died|Death/.test(kind)) return config.impact
  if (/TurnStarted|TurnEnded/.test(kind)) return config.turn
  if (/CardUsed/.test(kind)) return config.key
  if (/Responded|VirtualResponse|Discard|Guhuo/.test(kind)) return config.ordinary
  if (/CardMoved/.test(kind) && /discard/i.test(String(event?.to_zone ?? event?.destination ?? ''))) return config.ordinary
  return 0
}

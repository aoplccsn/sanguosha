import { describe, expect, it } from 'vitest'
import { GOD_ATTACK_COLORS, godAttackColor } from './GodAttackFX'

describe('GodAttackFX palette', () => {
  it('covers all eight disabled gods with distinct ordinary attack accents', () => {
    expect(Object.keys(GOD_ATTACK_COLORS)).toHaveLength(8)
    expect(new Set(Object.keys(GOD_ATTACK_COLORS).map((id) => godAttackColor(id, 'basic.slash'))).size).toBe(8)
  })
  it('gives Lu Bu separate normal, fire and thunder attack colors', () => {
    const id = 'forest_god_lvbu'
    expect(new Set(['basic.slash', 'basic.fire_slash', 'basic.thunder_slash'].map((card) => godAttackColor(id, card))).size).toBe(3)
    expect(godAttackColor('ordinary_general', 'basic.slash')).toBeNull()
  })
})

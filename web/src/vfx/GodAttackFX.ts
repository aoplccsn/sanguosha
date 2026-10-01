export const GOD_ATTACK_COLORS: Record<string, string> = {
  wind_god_guanyu: '#49c888',
  wind_god_lvmeng: '#65abd9',
  fire_god_zhouyu: '#ed6b39',
  fire_god_zhugeliang: '#a3a9ff',
  forest_god_caocao: '#d3ad6c',
  forest_god_lvbu: '#e04139',
  mountain_god_zhaoyun: '#bce9f2',
  mountain_god_simayi: '#a774d9',
}

export function godAttackColor(characterId: string, definition: string): string | null {
  const base = GOD_ATTACK_COLORS[characterId]
  if (!base) return null
  if (definition === 'basic.fire_slash') return characterId === 'forest_god_lvbu' ? '#ff632d' : '#ef773b'
  if (definition === 'basic.thunder_slash') return characterId === 'forest_god_lvbu' ? '#b37bff' : '#aabaff'
  return base
}

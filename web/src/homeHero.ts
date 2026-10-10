// Home-screen hero themes. Media comes from the existing idle-portrait registry and
// production general portraits; only the accent and lighting differ per hero.
export type HomeHero = {
  id: string
  name: string
  accent: string        // primary accent: title glow, primary button edge, borders
  light: string         // environmental light behind the hero
  heroPosition: string  // object-position inside the hero viewport
  scenePosition: string // background-position of the hall scene
}

export const homeHeroes: Record<string, HomeHero> = {
  zhugeliang: { id: 'fire_god_zhugeliang', name: '神诸葛亮', accent: '#b8c6ee', light: '#6f7fd6', heroPosition: 'center 12%', scenePosition: '78% 50%' },
  lvbu: { id: 'forest_god_lvbu', name: '神吕布', accent: '#e0574a', light: '#b3241a', heroPosition: 'center 10%', scenePosition: '78% 50%' },
  zhouyu: { id: 'fire_god_zhouyu', name: '神周瑜', accent: '#e8754d', light: '#b8401e', heroPosition: 'center 12%', scenePosition: '78% 50%' },
  guanyu: { id: 'wind_god_guanyu', name: '神关羽', accent: '#7fc0a0', light: '#2f7a5c', heroPosition: 'center 10%', scenePosition: '78% 50%' },
  ganning: { id: 'thunder_god_ganning', name: '神甘宁', accent: '#c9d6e6', light: '#2d4a78', heroPosition: 'center 12%', scenePosition: '78% 50%' },
}

export const homeHeroOrder = ['zhugeliang', 'lvbu', 'zhouyu', 'guanyu', 'ganning'] as const
export const defaultHomeHero = 'zhugeliang'

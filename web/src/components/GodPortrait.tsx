import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export type GodPortraitMode = 'idle' | 'entry' | 'attack' | 'hit' | 'dying' | 'victory'

const LU_BU = '/assets/gods/forest_god_lvbu/'
export function GodPortrait({ characterId, name, quality, mode = 'idle' }: {
  characterId: string; name: string; quality: VfxQuality; mode?: GodPortraitMode
}) {
  if (characterId !== 'forest_god_lvbu') return null
  if (quality === 'low') return <img className="god-portrait-static" src={LU_BU + 'portrait.png'} alt={name} />
  return <div className={'god-portrait god-portrait-' + mode + ' god-portrait-' + quality} role="img" aria-label={name}>
    <img className="god-portrait-background" src={LU_BU + 'background.png'} alt="" />
    <img className="god-portrait-body" src={LU_BU + 'body.png'} alt="" />
    {quality === 'high' && <span className="god-portrait-embers" aria-hidden="true" />}
  </div>
}

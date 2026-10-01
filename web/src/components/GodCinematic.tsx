import { useEffect, useState } from 'react'
import { GodPortrait } from './GodPortrait'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export type GodCinematicCue = {
  id: number
  level: 1 | 2 | 3
  nature: 'normal' | 'fire' | 'thunder'
  title?: string
  targetCount: number
}

const duration = { 1: 900, 2: 1200, 3: 2100 } as const

export function GodCinematic({ cue, quality, onComplete }: {
  cue: GodCinematicCue
  quality: VfxQuality
  onComplete(): void
}) {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(preference.matches)
    preference.addEventListener('change', update)
    return () => preference.removeEventListener('change', update)
  }, [])
  useEffect(() => {
    const timer = window.setTimeout(onComplete, reduced ? 240 : duration[cue.level])
    const skip = (event: KeyboardEvent) => { if (event.key === 'Escape') onComplete() }
    window.addEventListener('keydown', skip)
    return () => { window.clearTimeout(timer); window.removeEventListener('keydown', skip) }
  }, [cue.id, cue.level, onComplete, reduced])
  return <div key={cue.id} className={'god-cinematic god-cinematic-level-' + cue.level + ' god-cinematic-' + cue.nature + (reduced ? ' god-cinematic-reduced' : '')}
    style={{ '--cinematic-ms': (reduced ? 240 : duration[cue.level]) + 'ms' } as React.CSSProperties} role="status" aria-label={'神吕布' + (cue.title ?? '攻击') + '演出'}>
    <div className="god-cinematic-dim" />
    <div className="god-cinematic-stage">
      <div className="god-cinematic-backdrop" />
      {cue.level === 3 && <img className="god-cinematic-crest" src="/assets/gods/forest_god_lvbu/shenfen.png" alt="" />}
      <div className="god-cinematic-figure">
        <div className="god-cinematic-ready"><GodPortrait characterId="forest_god_lvbu" name="神吕布" quality={quality === 'low' ? 'medium' : quality} mode="idle" cue={cue.id} /></div>
        <img className="god-cinematic-attack-pose" src="/assets/gods/forest_god_lvbu/attack.png" alt="" />
      </div>
      <div className="god-cinematic-slash" />
      <div className="god-cinematic-impact" aria-hidden="true">{Array.from({ length: Math.min(cue.targetCount, 5) }, (_, index) => <i key={index} />)}</div>
      <div className="god-cinematic-name"><span>神吕布</span><strong>{cue.title ?? (cue.nature === 'fire' ? '火杀' : cue.nature === 'thunder' ? '雷杀' : '杀')}</strong></div>
    </div>
    <button className="god-cinematic-skip" onClick={onComplete} aria-label="跳过神将演出">跳过 Esc</button>
  </div>
}

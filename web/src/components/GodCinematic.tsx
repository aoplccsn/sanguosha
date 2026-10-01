import { useEffect, useState, type CSSProperties } from 'react'
import { GodPortrait } from './GodPortrait'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export type GodCinematicTarget = { id: string; x: number; y: number }
export type GodCinematicCue = {
  id: number
  level: 1 | 2 | 3
  nature: 'normal' | 'fire' | 'thunder'
  title?: string
  targets: GodCinematicTarget[]
}

const duration = { 1: 900, 2: 1200, 3: 2100 } as const

export function GodCinematic({ cue, quality, reducedMotion, onComplete }: {
  cue: GodCinematicCue
  quality: VfxQuality
  reducedMotion?: boolean
  onComplete(): void
}) {
  const [systemReduced, setSystemReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const reduced = reducedMotion ?? systemReduced
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setSystemReduced(preference.matches)
    preference.addEventListener('change', update)
    return () => preference.removeEventListener('change', update)
  }, [])
  const captureHold = import.meta.env.DEV && new URLSearchParams(window.location.search).has('t11_capture')
  useEffect(() => {
    const timer = window.setTimeout(onComplete, captureHold ? 15000 : reduced ? 240 : duration[cue.level])
    const skip = (event: KeyboardEvent) => { if (event.key === 'Escape') onComplete() }
    window.addEventListener('keydown', skip)
    return () => { window.clearTimeout(timer); window.removeEventListener('keydown', skip) }
  }, [cue.id, cue.level, onComplete, reduced, captureHold])
  const imageExtension = quality === 'high' ? '.png' : '_medium.webp'
  const asset = (name: string) => '/assets/gods/forest_god_lvbu/' + name + imageExtension
  const css = { '--cinematic-ms': (reduced ? 240 : duration[cue.level]) + 'ms' } as CSSProperties
  return <div className={'god-cinematic god-cinematic-level-' + cue.level + ' god-cinematic-' + cue.nature + ' god-cinematic-' + quality + (reduced ? ' god-cinematic-reduced' : '')}
    style={css} role="status" aria-label={'神吕布' + (cue.title ?? '攻击') + '演出'}>
    <div className="god-cinematic-dim" />
    <div className="god-cinematic-stage">
      <div className="god-cinematic-backdrop" />
      {cue.level === 3 && <img className="god-cinematic-crest" src={asset('shenfen')} alt="" />}
      {cue.level >= 2 && <div className="god-cinematic-war-spirit" aria-hidden="true"><img src={asset('attack')} alt="" /></div>}
      <div className="god-cinematic-figure">
        <div className="god-cinematic-ready">{quality === 'high' ? <GodPortrait characterId="forest_god_lvbu" name="神吕布" quality="high" mode="idle" cue={cue.id} /> : <img className="god-cinematic-ready-image" src={asset('body')} alt="" />}</div>
        <img className="god-cinematic-attack-pose" src={asset('attack')} alt="" />
      </div>
      <div className="god-cinematic-slash" />
      {cue.nature !== 'normal' && <img className="god-cinematic-elemental" src={asset(cue.nature + '_slash')} alt="" />}
      <div className="god-cinematic-name"><span>神吕布</span><strong>{cue.title ?? (cue.nature === 'fire' ? '火杀' : cue.nature === 'thunder' ? '雷杀' : '杀')}</strong></div>
    </div>
    <div className="god-cinematic-targets" aria-hidden="true">{cue.targets.map((target, index) =>
      <i key={target.id} data-target-id={target.id} style={{ left: target.x + '%', top: target.y + '%',
        animationDelay: (reduced ? 0 : duration[cue.level] * (cue.level === 3 ? .55 + index * .08 : .66)) + 'ms' }} />)}</div>
    <button className="god-cinematic-skip" onClick={onComplete} aria-label="跳过神将演出">跳过 Esc</button>
  </div>
}

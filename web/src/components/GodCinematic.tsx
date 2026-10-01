import { useEffect, useState, type CSSProperties } from 'react'
import { GodPortrait } from './GodPortrait'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export type GodCinematicTarget = { id: string; x: number; y: number }
export type GodCinematicCue = {
  id: number
  level: 1 | 2 | 3
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
  // The 960 px medium sheets visibly upscale in a 1080p cinematic.
  // Full resolution source art is shared by High and Medium; Low alone uses compact sheets.
  const imageExtension = quality === 'low' ? '_medium.webp' : '.png'
  const asset = (name: string) => '/assets/gods/forest_god_lvbu/' + name + imageExtension
  const css = { '--cinematic-ms': (reduced ? 240 : duration[cue.level]) + 'ms' } as CSSProperties
  return <div className={'god-cinematic god-cinematic-level-' + cue.level + ' god-cinematic-standard god-cinematic-' + quality + (reduced ? ' god-cinematic-reduced' : '')}
    style={css} role="status" aria-label={'神吕布' + (cue.title ?? '攻击') + '演出'}>
    <div className="god-cinematic-dim" />
    <div className="god-cinematic-stage">
      <div className="god-cinematic-backdrop" />
      {cue.level === 3 && <img className="god-cinematic-crest" src={asset('shenfen')} alt="" />}
      {cue.level >= 2 && <div className="god-cinematic-war-spirit" aria-hidden="true"><img src={asset(quality === 'low' ? 'attack' : 'attack_cutout')} alt="" /></div>}
      <div className="god-cinematic-figure">
        <div className="god-cinematic-ready">{quality === 'low' ? <img className="god-cinematic-ready-image" src={asset('body')} alt="" /> : <GodPortrait characterId="forest_god_lvbu" name="神吕布" quality="high" mode="idle" cue={cue.id} reducedMotion={reduced} compact={quality === 'medium'} />}</div>
        <img className="god-cinematic-attack-pose" src={asset(quality === 'low' ? 'attack' : 'attack_cutout')} alt="" />
      </div>
      <svg className="god-cinematic-blade" viewBox="0 0 1600 700" preserveAspectRatio="none" aria-hidden="true">
        <path className="god-cinematic-blade-outer" d="M 95 590 L 420 360 L 960 158 L 1510 90" />
        <path className="god-cinematic-blade-core" d="M 95 590 L 420 360 L 960 158 L 1510 90" />
        <path className="god-cinematic-blade-edge" d="M 95 590 L 420 360 L 960 158 L 1510 90" />
      </svg>
      <div className="god-cinematic-impact"><i /><i /><i /><i /><i /></div>
      {cue.level === 3 && <div className="god-cinematic-shockwave" aria-hidden="true" />}
      <div className="god-cinematic-name"><span>神吕布</span><strong>{cue.title ?? (cue.level === 3 ? '神愤' : '无双戟击')}</strong></div>
    </div>
    <div className="god-cinematic-targets" aria-hidden="true">{cue.targets.map((target, index) =>
      <i key={target.id} data-target-id={target.id} style={{ left: target.x + '%', top: target.y + '%',
        animationDelay: (reduced ? 0 : duration[cue.level] * (cue.level === 3 ? .55 + index * .08 : .66)) + 'ms' }} />)}</div>
    <button className="god-cinematic-skip" onClick={onComplete} aria-label="跳过神将演出">跳过 Esc</button>
  </div>
}

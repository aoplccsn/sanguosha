import { useState } from 'react'
import { GodPortrait, type GodPortraitMode } from './GodPortrait'
import { GodCinematic, type GodCinematicCue } from './GodCinematic'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export function GodShowcase() {
  const [mode, setMode] = useState<GodPortraitMode>('idle')
  const [quality, setQuality] = useState<VfxQuality>('high')
  const [cue, setCue] = useState(0)
  const [cinematic, setCinematic] = useState<GodCinematicCue | null>(null)
  const play = (value: GodPortraitMode) => { setMode(value); setCue((current) => current + 1) }
  const showAttack = (level: 1 | 2 | 3, nature: 'normal' | 'fire' | 'thunder', title?: string) => {
    setMode('attack')
    setCue((current) => current + 1)
    setCinematic({ id: Date.now(), level, nature, title, targets: (level === 3 ? [
      { id: 'p2', x: 76, y: 24 }, { id: 'p3', x: 87, y: 44 },
      { id: 'p4', x: 73, y: 70 }, { id: 'p5', x: 92, y: 77 },
    ] : [{ id: 'p2', x: 80, y: 49 }]) })
  }
  return <main className="god-showcase">
    <header><p>T11 · 神吕布动态验收预览</p><h1>神吕布</h1><small>仅供美术与动作验收，不进入可玩武将池</small></header>
    <div className="god-showcase-stage">
      <div className="god-showcase-large"><GodPortrait characterId="forest_god_lvbu" name="神吕布" quality={quality} mode={mode} cue={cue} /></div>
      <div className="god-showcase-small"><GodPortrait characterId="forest_god_lvbu" name="神吕布小头像" quality={quality} mode={mode} cue={cue} /></div>
    </div>
    <div className="god-showcase-controls">
      {(['idle', 'entry', 'attack', 'hit', 'dying', 'victory'] as const).map((value) =>
        <button key={value} onClick={() => play(value)}>{value}</button>)}
      <select aria-label="预览画质" value={quality} onChange={(event) => setQuality(event.target.value as VfxQuality)}>
        <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
      </select>
    </div>
    <div className="god-showcase-controls">
      <button onClick={() => showAttack(1, 'normal')}>普通杀全屏</button>
      <button onClick={() => showAttack(1, 'fire')}>火杀全屏</button>
      <button onClick={() => showAttack(1, 'thunder')}>雷杀全屏</button>
      <button onClick={() => showAttack(2, 'normal', '技能强化')}>二级技能演出</button>
      <button onClick={() => showAttack(3, 'normal', '神愤')}>神愤三级演出</button>
    </div>
    {cinematic && <GodCinematic cue={cinematic} quality={quality} onComplete={() => setCinematic(null)} />}
  </main>
}

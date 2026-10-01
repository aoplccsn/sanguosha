import { useEffect, useRef, useState } from 'react'
import type { PlayerView, PublicEvent } from '../types'
import { CombatVFXLayer } from './CombatVFXLayer'
import { GodPortrait, type GodPortraitMode } from './GodPortrait'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

const LU_BU = 'forest_god_lvbu'
const targetArt = [
  { id: 'p2', name: '曹操', image: '/assets/generals/wei/caocao.png' },
  { id: 'p3', name: '刘备', image: '/assets/generals/shu/liubei.png' },
  { id: 'p4', name: '孙权', image: '/assets/generals/wu/sunquan.png' },
  { id: 'p5', name: '吕布', image: '/assets/generals/qun/lvbu.png' },
]

function previewPlayer(id: string, name: string, characterId: string): PlayerView {
  return {
    player_id: id, name, character_name: name, character_id: characterId,
    identity_label: '预览', hp: 4, max_hp: 4, hand_count: 0, alive: true, active: id === 'p1',
    faction: 'qun', chained: false, equipment: [], judgments: [], base_distance: null,
    effective_distance: null, attack_range: 1, skill_labels: [],
  }
}

const players = [previewPlayer('p1', '神吕布', LU_BU),
  ...targetArt.map((target) => previewPlayer(target.id, target.name, target.id))]

export function GodShowcase() {
  const [mode, setMode] = useState<GodPortraitMode>('idle')
  const [quality, setQuality] = useState<VfxQuality>('high')
  const [reducedMotion, setReducedMotion] = useState(false)
  const [forceBlink, setForceBlink] = useState(false)
  const [cue, setCue] = useState(0)
  const [events, setEvents] = useState<PublicEvent[]>([])
  const [beamTargets, setBeamTargets] = useState<string[]>([])
  const [hitTargets, setHitTargets] = useState<string[]>([])
  const [stageKey, setStageKey] = useState(0)
  const nextEvent = useRef(0)
  const timers = useRef(new Set<number>())

  useEffect(() => () => { timers.current.forEach(window.clearTimeout) }, [])

  const later = (callback: () => void, delay: number) => {
    const timer = window.setTimeout(() => { timers.current.delete(timer); callback() }, delay)
    timers.current.add(timer)
  }
  const emit = (items: PublicEvent[]) => setEvents((current) => [...current, ...items.map((item) => ({
    ...item, event_id: 'preview-' + ++nextEvent.current,
  }))].slice(-40))
  const portrait = (next: GodPortraitMode) => { setMode(next); setCue((current) => current + 1) }
  const impact = (id: string) => {
    emit([{ kind: 'DamageDealtEvent', source_id: 'p1', target_id: id, amount: 1 }])
    setHitTargets((current) => [...new Set([...current, id])])
    later(() => setHitTargets((current) => current.filter((target) => target !== id)), 450)
  }
  const playAttack = (definition: string, level: 1 | 2 = 1) => {
    portrait('attack')
    setBeamTargets(['p2'])
    if (level === 2) emit([{ kind: 'GodSkillEvent', source_id: 'p1', target_ids: ['p2'], skill_id: 'wuwei', level: 2 }])
    emit([{ kind: 'CardUsedEvent', source_id: 'p1', target_ids: ['p2'], definition_id: definition }])
    later(() => impact('p2'), level === 2 ? 850 : 620)
    later(() => setBeamTargets([]), level === 2 ? 1250 : 1000)
  }
  const shenfen = () => {
    portrait('attack')
    const targets = targetArt.map((target) => target.id)
    setBeamTargets(targets)
    emit([{ kind: 'GodSkillEvent', source_id: 'p1', target_ids: targets, skill_id: 'shenfen', level: 3 }])
    targets.forEach((id, index) => later(() => impact(id), 1160 + index * 160))
    later(() => setBeamTargets([]), 2200)
  }
  const blink = () => {
    portrait('idle')
    setForceBlink(true)
    later(() => setForceBlink(false), 150)
  }
  const reset = () => {
    timers.current.forEach(window.clearTimeout)
    timers.current.clear()
    setEvents([]); setBeamTargets([]); setHitTargets([]); setForceBlink(false)
    portrait('idle')
    setStageKey((current) => current + 1)
  }

  return <main className={'god-showcase god-presentation-preview' + (reducedMotion ? ' god-preview-reduced' : '')}>
    <header>
      <p>T11.2 · 本地开发视觉验收</p>
      <h1>God Lü Bu Presentation Preview</h1>
      <small>使用当前游戏的 GodPortrait、CombatVFXLayer、GodCinematic 运行组件；按钮只注入视觉事件，不结算伤害或修改规则。</small>
    </header>
    <div className="god-preview-controls" aria-label="神吕布演出控制">
      <button onClick={() => portrait('idle')}>Idle</button>
      <button onClick={blink} disabled={quality === 'low'} title={quality === 'low' ? 'Low 使用静态头像；High / Medium 可观察真实眨眼层' : '也可以在 Idle 中等待自然眨眼'}>Blink</button>
      <button onClick={() => portrait('entry')}>Entry</button>
      <button onClick={() => playAttack('basic.slash')}>Normal Slash</button>
      <button onClick={() => playAttack('basic.fire_slash')}>Fire Slash</button>
      <button onClick={() => playAttack('basic.thunder_slash')}>Thunder Slash</button>
      <button onClick={() => playAttack('basic.slash', 2)}>Level 2</button>
      <button onClick={shenfen}>Shenfen</button>
      <button onClick={() => portrait('hit')}>Hit</button>
      <button onClick={() => portrait('dying')}>Dying</button>
      <button onClick={() => portrait('victory')}>Victory</button>
      <button onClick={reset}>Reset</button>
      <label>Quality <select aria-label="Quality" value={quality} onChange={(event) => setQuality(event.target.value as VfxQuality)}>
        <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
      </select></label>
      <label className="god-preview-toggle"><input type="checkbox" checked={reducedMotion} onChange={(event) => setReducedMotion(event.target.checked)} />Reduced Motion</label>
    </div>
    <div className="god-preview-layout">
      <section className="god-preview-hero" aria-label="神吕布动态立绘">
        <GodPortrait characterId={LU_BU} name="神吕布动态立绘" quality={quality} mode={mode} cue={cue} forceBlink={forceBlink} reducedMotion={reducedMotion} />
        <p>神吕布 · {mode === 'idle' ? '呼吸、头发、衣摆、武器与自然眨眼' : mode.toUpperCase()}</p>
      </section>
      <section className="god-preview-board" aria-label="五人牌桌">
        <div className="god-preview-board-title">五人牌桌 · 轨迹与多目标反馈</div>
        {targetArt.map((target) => <div key={target.id} className={'player-panel god-preview-seat god-preview-' + target.id + (hitTargets.includes(target.id) ? ' god-preview-seat-hit' : '')} data-player-id={target.id}>
          <div className="portrait-button"><img src={target.image} alt={target.name} /></div>
          <strong>{target.name}</strong><small>{target.id}</small>
        </div>)}
        <div className="player-panel player-self god-preview-seat god-preview-p1" data-player-id="p1">
          <div className="portrait-button"><GodPortrait characterId={LU_BU} name="神吕布牌桌头像" quality={quality} mode={mode} cue={cue} forceBlink={forceBlink} reducedMotion={reducedMotion} /></div>
          <strong>神吕布</strong><small>source · p1</small>
        </div>
        <CombatVFXLayer key={stageKey} players={players} targets={beamTargets} mode="attack" events={events} quality={quality} reducedMotion={reducedMotion} />
      </section>
    </div>
    <p className="god-preview-note">按 Esc 或右上角按钮可跳过全屏演出。Reset 清空视觉事件；此页不进入正式选将池。</p>
  </main>
}

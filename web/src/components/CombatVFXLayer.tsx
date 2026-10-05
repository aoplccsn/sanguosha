import { useCallback, useEffect, useRef, useState } from 'react'
import type { PublicEvent, PlayerView } from '../types'
import { CombatVFXRuntime, type BeamMode, type VfxQuality } from '../vfx/CombatVFXRuntime'
import { godAttackColor } from '../vfx/GodAttackFX'
import { GodCinematic, type GodCinematicCue, type GodCinematicTarget } from './GodCinematic'

function locateTargets(ids: string[]): GodCinematicTarget[] {
  const panels = Array.from(document.querySelectorAll<HTMLElement>('.player-panel[data-player-id]'))
  return ids.map((id) => {
    const panel = panels.find((item) => item.dataset.playerId === id)
    const rect = (panel?.querySelector('.portrait-button') ?? panel)?.getBoundingClientRect()
    return { id, x: rect ? (rect.left + rect.width / 2) / window.innerWidth * 100 : 80,
      y: rect ? (rect.top + rect.height / 2) / window.innerHeight * 100 : 50 }
  })
}

export function CombatVFXLayer({ players, targets, mode, events, quality, reducedMotion }: {
  players: PlayerView[]; targets: string[]; mode: BeamMode; events: PublicEvent[]; quality: VfxQuality; reducedMotion?: boolean
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const runtime = useRef<CombatVFXRuntime | null>(null)
  const seen = useRef(new Set<string>())
  const nextCue = useRef(0)
  const wuweiReady = useRef(new Set<string>())
  const launchTimers = useRef(new Set<number>())
  const [cinematics, setCinematics] = useState<GodCinematicCue[]>([])
  const dismiss = useCallback(() => setCinematics((queue) => queue.slice(1)), [])
  const targetKey = targets.join('|')
  useEffect(() => {
    const node = canvas.current
    const board = node?.parentElement
    if (!node || !board) return
    runtime.current = new CombatVFXRuntime(node, board, quality)
    return () => {
      launchTimers.current.forEach(window.clearTimeout)
      launchTimers.current.clear()
      runtime.current?.destroy()
      runtime.current = null
    }
  }, [])
  useEffect(() => { runtime.current?.setQuality(quality) }, [quality])
  useEffect(() => { runtime.current?.setPaused(cinematics.length > 0) }, [cinematics.length])
  useEffect(() => { runtime.current?.setReducedMotion(reducedMotion ?? null) }, [reducedMotion])
  useEffect(() => { runtime.current?.setBeam(targetKey ? targetKey.split('|') : [], mode) }, [targetKey, mode])
  useEffect(() => {
    for (const [index, event] of events.entries()) {
      const identity = String(event.event_id ?? index + ':' + event.kind) + ':' + String(event.presentation_phase ?? '')
      if (seen.current.has(identity)) continue
      seen.current.add(identity)
      const kind = String(event.kind)
      const definition = String(event.definition_id ?? '')
      const source = String(event.source_id ?? '')
      const sourceCharacter = players.find((player) => player.player_id === source)?.character_id
      const godColor = godAttackColor(sourceCharacter ?? '', definition)
      const color = godColor ?? (definition.includes('fire') ? '#fa7837' : definition.includes('thunder') ? '#9ca9ff' : '#efbd67')
      if (event.presentation_phase === 'reveal' && Array.isArray(event.target_ids) && event.target_ids.length) continue
      if ((kind === 'CardUsedEvent' || kind === 'TrickTargetsDeclaredEvent') && (definition.includes('slash') || definition === 'trick.savage_assault' || definition === 'trick.archery_attack')) {
        const targetIds = Array.isArray(event.target_ids) ? event.target_ids.map(String) : []
        const luBu = sourceCharacter === 'forest_god_lvbu'
        const empowered = luBu && wuweiReady.current.has(source)
        if (empowered) wuweiReady.current.delete(source)
        if (luBu) setCinematics((queue) => [...queue, {
          id: ++nextCue.current, level: empowered ? 2 : 1,
          title: empowered ? '无前·戟斩' : definition === 'trick.savage_assault' ? '南蛮入侵' : definition === 'trick.archery_attack' ? '万箭齐发' : undefined,
          targets: locateTargets(targetIds),
        }])
        const launch = () => { for (const target of targetIds) runtime.current?.trigger(definition === 'trick.archery_attack' ? 'arrows' : definition === 'trick.savage_assault' ? 'savage' : luBu || godColor ? 'god-slash' : 'slash', source, target, luBu ? '#f0c78c' : color, sourceCharacter) }
        if (luBu) {
          const timer = window.setTimeout(() => { launchTimers.current.delete(timer); launch() }, 350)
          launchTimers.current.add(timer)
        } else launch()
      } else if (kind === 'GodSkillEvent' && sourceCharacter === 'forest_god_lvbu') {
        const skill = String(event.skill_id ?? '')
        if (skill !== 'wuwei' && skill !== 'shenfen') continue
        const targetIds = Array.isArray(event.target_ids) ? event.target_ids.map(String) : []
        if (skill === 'wuwei') { wuweiReady.current.add(source); continue }
        setCinematics((queue) => [...queue, {
          id: ++nextCue.current, level: 3,
          title: '神愤', targets: locateTargets(targetIds),
        }])
      } else if ((kind === 'CardRespondedEvent' || kind === 'VirtualResponseEvent') && definition === 'basic.dodge') {
        runtime.current?.trigger('dodge', String((event.base_action as {source_id?:string} | undefined)?.source_id ?? source), source, '#8fe9ef')
      } else if (kind === 'DamageDealtEvent') {
        runtime.current?.trigger('impact', source, String(event.target_id ?? ''), godColor ?? '#ef6a46')
      }
    }
    if (seen.current.size > 200) seen.current = new Set(events.map((event, index) => String(event.event_id ?? index + ':' + event.kind)))
  }, [events, players])
  return <>
    <canvas ref={canvas} className="combat-vfx-layer" aria-hidden="true" />
    {cinematics[0] && <GodCinematic key={cinematics[0].id} cue={cinematics[0]} quality={quality} reducedMotion={reducedMotion} onComplete={dismiss} />}
  </>
}

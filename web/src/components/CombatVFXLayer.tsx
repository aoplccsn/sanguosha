import { useCallback, useEffect, useRef, useState } from 'react'
import type { PublicEvent, PlayerView } from '../types'
import { CombatVFXRuntime, type BeamMode, type VfxQuality } from '../vfx/CombatVFXRuntime'
import { godAttackColor } from '../vfx/GodAttackFX'
import { GodCinematic, type GodCinematicCue } from './GodCinematic'

export function CombatVFXLayer({ players, targets, mode, event, quality }: {
  players: PlayerView[]; targets: string[]; mode: BeamMode; event?: PublicEvent; quality: VfxQuality
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const runtime = useRef<CombatVFXRuntime | null>(null)
  const mounted = useRef(false)
  const lastEvent = useRef<PublicEvent | undefined>(undefined)
  const launchTimers = useRef<number[]>([])
  const [cinematic, setCinematic] = useState<GodCinematicCue | null>(null)
  const dismiss = useCallback(() => setCinematic(null), [])
  const targetKey = targets.join('|')
  useEffect(() => {
    const node = canvas.current
    const board = node?.parentElement
    if (!node || !board) return
    runtime.current = new CombatVFXRuntime(node, board, quality)
    return () => {
      launchTimers.current.forEach(window.clearTimeout)
      runtime.current?.destroy()
      runtime.current = null
    }
  }, [])
  useEffect(() => { runtime.current?.setQuality(quality) }, [quality])
  useEffect(() => { runtime.current?.setBeam(targetKey ? targetKey.split('|') : [], mode) }, [targetKey, mode])
  useEffect(() => {
    if (!mounted.current) { mounted.current = true; return }
    if (!event || lastEvent.current === event) return
    lastEvent.current = event
    const kind = String(event.kind)
    const definition = String(event.definition_id ?? '')
    const source = String(event.source_id ?? '')
    const sourceCharacter = players.find((player) => player.player_id === source)?.character_id
    const godColor = godAttackColor(sourceCharacter ?? '', definition)
    const color = godColor ?? (definition.includes('fire') ? '#fa7837' : definition.includes('thunder') ? '#9ca9ff' : '#efbd67')
    if (kind === 'CardUsedEvent' && definition.includes('slash')) {
      const targetIds = Array.isArray(event.target_ids) ? event.target_ids.map(String) : []
      const luBu = sourceCharacter === 'forest_god_lvbu'
      if (luBu) {
        setCinematic({ id: Date.now(), level: 1, nature: definition.includes('fire') ? 'fire' : definition.includes('thunder') ? 'thunder' : 'normal', targetCount: targetIds.length })
      }
      const launch = () => { for (const target of targetIds) runtime.current?.trigger(godColor ? 'god-slash' : 'slash', source, target, color, sourceCharacter) }
      if (luBu) launchTimers.current.push(window.setTimeout(launch, 350))
      else launch()
    } else if ((kind === 'CardRespondedEvent' || kind === 'VirtualResponseEvent') && definition === 'basic.dodge') {
      runtime.current?.trigger('dodge', source, source, '#8fe9ef')
    } else if (kind === 'DamageDealtEvent') {
      runtime.current?.trigger('impact', source, String(event.target_id ?? ''), godColor ?? '#ef6a46')
    }
  }, [event, players])
  return <>
    <canvas ref={canvas} className="combat-vfx-layer" aria-hidden="true" />
    {cinematic && <GodCinematic cue={cinematic} quality={quality} onComplete={dismiss} />}
  </>
}

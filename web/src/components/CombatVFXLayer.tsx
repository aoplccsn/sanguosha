import { useEffect, useRef } from 'react'
import type { PublicEvent, PlayerView } from '../types'
import { CombatVFXRuntime, type BeamMode, type VfxQuality } from '../vfx/CombatVFXRuntime'

export function CombatVFXLayer({ players, targets, mode, event, quality }: {
  players: PlayerView[]; targets: string[]; mode: BeamMode; event?: PublicEvent; quality: VfxQuality
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const runtime = useRef<CombatVFXRuntime | null>(null)
  const mounted = useRef(false)
  const lastEvent = useRef<PublicEvent | undefined>(undefined)
  const targetKey = targets.join('|')
  useEffect(() => {
    const node = canvas.current
    const board = node?.parentElement
    if (!node || !board) return
    runtime.current = new CombatVFXRuntime(node, board, quality)
    return () => { runtime.current?.destroy(); runtime.current = null }
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
    const godLuBu = sourceCharacter === 'forest_god_lvbu'
    const color = godLuBu ? '#d52d27' : definition.includes('fire') ? '#fa7837' : definition.includes('thunder') ? '#9ca9ff' : '#efbd67'
    if (kind === 'CardUsedEvent' && definition.includes('slash')) {
      for (const target of Array.isArray(event.target_ids) ? event.target_ids : []) runtime.current?.trigger('slash', source, String(target), color)
    } else if ((kind === 'CardRespondedEvent' || kind === 'VirtualResponseEvent') && definition === 'basic.dodge') {
      runtime.current?.trigger('dodge', source, source, '#8fe9ef')
    } else if (kind === 'DamageDealtEvent') {
      runtime.current?.trigger('impact', source, String(event.target_id ?? ''), godLuBu ? '#d52d27' : '#ef6a46')
    }
  }, [event, players])
  return <canvas ref={canvas} className="combat-vfx-layer" aria-hidden="true" />
}

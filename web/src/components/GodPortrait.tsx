import { useEffect, useId, useState } from 'react'
import type { VfxQuality } from '../vfx/CombatVFXRuntime'

export type GodPortraitMode = 'idle' | 'entry' | 'attack' | 'hit' | 'dying' | 'victory'
const LU_BU = '/assets/gods/forest_god_lvbu/'

// Masks use source-image coordinates, so animated parts remain registered.
const HEAD = 'M405 172 L548 158 L620 216 L627 309 L550 391 L444 355 L405 264 Z'
const HAIR_BACK = 'M34 198 L308 179 L455 185 L493 290 L442 439 L235 520 L49 472 Z'
const HAIR_FRONT = 'M370 162 L538 158 L601 224 L567 291 L483 273 L419 329 L389 262 Z'
const CLOTH_BACK = 'M0 425 L224 397 L387 520 L502 778 L471 1195 L119 1280 L0 978 Z'
const CLOTH_FRONT = 'M256 470 L609 497 L744 826 L589 1182 L295 1123 L185 797 Z'
const ARM = 'M625 260 L811 315 L860 622 L778 762 L645 624 L578 374 Z'
const WEAPON = 'M742 519 L830 532 L850 714 L1004 762 L1024 1536 L779 1536 L686 1007 L717 710 Z'
const EYES = 'M468 225 L580 214 L588 278 L476 293 Z'
const PARTS = [HEAD, HAIR_BACK, HAIR_FRONT, CLOTH_BACK, CLOTH_FRONT, ARM, WEAPON]

function useNaturalBlink(enabled: boolean) {
  const [blinking, setBlinking] = useState(false)
  useEffect(() => {
    if (!enabled) return
    let next = 0
    let close = 0
    let active = true
    const schedule = () => {
      next = window.setTimeout(() => {
        if (!active) return
        setBlinking(true)
        close = window.setTimeout(() => {
          setBlinking(false)
          schedule()
        }, 115)
      }, 2800 + Math.random() * 3400)
    }
    schedule()
    return () => { active = false; window.clearTimeout(next); window.clearTimeout(close) }
  }, [enabled])
  return blinking
}

export function GodPortrait({ characterId, name, quality, mode = 'idle', cue }: {
  characterId: string; name: string; quality: VfxQuality; mode?: GodPortraitMode; cue?: unknown
}) {
  const ids = useId().replace(/:/g, '')
  const [visibleMode, setVisibleMode] = useState(mode)
  const [motionKey, setMotionKey] = useState(0)
  useEffect(() => {
    setVisibleMode(mode)
    setMotionKey((current) => current + 1)
    if (mode === 'idle' || mode === 'dying') return
    const timer = window.setTimeout(() => setVisibleMode('idle'), mode === 'entry' ? 1450 : mode === 'victory' ? 1600 : mode === 'attack' ? 900 : 480)
    return () => window.clearTimeout(timer)
  }, [mode, cue])
  const blink = useNaturalBlink(characterId === 'forest_god_lvbu' && quality !== 'low' && visibleMode === 'idle')
  if (characterId !== 'forest_god_lvbu') return null
  if (quality === 'low') return <img className="god-portrait-static" src={LU_BU + (visibleMode === 'hit' || visibleMode === 'dying' || visibleMode === 'victory' ? visibleMode + '.png' : 'portrait.png')} alt={name} />
  const imageName = (name: string) => LU_BU + name + (quality === 'medium' ? '_medium.webp' : '.png')
  const body = imageName('body')
  const clip = (part: string) => 'url(#' + ids + '-' + part + ')'
  return <div className={'god-portrait god-portrait-' + visibleMode + ' god-portrait-' + quality} role="img" aria-label={name}>
    <img className="god-portrait-background" src={imageName('background')} alt="" />
    <svg key={motionKey} className="god-portrait-puppet" viewBox="0 0 1024 1536" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <mask id={ids + '-body-mask'} maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1536">
          <rect width="1024" height="1536" fill="white" />
          {PARTS.map((path, index) => <path key={index} d={path} fill="black" />)}
        </mask>
        {[
          ['head', HEAD], ['hair-back', HAIR_BACK], ['hair-front', HAIR_FRONT],
          ['cloth-back', CLOTH_BACK], ['cloth-front', CLOTH_FRONT],
          ['arm', ARM], ['weapon', WEAPON], ['eyes', EYES],
        ].map(([part, path]) => <clipPath id={ids + '-' + part} key={part}><path d={path} /></clipPath>)}
      </defs>
      <g className="god-part god-hair-back" clipPath={clip('hair-back')}><image href={body} width="1024" height="1536" /></g>
      <g className="god-part god-cloth-back" clipPath={clip('cloth-back')}><image href={body} width="1024" height="1536" /></g>
      <g className="god-part god-body"><image href={body} width="1024" height="1536" /></g>
      <g className="god-part god-head" clipPath={clip('head')}><image href={body} width="1024" height="1536" />
        <image className={'god-blink-frame' + (blink ? ' visible' : '')} href={imageName('blink')} width="1024" height="1536" clipPath={clip('eyes')} />
      </g>
      <g className="god-part god-hair-front" clipPath={clip('hair-front')}><image href={body} width="1024" height="1536" /></g>
      <g className="god-strike-limb">
        <g className="god-part god-arm" clipPath={clip('arm')}><image href={body} width="1024" height="1536" /></g>
        <g className="god-part god-weapon" clipPath={clip('weapon')}><image href={body} width="1024" height="1536" /></g>
      </g>
      <g className="god-part god-cloth-front" clipPath={clip('cloth-front')}><image href={body} width="1024" height="1536" /></g>
    </svg>
    {(['attack', 'hit', 'dying', 'victory'] as const).includes(visibleMode as 'attack' | 'hit' | 'dying' | 'victory') &&
      <img className="god-portrait-pose" src={imageName(visibleMode === 'attack' ? 'attack_close' : visibleMode)} alt="" />}
    {quality === 'high' && <span className="god-portrait-embers" aria-hidden="true" />}
  </div>
}

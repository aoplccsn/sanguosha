import type { GeneralInfo } from './types'

const imageExtension = import.meta.env.PROD ? '.webp' : '.png'

export const defaultGeneralPortrait = `/assets/generals/default_general${imageExtension}`
export const defaultCardImage = `/assets/cards/default_card${imageExtension}`

export function generalPortrait(id: string, kingdom: string, catalog: Record<string, GeneralInfo>): string {
  const portrait = catalog[id]?.portrait
  return portrait
    ? (import.meta.env.PROD ? portrait.replace(/\.png$/, '.webp') : portrait)
    : `/assets/generals/${kingdom}/${id}${imageExtension}`
}

export function cardImage(path: string): string {
  return `/assets/cards/${path}${imageExtension}`
}

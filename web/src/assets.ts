import type { GeneralInfo } from './types'
import manifest from '../public/assets/manifest.json'
const assets: Record<string, string> = manifest
export const assetUrl = (key: string) => `/assets/${assets[key]}`
export const defaultGeneralPortrait = assetUrl('default.general')
export const defaultCardImage = assetUrl('default.card')
export function generalPortrait(id: string, kingdom: string, catalog: Record<string, GeneralInfo>): string {
  return assets['general.' + id] ? assetUrl('general.' + id)
    : catalog[id]?.portrait ?? `/assets/generals/${kingdom}/${id}.png`
}
export function cardImage(path: string): string {
  const key = path.startsWith('basic/') ? 'basic.' + path.slice(6)
    : path.replace(/^military\//, '').replace(/-v2$/, '')
  return assetUrl(key)
}

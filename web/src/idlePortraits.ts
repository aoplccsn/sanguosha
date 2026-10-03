import manifest from '../../assets/idle_portraits.json'

export type IdlePortraitAsset = { video: string; objectPosition?: string }
// Populated only after a cleaned, verified runtime MP4 has been generated.
// Registry import is metadata only: it never constructs or preloads a video.
const assets: Record<string, IdlePortraitAsset> = manifest
export function idlePortrait(id: string): IdlePortraitAsset | undefined {
  return assets[id]
}

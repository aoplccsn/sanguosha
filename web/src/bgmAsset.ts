export type BgmScene = 'lobby' | 'battle'
export const BGM_URL = '/assets/audio/bgm/main_bgm.mp3'
export const BGM_AVAILABLE = Object.keys(import.meta.glob('/public/assets/audio/bgm/main_bgm.mp3')).length > 0
const lobbyAvailable = Object.keys(import.meta.glob('/public/assets/audio/bgm/lobby_bgm.wav')).length > 0
export const BGM_TRACKS: Record<BgmScene, string> = {
  lobby: lobbyAvailable ? '/assets/audio/bgm/lobby_bgm.wav' : BGM_URL,
  battle: BGM_URL,
}

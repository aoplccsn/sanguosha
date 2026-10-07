export function LandscapeGate() {
  return <div className="landscape-gate" role="status"><span aria-hidden="true">↻ ▯</span><strong>请横屏游玩</strong><p>旋转手机后即可继续当前对局</p></div>
}

// Called once from the user's start button; rotation itself never touches game state.
export async function tryLandscape() {
  if (!window.matchMedia('(pointer: coarse)').matches) return
  try {
    await document.documentElement.requestFullscreen?.()
    await (screen.orientation as ScreenOrientation & { lock?: (orientation: string) => Promise<void> }).lock?.('landscape')
  } catch { /* Unsupported browsers use the portrait prompt. */ }
}

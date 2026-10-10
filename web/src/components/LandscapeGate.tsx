// Best-effort landscape for touch devices. Never blocks: on any failure the
// responsive portrait layout stays in use, and later rotation is handled by CSS.
export async function tryLandscape() {
  if (!window.matchMedia?.('(pointer: coarse)').matches) return
  try {
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen?.()
  } catch { /* Fullscreen denied: continue without it. */ }
  try {
    await (screen.orientation as ScreenOrientation & { lock?: (orientation: string) => Promise<void> }).lock?.('landscape')
  } catch { /* Lock unsupported or rejected: portrait fallback layout. */ }
}

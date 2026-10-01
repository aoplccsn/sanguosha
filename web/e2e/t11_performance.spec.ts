import { test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

type Sample = { scenario: string; fps: number; averageMs: number; p95Ms: number; worstMs: number; longTasks: number }

test('record synthetic Canvas VFX frame timings at three desktop sizes', async ({ page }) => {
  test.setTimeout(90000)
  await page.goto('/')
  const sizes = [[1366, 768], [1600, 900], [1920, 1080]] as const
  const output: Record<string, Sample[]> = {}
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height })
    output[width + 'x' + height] = await page.evaluate(async () => {
      const { CombatVFXRuntime } = await import('/src/vfx/CombatVFXRuntime.ts')
      const board = document.createElement('section')
      board.className = 't11-perf-board'
      board.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;z-index:9999;pointer-events:none;background:#1a1412'
      board.innerHTML = '<article class="player-self" data-player-id="p1" style="position:absolute;left:40%;bottom:5%;width:160px;height:100px"><button class="portrait-button" style="width:70px;height:90px"></button></article><article data-player-id="p2" style="position:absolute;right:25%;top:15%;width:160px;height:100px"><button class="portrait-button" style="width:70px;height:90px"></button></article><canvas style="position:absolute;inset:0;width:100%;height:100%"></canvas>'
      document.body.append(board)
      const runtime = new CombatVFXRuntime(board.querySelector('canvas')!, board, 'medium')
      const samples: Sample[] = []
      async function record(scenario: string, activate: () => void) {
        let longTasks = 0
        const observer = new PerformanceObserver((list) => { longTasks += list.getEntries().length })
        try { observer.observe({ type: 'longtask', buffered: false }) } catch { /* unavailable */ }
        activate()
        const intervals: number[] = []
        let last = 0
        const start = performance.now()
        await new Promise<void>((resolve) => {
          function tick(now: number) {
            if (last) intervals.push(now - last)
            last = now
            if (now - start < 1200) requestAnimationFrame(tick)
            else resolve()
          }
          requestAnimationFrame(tick)
        })
        observer.disconnect()
        const sorted = [...intervals].sort((a, b) => a - b)
        const averageMs = intervals.reduce((sum, value) => sum + value, 0) / intervals.length
        samples.push({
          scenario, fps: 1000 / averageMs, averageMs,
          p95Ms: sorted[Math.floor(sorted.length * .95)] ?? 0,
          worstMs: sorted.at(-1) ?? 0, longTasks,
        })
      }
      await record('idle', () => {})
      await record('beam', () => runtime.setBeam(['p2'], 'attack'))
      runtime.setBeam([], 'normal')
      await record('slash', () => runtime.trigger('slash', 'p1', 'p2'))
      await record('dodge', () => runtime.trigger('dodge', 'p2', 'p2'))
      await record('damage', () => runtime.trigger('impact', 'p1', 'p2'))
      await record('god-lvbu-slash', () => runtime.trigger('god-slash', 'p1', 'p2', '#e04139', 'forest_god_lvbu'))
      await record('simultaneous', () => {
        runtime.setBeam(['p2'], 'attack')
        runtime.trigger('slash', 'p1', 'p2')
        runtime.trigger('dodge', 'p2', 'p2')
        runtime.trigger('impact', 'p1', 'p2')
      })
      await record('god-lvbu-simultaneous', () => {
        runtime.setBeam(['p2'], 'attack')
        runtime.trigger('god-slash', 'p1', 'p2', '#e04139', 'forest_god_lvbu')
        runtime.trigger('impact', 'p1', 'p2', '#e04139')
      })
      runtime.destroy()
      board.remove()
      return samples
    })
  }
  const destination = path.resolve(process.cwd(), '../docs/t11/performance_final.json')
  fs.writeFileSync(destination, JSON.stringify({
    method: 'Chromium headless requestAnimationFrame cadence; synthetic two-player Canvas fixture; medium quality; 1.2 s per scenario. Not a measured pre-change baseline or GPU paint trace.',
    measuredAt: new Date().toISOString(), results: output,
  }, null, 2))
})

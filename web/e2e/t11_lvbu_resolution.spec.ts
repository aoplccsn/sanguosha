import { expect, test } from '@playwright/test'
import path from 'node:path'

const review = path.resolve(process.cwd(), '../docs/t11/god_art/review/lvbu_final')

test('1920x1080 medium cinematic keeps full resolution artwork and sharp vector blade', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/t11/god-lvbu-preview?t11_capture=1')
  await page.getByLabel('Quality').selectOption('medium')
  for (const [button, file, frame] of [
    ['Normal Slash', 't11_3_attack_1920.png', 550],
    ['Shenfen', 't11_3_shenfen_1920.png', 1150],
  ] as const) {
    await page.getByRole('button', { name: button }).click()
    const overlay = page.locator('.god-cinematic')
    await expect(overlay).toBeVisible()
    await overlay.locator('img').evaluateAll(async (images) => {
      await Promise.all(images.map((node) => (node as HTMLImageElement).decode()))
    })
    await overlay.evaluate((node, position) => {
      node.getAnimations({ subtree: true }).forEach((animation) => {
        animation.pause()
        animation.currentTime = position
      })
    }, frame)
    const resolution = await page.evaluate(() => {
      const canvas = document.querySelector('.god-preview-board canvas') as HTMLCanvasElement
      const art = Array.from(document.querySelectorAll<HTMLImageElement>('.god-cinematic-attack-pose, .god-cinematic-crest, .god-cinematic-ready-image'))
      return {
        viewport: [innerWidth, innerHeight], dpr: devicePixelRatio, zoom: visualViewport?.scale,
        canvas: [canvas.width, canvas.height, canvas.getBoundingClientRect().width, canvas.getBoundingClientRect().height],
        art: art.map((image) => ({ source: image.naturalWidth, displayed: image.getBoundingClientRect().width })),
      }
    })
    expect(resolution.viewport).toEqual([1920, 1080])
    expect(resolution.dpr).toBe(1)
    expect(resolution.zoom).toBe(1)
    expect(resolution.canvas[0]).toBeGreaterThanOrEqual(resolution.canvas[2])
    for (const image of resolution.art) expect(image.source).toBeGreaterThanOrEqual(image.displayed)
    await page.screenshot({ path: path.join(review, file) })
    await page.keyboard.press('Escape')
    await expect(overlay).toHaveCount(0)
  }
})

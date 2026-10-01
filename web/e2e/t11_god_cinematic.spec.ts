import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const review = path.resolve(process.cwd(), '../docs/t11/god_art/review')

test('Lu Bu five cards share one standard cinematic and three levels render', async ({ page }) => {
  test.setTimeout(60000)
  fs.mkdirSync(review, { recursive: true })
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto('/t11/god-lvbu-preview')
  await expect(page.locator('.god-preview-board .player-panel')).toHaveCount(5)
  await expect(page.locator('.god-preview-board .combat-vfx-layer')).toBeVisible()
  for (const [button, name] of [
    ['Normal Slash', 'slash'],
    ['Fire Slash', 'fire'],
    ['Thunder Slash', 'thunder'],
    ['Savage Assault', 'savage'],
    ['Archery Attack', 'archery'],
    ['Level 2', 'level2'],
    ['Shenfen', 'shenfen'],
  ]) {
    await page.getByRole('button', { name: button }).click()
    const overlay = page.locator('.god-cinematic')
    await expect(overlay).toBeVisible()
    await expect(overlay).toHaveClass(/god-cinematic-standard/)
    await expect(overlay.locator('.god-cinematic-blade')).toHaveCount(1)
    await expect(overlay.locator('.god-cinematic-elemental')).toHaveCount(0)
    await expect(overlay.locator('.god-cinematic-attack-pose')).toBeVisible()
    if (['savage', 'archery', 'shenfen'].includes(name)) await expect(overlay.locator('.god-cinematic-targets i')).toHaveCount(4)
    await page.waitForTimeout(name === 'shenfen' ? 1050 : 460)
    if (['slash', 'level2', 'shenfen'].includes(name))
      await page.screenshot({ path: path.join(review, 'god_lvbu_cinematic_' + name + '.png') })
    if (await overlay.count()) await page.keyboard.press('Escape')
    await expect(overlay).toHaveCount(0)
  }
})

test('Shenfen can be skipped with Escape and reduced motion ends promptly', async ({ page }) => {
  await page.goto('/t11/god-lvbu-preview')
  await page.getByRole('button', { name: 'Shenfen' }).click()
  await expect(page.locator('.god-cinematic-level-3')).toBeVisible()
  await page.getByRole('button', { name: '跳过神将演出' }).click()
  await expect(page.locator('.god-cinematic')).toHaveCount(0)
  await page.getByRole('button', { name: 'Shenfen' }).click()
  await expect(page.locator('.god-cinematic-level-3')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.locator('.god-cinematic')).toHaveCount(0)
  await page.getByLabel('Reduced Motion').check()
  await page.getByRole('button', { name: 'Shenfen' }).click()
  await expect(page.locator('.god-cinematic-reduced')).toBeVisible()
  await expect(page.locator('.god-cinematic')).toHaveCount(0, { timeout: 1000 })
})

test('presentation preview quality, blink and reset controls use live components', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  await page.goto('/')
  await page.getByRole('link', { name: /God Lü Bu Presentation Preview/ }).click()
  await expect(page).toHaveURL(/\/t11\/god-lvbu-preview$/)
  await expect(page.locator('.god-preview-board .player-panel')).toHaveCount(5)
  const selfBounds = await page.locator('.god-preview-p1').boundingBox()
  expect(selfBounds && selfBounds.y + selfBounds.height).toBeLessThanOrEqual(768)
  await expect(page.locator('.god-preview-hero .god-portrait-high')).toBeVisible()
  await page.getByRole('button', { name: 'Blink' }).click()
  await expect(page.locator('.god-preview-hero .god-blink-frame.visible')).toHaveCount(1)
  await page.getByLabel('Quality').selectOption('medium')
  await expect(page.locator('.god-preview-hero .god-portrait-medium')).toBeVisible()
  await page.getByLabel('Quality').selectOption('low')
  await expect(page.locator('.god-preview-hero .god-portrait-static')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Blink' })).toBeDisabled()
  await page.getByLabel('Quality').selectOption('high')
  await page.getByRole('button', { name: 'Shenfen' }).click()
  await expect(page.locator('.god-cinematic-targets i')).toHaveCount(4)
  await page.getByRole('button', { name: 'Reset' }).click()
  await expect(page.locator('.god-cinematic')).toHaveCount(0)
  await expect(page.locator('.god-preview-hero .god-portrait-idle')).toBeVisible()
})

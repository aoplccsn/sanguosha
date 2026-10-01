import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const review = path.resolve(process.cwd(), '../docs/t11/god_art/review')

test('Lu Bu Slash, fire, thunder and Shenfen show the character in a full-screen attack', async ({ page }) => {
  test.setTimeout(60000)
  fs.mkdirSync(review, { recursive: true })
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto('/t11/god-lvbu-preview')
  for (const [button, nature, name] of [
    ['普通杀全屏', 'normal', 'slash'],
    ['火杀全屏', 'fire', 'fire'],
    ['雷杀全屏', 'thunder', 'thunder'],
    ['二级技能演出', 'normal', 'level2'],
    ['神愤三级演出', 'normal', 'shenfen'],
  ]) {
    await page.getByRole('button', { name: button }).click()
    const overlay = page.locator('.god-cinematic')
    await expect(overlay).toBeVisible()
    await expect(overlay).toHaveClass(new RegExp('god-cinematic-' + nature))
    await expect(overlay.locator('.god-cinematic-attack-pose')).toBeVisible()
    await page.waitForTimeout(name === 'shenfen' ? 1050 : 460)
    await page.screenshot({ path: path.join(review, 'god_lvbu_cinematic_' + name + '.png') })
    if (await overlay.count()) await page.keyboard.press('Escape')
    await expect(overlay).toHaveCount(0)
  }
})

test('Shenfen can be skipped with Escape and reduced motion ends promptly', async ({ page }) => {
  await page.goto('/t11/god-lvbu-preview')
  await page.getByRole('button', { name: '神愤三级演出' }).click()
  await expect(page.locator('.god-cinematic-level-3')).toBeVisible()
  await page.getByRole('button', { name: '跳过神将演出' }).click()
  await expect(page.locator('.god-cinematic')).toHaveCount(0)
  await page.getByRole('button', { name: '神愤三级演出' }).click()
  await expect(page.locator('.god-cinematic-level-3')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.locator('.god-cinematic')).toHaveCount(0)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.getByRole('button', { name: '神愤三级演出' }).click()
  await expect(page.locator('.god-cinematic-reduced')).toBeVisible()
  await expect(page.locator('.god-cinematic')).toHaveCount(0, { timeout: 1000 })
})

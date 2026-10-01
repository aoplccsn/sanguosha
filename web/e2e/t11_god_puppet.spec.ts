import { expect, test } from '@playwright/test'
import path from 'node:path'
import fs from 'node:fs'

test('Lu Bu preview shows separate animated body parts and attack pose', async ({ page }) => {
  test.setTimeout(60000)
  const review = path.resolve(process.cwd(), '../docs/t11/god_art/review')
  fs.mkdirSync(review, { recursive: true })
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto('/t11/god-lvbu-preview')
  await expect(page.getByRole('heading', { name: '神吕布' })).toBeVisible()
  for (const part of ['body', 'head', 'hair-back', 'hair-front', 'cloth-back', 'cloth-front', 'arm', 'weapon']) {
    await expect(page.locator('.god-showcase-large .god-' + part)).toHaveCount(1)
  }
  await page.locator('.god-showcase-large .god-portrait-background').evaluate((node: HTMLImageElement) => node.decode())
  await page.screenshot({ path: path.join(review, 'god_lvbu_puppet_idle.png') })
  await page.getByRole('button', { name: 'attack' }).click()
  await expect(page.locator('.god-showcase-large .god-portrait-attack')).toBeVisible()
  await page.waitForTimeout(320)
  await page.screenshot({ path: path.join(review, 'god_lvbu_puppet_attack.png') })
})

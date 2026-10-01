import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const review = path.resolve(process.cwd(), '../docs/t11/god_art/review/lvbu_final')

test('God Lu Bu entry and death animation state frames', async ({ page }) => {
  fs.mkdirSync(review, { recursive: true })
  await page.setViewportSize({ width: 1366, height: 768 })
  await page.goto('/t11/god-lvbu-preview')
  await expect(page.locator('.god-preview-hero .god-portrait')).toBeVisible()
  for (const mode of ['entry', 'dying'] as const) {
    await page.getByRole('button', { name: mode[0].toUpperCase() + mode.slice(1), exact: true }).click()
    await expect(page.locator('.god-preview-hero .god-portrait-' + mode)).toBeVisible()
    await page.waitForTimeout(mode === 'entry' ? 520 : 870)
    await page.screenshot({ path: path.join(review, mode + '_preview.png') })
  }
})

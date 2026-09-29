import { expect, test } from '@playwright/test'
import fs from 'node:fs'

test('Vite HMR updates the page without a full browser reload', async ({ page }) => {
  const file = 'src/components/HomePage.tsx'
  const original = fs.readFileSync(file, 'utf8')
  const marker = 'T9_HMR_CHECKPOINT'
  const sourceMarker = '<p className="home-copy">'
  const changed = original.replace(sourceMarker, '<p data-hmr-marker="' + marker + '" className="home-copy">')
  await page.goto('/')
  await expect(page.getByText('打开网页，邀友入局。规则、身份与牌堆全部由服务器掌管。')).toBeVisible()
  await page.evaluate(() => { (window as Window & { __t9HmrToken?: string }).__t9HmrToken = crypto.randomUUID() })
  const tokenBefore = await page.evaluate(() => (window as Window & { __t9HmrToken?: string }).__t9HmrToken)
  try {
    fs.writeFileSync(file, changed, 'utf8')
    await expect(page.locator('[data-hmr-marker="T9_HMR_CHECKPOINT"]')).toBeVisible({ timeout: 15000 })
    const tokenAfter = await page.evaluate(() => (window as Window & { __t9HmrToken?: string }).__t9HmrToken)
    expect(tokenAfter).toBe(tokenBefore)
  } finally {
    fs.writeFileSync(file, original, 'utf8')
  }
})

import { test, expect } from '@playwright/test'
const dir = `../docs/t21/${process.env.T21_PHASE ?? 'after'}`
test('T21 home lobby draft shots', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/?seed=21')
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${dir}/home.png` })
  await page.getByLabel('玩家昵称').fill('主公')
  await page.getByRole('button', { name: '创建多人房间', exact: true }).click()
  await expect(page.locator('.lobby-seat').first()).toBeVisible()
  await page.screenshot({ path: `${dir}/lobby.png` })
  await page.getByRole('button', { name: '开始游戏', exact: true }).click()
  await expect(page.locator('.general-card').first()).toBeVisible()
  await page.locator('.general-card').nth(1).click()
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${dir}/draft.png` })
})

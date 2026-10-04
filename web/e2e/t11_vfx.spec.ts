import { expect, test } from '@playwright/test'

test('Canvas combat layer loads, resizes and persists quality without browser errors', async ({ browser }) => {
  test.setTimeout(90000)
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 } })
  const page = await context.newPage()
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  try {
    await page.goto('/?seed=5')
    await page.getByLabel('玩家昵称').fill('T11测试')
    await page.getByRole('button', { name: '单人游戏' }).click()
    await expect(page.getByRole('heading', { name: '择将入局' })).toBeVisible()
    await page.locator('.general-card').first().click()
    await page.getByRole('button', { name: '确认武将' }).click()
    await expect(page.locator('.game-board')).toBeVisible()
    for (const file of ['portrait.png', 'background.png', 'body.png']) {
      const response = await page.request.get('/assets/gods/forest_god_lvbu/' + file)
      expect(response.ok()).toBe(true)
    }
    const canvas = page.locator('.combat-vfx-layer')
    await expect(canvas).toBeVisible()
    await expect.poll(() => canvas.evaluate((node: HTMLCanvasElement) => node.width)).toBeGreaterThan(0)
    await page.getByLabel('战斗特效画质').selectOption('low')
    await expect(page.getByLabel('战斗特效画质')).toHaveValue('low')
    await page.setViewportSize({ width: 1366, height: 768 })
    await expect.poll(() => canvas.evaluate((node: HTMLCanvasElement) => node.width)).toBeGreaterThan(0)
    await page.reload()
    // Quality persists independently of the local development room reconnect.
    expect(await page.evaluate(()=>localStorage.getItem('sanguosha.vfx.quality.v1'))).toBe('low')
    await page.getByRole('button', { name: '单人游戏' }).click()
    await expect(page.getByRole('heading', { name: '择将入局' })).toBeVisible()
    await page.locator('.general-card').first().click()
    await page.getByRole('button', { name: '确认武将' }).click()
    await expect(page.getByLabel('战斗特效画质')).toHaveValue('low')
    expect(errors).toEqual([])
  } finally {
    await context.close()
  }
})

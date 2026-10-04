import { expect, test } from '@playwright/test'

test('god generals enter the default draft without a switch', async ({ page }) => {
  await page.goto('/?seed=0')
  await expect(page.getByLabel('允许神将进入候选池')).toHaveCount(0)
  await page.getByLabel('玩家昵称').fill('默认神将验收')
  await page.getByRole('button', { name: '单人游戏' }).click()
  await expect(page.getByRole('heading', { name: '择将入局' })).toBeVisible()
  await expect.poll(() => page.locator('.general-card img').evaluateAll(images =>
    images.some(image => (image as HTMLImageElement).src.includes('_god_')))).toBe(true)
})

test('local browsers show actor target Slash and Dodge', async ({ browser }) => {
  test.setTimeout(120000)
  const hostContext = await browser.newContext()
  const guestContext = await browser.newContext()
  const host = await hostContext.newPage()
  const guest = await guestContext.newPage()
  const errors: string[] = []
  for (const page of [host, guest]) {
    page.on('pageerror', error => errors.push(error.message))
    page.on('websocket', socket => socket.on('socketerror', error => errors.push(String(error))))
  }
  try {
    await host.goto('/?seed=3')
    await host.getByLabel('玩家昵称').fill('攻击方')
    await host.getByRole('button', { name: '创建多人房间' }).click()
    const code = (await host.locator('.room-code-box strong').textContent())?.trim()
    expect(code).toMatch(/^[A-Z0-9]{6}$/)
    await guest.goto('/room/' + code)
    await guest.getByLabel('玩家昵称').fill('防守方')
    await guest.getByRole('button', { name: '加入房间' }).click()
    await guest.getByRole('button', { name: '准备' }).click()
    await host.getByRole('button', { name: '开始游戏' }).click()
    await expect(host.getByRole('heading', { name: '择将入局' })).toBeVisible()
    await host.locator('.general-card').first().click()
    await host.getByRole('button', { name: '确认武将' }).click()
    await guest.locator('.general-card').first().click()
    await guest.getByRole('button', { name: '确认武将' }).click()
    await expect(host.locator('.game-page')).toBeVisible()
    await expect(host.locator('[data-player-id="p1"]')).toHaveClass(/active/)
    await host.getByRole('button', { name: /^杀 / }).click()
    await host.locator('.player-panel.selectable').filter({ hasText: '防守方' }).click()
    await host.getByRole('button', { name: '确定' }).click()
    await expect(host.locator('.event-stage')).toContainText('吕布 对 刘备 使用【杀】', { timeout: 15000 })
    await expect(host.locator('[data-player-id="p1"]')).toHaveClass(/presenting-action/)
    await expect(host.locator('[data-player-id="p2"]')).toHaveClass(/event-target/)
    await expect(guest.locator('.decision-prompt')).toContainText('闪')
    await guest.getByRole('button', { name: /^闪 / }).click()
    await guest.getByRole('button', { name: '确定' }).click()
    await expect(guest.locator('.event-stage')).toContainText('刘备 打出【闪】', { timeout: 15000 })
    expect(errors.filter(message => message !== 'WebSocket is closed before the connection is established.')).toEqual([])
  } finally {
    await Promise.allSettled([hostContext.close(), guestContext.close()])
  }
})

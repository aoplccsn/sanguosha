import { expect, test } from '@playwright/test'

test('two real browsers enter a production game', async ({ browser }) => {
  test.setTimeout(120000)
  const hostContext = await browser.newContext()
  const guestContext = await browser.newContext()
  try {
    const host = await hostContext.newPage()
    const guest = await guestContext.newPage()
    await host.goto('/?seed=5')
    await host.getByLabel('玩家昵称').fill('房主')
    await host.getByRole('button', { name: '创建多人房间' }).click()
    const code = (await host.locator('.room-code-box strong').textContent())?.trim()
    expect(code).toMatch(/^[A-Z0-9]{6}$/)
    await guest.goto('/room/' + code)
    await guest.getByLabel('玩家昵称').fill('来宾')
    await guest.getByRole('button', { name: '加入房间' }).click()
    await guest.getByRole('button', { name: '准备' }).click()
    await host.getByRole('button', { name: '开始游戏' }).click()
    await expect(host.getByRole('heading', { name: '择将入局' })).toBeVisible()
    await host.locator('.general-card').filter({ hasText: '孙权' }).click()
    await host.getByRole('button', { name: '确认武将' }).click()
    await guest.locator('.general-card').filter({ hasText: '张辽' }).click()
    await guest.getByRole('button', { name: '确认武将' }).click()
    await expect(host.locator('.game-page')).toBeVisible()
    await expect(guest.locator('.game-page')).toBeVisible()
  } finally {
    await hostContext.close()
    await guestContext.close()
  }
})

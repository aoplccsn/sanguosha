import { expect, test } from '@playwright/test'

test('single-origin container path: two browsers, reconnect, Slash and Dodge', async ({ browser, request }) => {
  test.setTimeout(120000)
  const hostContext = await browser.newContext()
  const guestContext = await browser.newContext()
  const host = await hostContext.newPage()
  const guest = await guestContext.newPage()
  try {
    expect((await request.get('/')).ok()).toBe(true)
    expect((await request.get('/api/health')).ok()).toBe(true)
    const catalog = await (await request.get('/api/catalog/generals')).json() as unknown[]
    expect(catalog).toHaveLength(108)

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
    await expect(guest.getByRole('heading', { name: '择将入局' })).toBeVisible()
    await host.locator('.general-card').first().click()
    await host.getByRole('button', { name: '确认武将' }).click()
    await guest.locator('.general-card').first().click()
    await guest.getByRole('button', { name: '确认武将' }).click()
    await expect(host.locator('.game-page')).toBeVisible()
    await expect(guest.locator('.player-panel')).toHaveCount(5)

    await guest.reload()
    await expect(guest.getByRole('button', { name: '继续对局', exact: true })).toBeVisible()
    await guest.getByRole('button', { name: '继续对局', exact: true }).click()
    await expect(guest.locator('.game-page')).toBeVisible()
    await expect(guest.locator('.player-self')).toContainText('防守方')

    await host.getByRole('button', { name: /^杀 / }).click()
    await host.locator('.player-panel.selectable').filter({ hasText: '防守方' }).click()
    await host.getByRole('button', { name: '确定' }).click()
    await expect(host.locator('.event-stage')).toContainText('杀')
    await expect(guest.locator('.decision-prompt')).toContainText('闪')
    await guest.getByRole('button', { name: /^闪 / }).click()
    await guest.getByRole('button', { name: '确定' }).click()
    await expect(guest.locator('.response-card img')).toHaveAttribute('alt', '闪')
  } finally {
    await Promise.allSettled([hostContext.close(), guestContext.close()])
  }
})

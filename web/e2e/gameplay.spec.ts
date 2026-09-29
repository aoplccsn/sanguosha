import { expect, test, type Browser, type BrowserContext, type Page } from '@playwright/test'

async function enterSeededGame(browser: Browser) {
  const hostContext = await browser.newContext()
  const guestContext = await browser.newContext()
  const host = await hostContext.newPage()
  const guest = await guestContext.newPage()
  await host.goto('/?seed=5')
  await host.getByLabel('玩家昵称').fill('房主')
  await host.getByRole('button', { name: '创建多人房间' }).click()
  const roomCode = (await host.locator('.room-code-box strong').textContent())?.trim()
  expect(roomCode).toMatch(/^[A-Z0-9]{6}$/)
  await guest.goto('/room/' + roomCode)
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
  return { hostContext, guestContext, host, guest, roomCode: roomCode! }
}

async function closeGame(contexts: BrowserContext[]) {
  for (const context of contexts) await context.close()
}

async function chooseSlashTarget(host: Page) {
  await expect(host.locator('.decision-prompt')).toBeVisible()
  await host.getByRole('button', { name: /^杀 / }).click()
  await host.getByRole('button', { name: '确定' }).click()
  const target = host.locator('.player-panel.selectable').filter({ hasText: '来宾' })
  await expect(target).toBeVisible()
  await target.click()
  await expect(host.locator('.target-beam line')).toHaveCount(1)
  await host.getByRole('button', { name: '确定' }).click()
}

test('real browser gameplay performs skill, Slash, Dodge and Nullification', async ({ browser }) => {
  test.setTimeout(120000)
  const game = await enterSeededGame(browser)
  const { host, guest } = game
  try {
    await expect(host.getByRole('button', { name: 'zhiheng' })).toBeEnabled()
    await host.getByRole('button', { name: 'zhiheng' }).click()
    await host.getByRole('button', { name: '确定' }).click()
    await expect(host.locator('.decision-prompt')).toContainText('制衡')
    await host.locator('.hand-card:not([disabled])').filter({ hasText: '闪电' }).click()
    await host.getByRole('button', { name: '确定' }).click()
    await expect(host.getByRole('button', { name: /^杀 / })).toBeEnabled()

    await chooseSlashTarget(host)
    await expect(guest.locator('.decision-prompt')).toContainText('闪')
    await guest.getByRole('button', { name: /^闪 / }).click()
    await guest.getByRole('button', { name: '确定' }).click()
    await expect(host.locator('.event-stage')).toContainText('闪')
    await expect(guest.locator('.event-stage')).toContainText('闪')

    await expect(host.getByRole('button', { name: /^五谷丰登 / })).toBeEnabled()
    await host.getByRole('button', { name: /^五谷丰登 / }).click()
    await host.getByRole('button', { name: '确定' }).click()
    await expect(host.getByRole('button', { name: '本次均不响应' })).toBeVisible()
    await host.getByRole('button', { name: '本次均不响应' }).click()
    await expect(guest.locator('.decision-prompt')).toContainText('无懈可击')
    await guest.locator('.hand-card:not([disabled])').filter({ hasText: '无懈可击' }).click()
    await guest.getByRole('button', { name: '确定' }).click()
    await expect(host.locator('.shared-card-pool')).toBeVisible()
    await expect(guest.locator('.shared-card-pool')).toBeVisible()
    for (let round = 0; round < 8; round += 1) {
      const page = await host.locator('.decision-prompt').isVisible() ? host
        : await guest.locator('.decision-prompt').isVisible() ? guest : null
      if (!page) break
      const prompt = await page.locator('.decision-prompt').textContent() ?? ''
      if (prompt.includes('无懈可击')) {
        const legal = page.locator('.hand-card:not([disabled])').filter({ hasText: '无懈可击' })
        if (await legal.count()) await legal.first().click()
        else await page.getByRole('button', { name: '本次均不响应' }).click()
        await page.getByRole('button', { name: '确定' }).click()
      } else if (await page.locator('.shared-card-pool').isVisible()) {
        await page.locator('.shared-card-pool .hand-card:not([disabled])').first().click()
        await page.getByRole('button', { name: '确定' }).click()
      } else {
        break
      }
      await page.waitForTimeout(250)
    }
  } finally {
    await closeGame([game.hostContext, game.guestContext])
  }
})

test('browser reload reconnects to the same seat and restores a private request', async ({ browser }) => {
  test.setTimeout(90000)
  const game = await enterSeededGame(browser)
  const { host, guest } = game
  try {
    await chooseSlashTarget(host)
    const prompt = await guest.locator('.decision-prompt .prompt-copy strong').textContent()
    await expect(guest.locator('.decision-prompt')).toContainText('闪')
    await guest.reload()
    await expect(guest.locator('.game-page')).toBeVisible()
    await expect(guest.locator('.player-self')).toContainText('你 · 来宾')
    await expect(guest.locator('.decision-prompt .prompt-copy strong')).toHaveText(prompt ?? '')
    await expect(guest.locator('.decision-prompt .timer')).toBeVisible()
  } finally {
    await closeGame([game.hostContext, game.guestContext])
  }
})

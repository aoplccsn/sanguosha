import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const screenshotDir = path.resolve(process.cwd(), '../docs/t9_web_screenshots')

async function enterGame(host: import('@playwright/test').Page, guest: import('@playwright/test').Page) {
  await host.goto('/?seed=5')
  await host.getByLabel('玩家昵称').fill('房主')
  await host.getByRole('button', { name: '创建多人房间' }).click()
  const code = (await host.locator('.room-code-box strong').textContent())?.trim()
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
}

test('T9 visual screenshot matrix', async ({ browser }) => {
  test.setTimeout(120000)
  fs.mkdirSync(screenshotDir, { recursive: true })
  const hostContext = await browser.newContext()
  const guestContext = await browser.newContext()
  const host = await hostContext.newPage()
  const guest = await guestContext.newPage()
  try {
    await host.goto('/?seed=5')
    await host.screenshot({ path: path.join(screenshotDir, 'home.png'), fullPage: true })
    await host.getByLabel('玩家昵称').fill('房主')
    await host.getByRole('button', { name: '创建多人房间' }).click()
    await host.screenshot({ path: path.join(screenshotDir, 'lobby.png'), fullPage: true })
    const code = (await host.locator('.room-code-box strong').textContent())?.trim()
    await guest.goto('/room/' + code)
    await guest.getByLabel('玩家昵称').fill('来宾')
    await guest.getByRole('button', { name: '加入房间' }).click()
    await guest.getByRole('button', { name: '准备' }).click()
    await host.getByRole('button', { name: '开始游戏' }).click()
    await expect(host.getByRole('heading', { name: '择将入局' })).toBeVisible()
    await host.screenshot({ path: path.join(screenshotDir, 'pregame_10_generals.png'), fullPage: true })
    await host.locator('.general-card').filter({ hasText: '孙权' }).click()
    await host.getByRole('button', { name: '确认武将' }).click()
    await guest.locator('.general-card').filter({ hasText: '张辽' }).click()
    await guest.getByRole('button', { name: '确认武将' }).click()
    await expect(host.locator('.game-page')).toBeVisible()
    await host.locator('.player-panel img').evaluateAll((images) => Promise.all(images.map((image) =>
      image.complete ? Promise.resolve() : new Promise<void>((resolve) => { image.addEventListener('load', () => resolve(), { once: true }); image.addEventListener('error', () => resolve(), { once: true }) }))))
    for (const size of [[1366, 768], [1600, 900], [1920, 1080]]) {
      await host.setViewportSize({ width: size[0], height: size[1] })
      await host.screenshot({ path: path.join(screenshotDir, 'table_' + size[0] + 'x' + size[1] + '.png'), fullPage: true })
    }
    await host.getByRole('button', { name: /^杀 / }).click()
    await host.getByRole('button', { name: '确定' }).click()
    await host.locator('.player-panel.selectable').filter({ hasText: '来宾' }).click()
    await host.screenshot({ path: path.join(screenshotDir, 'slash_target.png'), fullPage: true })
    await host.getByRole('button', { name: '确定' }).click()
    await expect(guest.locator('.decision-prompt')).toContainText('闪')
    await guest.screenshot({ path: path.join(screenshotDir, 'dodge_response.png'), fullPage: true })
  } finally {
    await hostContext.close()
    await guestContext.close()
  }
})

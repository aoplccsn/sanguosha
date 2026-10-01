import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const evidenceDir = path.resolve(process.cwd(), '../docs/t10_art/v3_review/web_ui_smoke')

async function imageLoaded(locator: import('@playwright/test').Locator) {
  await expect.poll(() => locator.evaluate((image: HTMLImageElement) =>
    image.complete && image.naturalWidth > 0 && !image.currentSrc.endsWith('/default_general.png'))).toBe(true)
}

test('V3 portraits render in multiplayer draft, player panel and detail', async ({ browser }) => {
  test.setTimeout(120000)
  fs.mkdirSync(evidenceDir, { recursive: true })
  const hostContext = await browser.newContext({ viewport: { width: 1600, height: 900 } })
  const guestContext = await browser.newContext({ viewport: { width: 1600, height: 900 } })
  const host = await hostContext.newPage()
  const guest = await guestContext.newPage()
  try {
    await host.goto('/?seed=5')
    await host.getByLabel('玩家昵称').fill('房主')
    await host.getByRole('button', { name: '创建多人房间' }).click()
    const code = (await host.locator('.room-code-box strong').textContent())?.trim()
    expect(code).toBeTruthy()
    await guest.goto('/room/' + code)
    await guest.getByLabel('玩家昵称').fill('来宾')
    await guest.getByRole('button', { name: '加入房间' }).click()
    await guest.getByRole('button', { name: '准备' }).click()
    await host.getByRole('button', { name: '开始游戏' }).click()
    await expect(host.getByRole('heading', { name: '择将入局' })).toBeVisible()
    await expect(host.locator('.general-card')).toHaveCount(10)
    const hostChoice = host.locator('.general-card').first()
    const chosenPortrait = await hostChoice.locator('img').getAttribute('src')
    await hostChoice.click()
    await imageLoaded(host.locator('.general-detail > img'))
    await host.getByRole('button', { name: '确认武将' }).click()
    await guest.locator('.general-card').first().click()
    await guest.getByRole('button', { name: '确认武将' }).click()
    await expect(host.locator('.game-page')).toBeVisible()
    for (const img of await host.locator('.player-panel .portrait-button img').all()) await imageLoaded(img)
    const selfPortrait = host.locator('.player-self .portrait-button img')
    await expect(selfPortrait).toHaveAttribute('src', chosenPortrait!)
    await host.locator('.player-self .portrait-button').click()
    await expect(host.locator('.game-general-detail')).toBeVisible()
    await imageLoaded(host.locator('.game-general-detail > img'))
    await host.screenshot({ path: path.join(evidenceDir, 'player_detail_final.png'), fullPage: true })
  } finally {
    await Promise.allSettled([hostContext.close(), guestContext.close()])
  }
})

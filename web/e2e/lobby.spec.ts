import { expect, test } from '@playwright/test'

test('two browsers create, join, ready and enter the general draft', async ({ browser }) => {
  const hostContext = await browser.newContext()
  const guestContext = await browser.newContext()
  const host = await hostContext.newPage()
  const guest = await guestContext.newPage()
  await host.goto('/')
  await host.getByLabel('玩家昵称').fill('房主')
  await host.getByRole('button', { name: '创建多人房间' }).click()
  const roomCode = (await host.locator('.room-code-box strong').textContent())?.trim()
  expect(roomCode).toMatch(/^[A-Z0-9]{6}$/)

  await guest.goto('/room/' + roomCode)
  await guest.getByLabel('玩家昵称').fill('来宾')
  await guest.getByRole('button', { name: '加入房间' }).click()
  await expect(guest.getByText(roomCode!)).toBeVisible()
  await guest.getByRole('button', { name: '准备' }).click()
  await host.getByRole('button', { name: '开始游戏' }).click()
  await expect(host.getByRole('heading', { name: '择将入局' })).toBeVisible()
  await expect(guest.getByRole('heading', { name: '择将入局' })).toBeVisible()
  await hostContext.close()
  await guestContext.close()
})

test('five browser contexts can occupy one room before draft', async ({ browser }) => {
  const contexts = await Promise.all(Array.from({ length: 5 }, () => browser.newContext()))
  const pages = await Promise.all(contexts.map((context) => context.newPage()))
  await pages[0].goto('/')
  await pages[0].getByLabel('玩家昵称').fill('玩家1')
  await pages[0].getByRole('button', { name: '创建多人房间' }).click()
  const roomCode = (await pages[0].locator('.room-code-box strong').textContent())?.trim()
  expect(roomCode).toMatch(/^[A-Z0-9]{6}$/)
  for (let index = 1; index < pages.length; index += 1) {
    await pages[index].goto('/room/' + roomCode)
    await pages[index].getByLabel('玩家昵称').fill('玩家' + (index + 1))
    await pages[index].getByRole('button', { name: '加入房间' }).click()
    await expect(pages[index].getByText(roomCode!)).toBeVisible()
    await pages[index].getByRole('button', { name: '准备' }).click()
  }
  await pages[0].getByRole('button', { name: '开始游戏' }).click()
  await expect(pages[0].getByRole('heading', { name: '择将入局' })).toBeVisible()
  for (const context of contexts) await context.close()
})

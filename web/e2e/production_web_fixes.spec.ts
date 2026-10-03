import { expect, test } from '@playwright/test'
import type { WebSocketRoute } from '@playwright/test'

test('production draft renders Chinese names and loaded portraits', async ({ page, request }) => {
  const response = await request.get('/api/catalog/generals')
  expect(response.ok()).toBeTruthy()
  const catalog = await response.json() as Array<{ id: string; name: string; portrait: string }>
  expect(catalog).toHaveLength(65)
  expect(catalog.filter((item) => item.id.includes('_god_'))).toHaveLength(8)
  for (const general of catalog) {
    expect(general.name).toMatch(/[\u3400-\u9fff]/u)
    expect(general.portrait).toMatch(/\.webp$/)
  }

  await page.goto('/?seed=5')
  await page.getByLabel('玩家昵称').fill('验收')
  await page.getByRole('button', { name: '单人游戏' }).click()
  await expect(page.getByRole('heading', { name: '择将入局' })).toBeVisible()
  const cards = page.locator('.general-card')
  await expect(cards).toHaveCount(10)
  for (let index = 0; index < 10; index++) {
    const card = cards.nth(index)
    await expect(card.locator('strong')).toHaveText(/[\u3400-\u9fff]/u)
    await expect(card.locator('img')).toHaveJSProperty('complete', true)
    expect(await card.locator('img').evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0)
  }
})

test('short room socket reconnect does not show a fatal connection error', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/room/**', (socket) => {
    sockets.push(socket)
    socket.send(JSON.stringify({ type: 'WELCOME', room_code: 'ABC234' }))
    socket.onMessage((raw) => {
      const message = JSON.parse(String(raw)) as { type: string }
      if (message.type === 'JOIN_ROOM' || message.type === 'RECONNECT') {
        socket.send(JSON.stringify({ type: 'WELCOME', room_code: 'ABC234', seat_id: 'p1', reconnect_token: 'token' }))
        socket.send(JSON.stringify({ type: 'LOBBY_STATE', phase: 'OPEN', host_id: 'p1', mode_id: 'military-five', seat_count: 5, allow_gods: false, seats: [] }))
      }
    })
  })
  await page.route('**/api/rooms', (route) => route.fulfill({ status: 201, contentType: 'application/json', body: '{"room_code":"ABC234"}' }))
  await page.goto('/')
  await page.getByLabel('玩家昵称').fill('验收')
  await page.getByRole('button', { name: '创建多人房间' }).click()
  await expect(page.getByRole('heading', { name: '多人房间' })).toBeVisible()
  await sockets[0].close()
  await expect(page.getByText('连接波动，正在恢复…')).toBeVisible()
  await expect(page.getByText('连接波动，正在恢复…')).toHaveCount(0)
  expect(sockets).toHaveLength(2)
  await expect(page.getByText('无法连接到房间，仍在尝试恢复…')).toHaveCount(0)
})

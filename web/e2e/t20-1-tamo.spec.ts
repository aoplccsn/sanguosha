import { test, expect, type Page } from '@playwright/test'
import type { Projection } from '../src/types'

type Stream = { projection?: Projection; self?: string; room?: string; choices?: string[] }

function receive(stream: Stream, payload: string | Buffer) {
  const message = JSON.parse(payload.toString())
  if (message.type === 'PROJECTION_UPDATE') stream.projection = message.projection
  if (message.type === 'WELCOME' && message.seat_id) {
    stream.self = message.seat_id
    stream.room = message.room_code
  }
  if (message.type === 'DRAFT_REQUEST') stream.choices = message.request.choices
}

async function expectTable(page: Page, stream: Stream, seats: string[], anchors: readonly string[]) {
  await expect.poll(() => stream.projection?.players.map(player => player.player_id)).toEqual(seats)
  const self = stream.self!
  const index = seats.indexOf(self)
  const relative = [...seats.slice(index + 1), ...seats.slice(0, index)]
  await expect(page.locator('.player-panel')).toHaveCount(seats.length)
  await expect(page.locator('.self-area .player-self')).toHaveAttribute('data-player-id', self)
  for (const [offset, id] of relative.entries()) {
    await expect(page.locator(`.player-${anchors[offset]}`)).toHaveAttribute('data-player-id', id)
  }
  expect(await page.locator('.game-board > .player-panel').evaluateAll(panels =>
    panels.map(panel => (panel as HTMLElement).dataset.playerId))).toEqual(relative)
}

for (const [mode, count, anchors] of [
  ['military-five', 5, ['east', 'north-east', 'north-west', 'west']],
  ['military-eight', 8, ['east-lower', 'east-upper', 'north-east', 'north', 'north-west', 'west-upper', 'west-lower']],
] as const) {
  test(`T20.1 ${count}-player Tamo rearranges the table and reconnects both viewpoints`, async ({ page, browser, baseURL, request }) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    const host: Stream = {}
    // Keep the protected self-pick entry, with a second human available for reconnect verification.
    await page.routeWebSocket('**/ws', socket => {
      const server = socket.connectToServer()
      socket.onMessage(payload => {
        const message = JSON.parse(payload.toString())
        if (message.type === 'CREATE_ROOM') message.single_player = false
        server.send(JSON.stringify(message))
      })
      server.onMessage(payload => { receive(host, payload); socket.send(payload) })
    })
    const otherContext = await browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 } })
    const other = await otherContext.newPage()
    const guest: Stream = {}
    other.on('websocket', socket => socket.on('framereceived', frame => receive(guest, frame.payload)))
    try {
      await page.goto('/?seed=0')
      await page.getByRole('combobox', { name: '对局模式' }).selectOption(mode)
      await page.getByRole('button', { name: '测试模式' }).click()
      await page.getByLabel('测试权限码').fill('fixture-only-code')
      await page.getByRole('button', { name: '验证', exact: true }).click()
      await page.getByRole('button', { name: '创建测试房' }).click()
      await expect(page.getByRole('heading', { name: '多人房间' })).toBeVisible()
      await other.goto('/')
      await other.getByLabel('房间码').fill(host.room!)
      await other.getByRole('button', { name: '加入房间' }).click()
      await other.getByRole('button', { name: '准备', exact: true }).click()
      await page.getByRole('button', { name: '开始游戏' }).click()
      await expect(page.getByText('测试房 · 自选武将')).toBeVisible()
      await page.getByLabel('搜索武将或技能').fill('神鲁肃')
      await page.getByRole('button', { name: /神鲁肃/ }).first().click()
      await page.getByRole('button', { name: '确认武将' }).click()
      const catalog = await (await request.get('/api/catalog/generals')).json()
      await expect(other.locator('.general-card')).toHaveCount(10)
      const general = catalog.find((entry: { id: string; kingdom: string }) =>
        guest.choices?.includes(entry.id) && entry.kingdom !== 'god' && entry.id !== 'forest_zuoci')
      expect(general).toBeTruthy()
      await other.getByRole('button', { name: new RegExp(general.name) }).first().click()
      await other.getByRole('button', { name: '确认武将' }).click()
      await page.getByRole('button', { name: '魏', exact: true }).click()
      await expect(page.getByText('榻谟：调整非主公角色座次？')).toBeVisible()
      const before = host.projection!.players.map(player => player.player_id)
      const lord = host.projection!.players.find(player => player.identity_label === '主公')!.player_id
      const lordIndex = before.indexOf(lord)
      expect(lordIndex).toBeGreaterThan(0)
      const slots = Array.from({ length: count - 1 }, (_, offset) => (lordIndex + offset + 1) % count)
      const clockwise = slots.map(index => before[index])
      const chosen = [...clockwise.slice(1), clockwise[0]]
      expect(chosen).toContain(host.self)
      const expected = [...before]
      slots.forEach((slot, index) => { expected[slot] = chosen[index] })
      expect(expected.indexOf(host.self!)).not.toBe(before.indexOf(host.self!))
      await expectTable(page, host, before, anchors)
      const oldPositions = await page.locator('.player-panel').evaluateAll(panels =>
        Object.fromEntries(panels.map(panel => {
          const rect = panel.getBoundingClientRect()
          return [(panel as HTMLElement).dataset.playerId, { x: rect.x, y: rect.y }]
        })))
      await page.getByRole('button', { name: '发动 / 是' }).click()
      await expect(page.getByText('榻谟：按新座次顺序选择全部非主公角色')).toBeVisible()
      await expect(page.locator('.player-panel.selectable')).toHaveCount(count - 1)
      for (const id of chosen) await page.locator(`[data-player-id="${id}"] .portrait-button`).click()
      await page.getByRole('button', { name: '确定', exact: true }).click()
      await expectTable(page, host, expected, anchors)
      await expectTable(other, guest, expected, anchors)
      expect(host.projection!.players[lordIndex].player_id).toBe(lord)
      expect(await page.locator('.game-board > .player-panel').evaluateAll((panels, previous) =>
        panels.some(panel => {
          const old = previous[(panel as HTMLElement).dataset.playerId!]
          const rect = panel.getBoundingClientRect()
          return Math.abs(rect.x - old.x) + Math.abs(rect.y - old.y) > 20
        }), oldPositions)).toBe(true)
      for (const [client, stream] of [[page, host], [other, guest]] as const) {
        stream.projection = undefined
        await client.reload()
        await client.getByRole('button', { name: '继续对局' }).click()
        await expectTable(client, stream, expected, anchors)
      }
    } finally {
      await otherContext.close()
    }
  })
}

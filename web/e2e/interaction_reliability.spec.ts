import { expect, test, type Page, type WebSocketRoute } from '@playwright/test'

const card = (id: string, name: string, definition: string) => ({ card_id: id, name, definition_id: definition, suit: '♥', rank: '2', category: 'basic', equipment_slot: '', details: '' })
const dodge = card('dodge-1', '闪', 'basic.dodge')
const nullification = card('null-1', '无懈可击', 'trick.nullification')
const slash = card('slash-1', '杀', 'basic.slash')
const player = { player_id: 'p1', name: '你 · 验收', character_name: '曹操', identity_label: '主公', hp: 4, max_hp: 4, hand_count: 3, alive: true, active: false, character_id: 'caocao', faction: '魏', chained: false, equipment: [], judgments: [], base_distance: null, effective_distance: null, attack_range: 1, skill_labels: [] }
const projection = { players: [player], hand: [dodge, nullification, slash], current_phase: 'play', turn_number: 1, deck_count: 100, discard_count: 0, result: null, discard_top: null, shared_cards: [] }
const pending = (id: string, definition = 'basic.dodge', eligible = ['dodge-1']) => ({ request_id: id, player_id: 'p1', request_type: 'respond_with_card', prompt: '请响应', choices: [], allowed_player_ids: [], required_definition_id: definition, eligible_card_ids: eligible, allow_pass: true, min_count: 1, max_count: 1, subject_player_id: null, remaining_ms: 30000 })

async function room(page: Page, request = pending('r1')) {
  const sockets: WebSocketRoute[] = []
  const submitted: Array<Record<string, any>> = []
  await page.routeWebSocket('**/room/**', (socket) => {
    sockets.push(socket)
    socket.onMessage((raw) => {
      const message = JSON.parse(String(raw)) as Record<string, any>
      if (message.type === 'JOIN_ROOM' || message.type === 'RECONNECT') {
        socket.send(JSON.stringify({ type: 'WELCOME', room_code: 'ABC234', seat_id: 'p1', reconnect_token: 'token' }))
        socket.send(JSON.stringify({ type: 'PROJECTION_UPDATE', active_request_id: request?.request_id ?? null, projection }))
        if (request) socket.send(JSON.stringify({ type: 'PENDING_REQUEST', request }))
      }
      if (message.type === 'SUBMIT_DECISION') submitted.push(message)
    })
  })
  await page.route('**/api/rooms', (route) => route.fulfill({ status: 201, contentType: 'application/json', body: '{"room_code":"ABC234"}' }))
  await page.goto('/')
  await page.getByLabel('玩家昵称').fill('验收')
  await page.getByRole('button', { name: '创建多人房间' }).click()
  await expect(page.getByText('第 1 回合')).toBeVisible()
  return { sockets, submitted }
}

for (const [label, definition, id, name] of [
  ['Dodge', 'basic.dodge', 'dodge-1', '闪'],
  ['Nullification', 'trick.nullification', 'null-1', '无懈可击'],
] as const) {
  test(`${label}: first card click selects and one confirm submits`, async ({ page }) => {
    const { submitted } = await room(page, pending('r1', definition, [id]))
    const cardButton = page.getByRole('button', { name: new RegExp(name) }).last()
    await cardButton.click()
    await expect(cardButton).toHaveClass(/selected/)
    await page.getByRole('button', { name: '确定' }).click()
    await expect(page.getByRole('button', { name: '处理中…' })).toBeDisabled()
    await expect.poll(() => submitted.length).toBe(1)
    expect(submitted[0].decision).toEqual({ request_id: 'r1', value: id })
  })
}

test('illegal card explains why and rapid confirm sends once', async ({ page }) => {
  const { submitted } = await room(page)
  await page.getByRole('button', { name: /杀/ }).dispatchEvent('click')
  await expect(page.getByText('此牌不能用于当前响应')).toBeVisible()
  await page.getByRole('button', { name: /闪/ }).click()
  const confirm = page.getByRole('button', { name: '确定' })
  await confirm.click()
  await page.getByRole('button', { name: '处理中…' }).dispatchEvent('click')
  await expect.poll(() => submitted.length).toBe(1)
  await expect(page.getByRole('button', { name: '处理中…' })).toBeDisabled()
})

test('reconnect restores response and the first click works', async ({ page }) => {
  const { sockets, submitted } = await room(page)
  await sockets[0].close()
  await expect.poll(() => sockets.length).toBe(2)
  await expect(page.getByRole('button', { name: /闪/ })).toBeVisible()
  await page.getByRole('button', { name: /闪/ }).click()
  await expect(page.getByRole('button', { name: /闪/ })).toHaveClass(/selected/)
  await page.getByRole('button', { name: '确定' }).click()
  await expect.poll(() => submitted.length).toBe(1)
})

test('leaving for home closes connection and offers explicit resume choice on reload', async ({ page }) => {
  const { sockets } = await room(page)
  await page.getByRole('button', { name: '离开牌局' }).click()
  await expect(page.getByRole('button', { name: '创建多人房间' })).toBeVisible()
  await expect(page.getByText('连接波动，正在恢复…')).toHaveCount(0)
  await page.waitForTimeout(1000)
  expect(sockets).toHaveLength(1)
  await page.evaluate(() => localStorage.setItem('sanguosha.web.session.v1', JSON.stringify({ roomCode: 'ABC234', playerName: '验收', seatId: 'p1', reconnectToken: 'token' })))
  await page.reload()
  await expect(page.getByText('检测到上次对局')).toBeVisible()
  expect(sockets).toHaveLength(1)
  await page.getByRole('button', { name: '放弃' }).click()
  await expect(page.getByText('检测到上次对局')).toHaveCount(0)
})

test('no legal response does not display a response prompt', async ({ page }) => {
  await room(page, null as never)
  await expect(page.getByRole('button', { name: '确定' })).toHaveCount(0)
  await expect(page.locator('.decision-prompt')).toHaveCount(0)
})

test('normal speed spaces public AI actions without delaying a pending response', async ({ page }) => {
  const { sockets } = await room(page, null as never)
  await expect(page.getByLabel('对局速度')).toHaveValue('normal')
  sockets[0].send(JSON.stringify({ type: 'PUBLIC_EVENT', event: { kind: 'CardUsedEvent', event_id: 'e1', source_id: 'p1', card_name: '杀' } }))
  await expect(page.locator('.event-stage')).toContainText('杀')
  sockets[0].send(JSON.stringify({ type: 'PUBLIC_EVENT', event: { kind: 'CardUsedEvent', event_id: 'e2', source_id: 'p1', card_name: '桃' } }))
  await page.waitForTimeout(250)
  await expect(page.locator('.event-stage')).toContainText('杀')
  await expect(page.locator('.event-stage')).toContainText('桃', { timeout: 2000 })
  sockets[0].send(JSON.stringify({ type: 'PENDING_REQUEST', request: pending('r2') }))
  await expect(page.getByRole('button', { name: '确定' })).toBeVisible()
})

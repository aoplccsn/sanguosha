import { expect, test, type Page, type WebSocketRoute } from '@playwright/test'

const card = (id: string, name: string, definition: string) => ({ card_id: id, name, definition_id: definition, suit: '♥', rank: '2', category: 'basic', equipment_slot: '', details: '' })
const dodge = card('dodge-1', '闪', 'basic.dodge')
const nullification = card('null-1', '无懈可击', 'trick.nullification')
const slash = card('slash-1', '杀', 'basic.slash')
const trick = card('trick-1', '顺手牵羊', 'trick.snatch')
const horse = card('horse-1', '的卢', 'equipment.horse.dilu')
const player = { player_id: 'p1', name: '你 · 验收', character_name: '曹操', identity_label: '主公', hp: 4, max_hp: 4, hand_count: 3, alive: true, active: false, character_id: 'caocao', faction: '魏', chained: false, equipment: [], judgments: [], base_distance: null, effective_distance: null, attack_range: 1, skill_labels: [] }
const opponent = { ...player, player_id: 'p2', name: '刘备', character_name: '刘备', identity_label: '未知', active: false, hand_count: 3, base_distance: 1, effective_distance: 1 }
const projection = { players: [player, opponent], hand: [dodge, nullification, slash, trick, horse], current_phase: 'play', turn_number: 1, deck_count: 100, discard_count: 0, result: null, discard_top: null, shared_cards: [] }
const pending = (id: string, definition = 'basic.dodge', eligible = ['dodge-1']) => ({ request_id: id, player_id: 'p1', request_type: 'respond_with_card', prompt: '请响应', choices: [], allowed_player_ids: [], required_definition_id: definition, eligible_card_ids: eligible, allow_pass: true, min_count: 1, max_count: 1, subject_player_id: null, remaining_ms: 30000 })

async function room(page: Page, request: any = pending('r1')) {
  const sockets: WebSocketRoute[] = []
  const submitted: Array<Record<string, any>> = []
  await page.routeWebSocket('**/room/**', (socket) => {
    sockets.push(socket)
    socket.onMessage((raw) => {
      const message = JSON.parse(String(raw)) as Record<string, any>
      if (message.type === 'JOIN_ROOM' || message.type === 'RECONNECT') {
        socket.send(JSON.stringify({ type: 'WELCOME', room_code: 'ABC234', seat_id: 'p1', reconnect_token: 'token' }))
        if (request?.request_type === 'choose_general') {
          socket.send(JSON.stringify({ type: 'DRAFT_REQUEST', identity: 'lord', lord_id: 'p1', request }))
        } else {
          socket.send(JSON.stringify({ type: 'PROJECTION_UPDATE', active_request_id: request?.request_id ?? null, projection }))
          if (request) socket.send(JSON.stringify({ type: 'PENDING_REQUEST', request }))
        }
      }
      if (message.type === 'SUBMIT_DECISION') submitted.push(message)
    })
  })
  await page.route('**/api/rooms', (route) => route.fulfill({ status: 201, contentType: 'application/json', body: '{"room_code":"ABC234"}' }))
  await page.goto('/')
  await page.getByLabel('玩家昵称').fill('验收')
  await page.getByRole('button', { name: '创建多人房间' }).click()
  await expect(page.getByText(request?.request_type === 'choose_general' ? '择将入局' : '第 1 回合')).toBeVisible()
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
    await expect(page.getByRole('button', { name: '正在提交…' })).toBeDisabled()
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
  await page.getByRole('button', { name: '正在提交…' }).dispatchEvent('click')
  await expect.poll(() => submitted.length).toBe(1)
  await expect(page.getByRole('button', { name: '正在提交…' })).toBeDisabled()
})

for (const [name, id] of [['杀', 'slash-1'], ['顺手牵羊', 'trick-1']] as const) {
  test(`${name}: card, target, one final confirm`, async ({ page }) => {
    const request = { ...pending('play-1'), request_type: 'choose_option',
      choices: [`use:${id}`, 'end_play_phase'], eligible_card_ids: [], allow_pass: false,
      required_definition_id: null, min_count: 0, max_count: 0, remaining_ms: 60000,
      play_card_targets: { [`use:${id}`]: { targets: ['p2'], min: 1, max: 1 } } }
    const { submitted } = await room(page, request)
    const cardButton = page.getByRole('button', { name: new RegExp(name) }).last()
    await cardButton.click()
    await expect(cardButton).toHaveClass(/selected/)
    await expect(page.getByText(`${name} → 请选择目标`)).toBeVisible()
    await page.locator('[data-player-id="p2"] .player-heading').click()
    await expect(page.getByText(`${name} → 刘备`)).toBeVisible()
    await page.getByRole('button', { name: '确定' }).click()
    await expect.poll(() => submitted.length).toBe(1)
    expect(submitted[0].decision.value).toEqual({ option: `use:${id}`, targets: ['p2'] })
  })
}

test('equipment confirms without a target or nullification prompt', async ({ page }) => {
  const request = { ...pending('equip-1'), request_type: 'choose_option',
    choices: ['use:horse-1', 'end_play_phase'], eligible_card_ids: [], allow_pass: false,
    required_definition_id: null, min_count: 0, max_count: 0, remaining_ms: 60000,
    play_card_targets: { 'use:horse-1': { targets: [], min: 0, max: 0 } } }
  const { submitted } = await room(page, request)
  await page.getByRole('button', { name: /的卢/ }).last().click()
  await expect(page.getByRole('button', { name: '确定' })).toBeEnabled()
  await page.getByRole('button', { name: '确定' }).click()
  await expect.poll(() => submitted.length).toBe(1)
  expect(submitted[0].decision.value).toEqual({ option: 'use:horse-1', targets: [] })
  await expect(page.getByText('请响应无懈可击')).toHaveCount(0)
})

test('ACK shows confirmed and does not submit the same decision again', async ({ page }) => {
  const { sockets, submitted } = await room(page)
  await page.getByRole('button', { name: /闪/ }).click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.getByRole('button', { name: '正在提交…' })).toBeDisabled()
  sockets[0].send(JSON.stringify({ type: 'DECISION_ACCEPTED', request_id: 'r1', accepted: true,
    server_timing_ms: { receive_to_accept: 1, accept_to_ack: 3 } }))
  await expect(page.getByText('已确认，正在结算…')).toBeVisible()
  await expect(page.locator('.decision-prompt')).toHaveCount(0)
  expect(submitted).toHaveLength(1)
  const metrics = await page.evaluate(() => (window as any).sanguoshaDiagnostics)
  expect(metrics.decisions).toHaveLength(1)
  expect(metrics.decisions[0].receive_to_accept_ms).toBe(1)
})

test('cancel keeps the selected card and returns to target selection', async ({ page }) => {
  await room(page, { ...pending('cancel-1'), request_type: 'choose_option', choices: ['use:slash-1'],
    eligible_card_ids: [], allow_pass: false, min_count: 0, max_count: 0,
    play_card_targets: { 'use:slash-1': { targets: ['p2'], min: 1, max: 1 } } })
  await page.getByRole('button', { name: /杀/ }).click()
  await page.locator('[data-player-id="p2"] .player-heading').click()
  await expect(page.locator('[data-player-id="p2"]')).toHaveClass(/selected-target/)
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('button', { name: /杀/ })).toHaveClass(/selected/)
  await expect(page.getByText('杀 → 请选择目标')).toBeVisible()
})

test('Yinghun branch choices display Chinese labels', async ({ page }) => {
  const { submitted } = await room(page, { ...pending('yinghun'), request_type: 'choose_option',
    choices: ['draw_x_discard_one', 'draw_one_discard_x'], eligible_card_ids: [], allow_pass: false,
    choice_labels: { draw_x_discard_one: '摸 X 张，弃一张', draw_one_discard_x: '摸一张，弃 X 张' } })
  await page.getByRole('button', { name: '摸 X 张，弃一张' }).click()
  await expect.poll(() => submitted.length).toBe(1)
  expect(submitted[0].decision.value).toBe('draw_x_discard_one')
  await expect(page.getByText('draw_one_discard_x')).toHaveCount(0)
})

test('legal ViewAs Nullification remains selectable', async ({ page }) => {
  const { submitted } = await room(page, { ...pending('kanpo', 'trick.nullification', ['virtual:kanpo:black-card']),
    choice_labels: { 'virtual:kanpo:black-card': '看破' } })
  await page.getByRole('button', { name: '看破', exact: true }).click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect.poll(() => submitted.length).toBe(1)
  expect(submitted[0].decision.value).toBe('virtual:kanpo:black-card')
})

test('room failure returns home with a banner and stops reconnecting', async ({ page }) => {
  const { sockets } = await room(page)
  sockets[0].send(JSON.stringify({ type: 'ERROR', message: 'room not found' }))
  await expect(page.getByRole('button', { name: '创建多人房间' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('无法恢复上一局')
  await page.waitForTimeout(1000)
  expect(sockets).toHaveLength(1)
  await expect(page.getByText('连接波动，正在恢复…')).toHaveCount(0)
})

test('human timer displays the server 60-second allowance', async ({ page }) => {
  await room(page, { ...pending('timer-60'), remaining_ms: 60000 })
  await expect(page.getByLabel('剩余 60 秒')).toBeVisible()
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


test('draft selection survives expired display, two-second ACK and delayed projection', async ({ page }) => {
  const { sockets, submitted } = await room(page, { ...pending('draft-race'),
    request_type: 'choose_general', choices: ['caocao', 'liubei'], eligible_card_ids: [],
    allow_pass: false, remaining_ms: 500 })
  const selected = page.locator('.general-card').filter({ has: page.getByText('曹操', { exact: true }) })
  await selected.click()
  await page.getByRole('button', { name: '确认武将' }).click()
  await expect(page.getByRole('button', { name: '正在提交…' })).toBeDisabled()
  await expect.poll(() => submitted.length).toBe(1)
  // The mock server holds an already accepted decision while its ACK is in transit.
  await page.waitForTimeout(2100)
  await expect(page.getByLabel('剩余 0 秒')).toBeVisible()
  await expect(selected).toHaveClass(/selected/)
  await expect(selected).toBeDisabled()
  sockets[0].send(JSON.stringify({ type: 'DECISION_ACCEPTED', request_id: 'draft-race', accepted: true }))
  await expect(page.getByText('已确认，等待其他玩家…', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: '已确认', exact: true })).toBeDisabled()
  await expect(page.getByLabel('剩余 0 秒')).toHaveCount(0)
  await page.waitForTimeout(1100)
  await expect(selected).toHaveClass(/selected/)
  expect(submitted).toHaveLength(1)
  expect(submitted[0].decision).toEqual({ request_id: 'draft-race', value: 'caocao' })
  sockets[0].send(JSON.stringify({ type: 'PROJECTION_UPDATE', after_request_id: 'draft-race',
    active_request_id: null, projection }))
  await expect(page.getByText('第 1 回合')).toBeVisible()
  await expect(page.locator('[data-player-id="p1"]')).toContainText('曹操')
})

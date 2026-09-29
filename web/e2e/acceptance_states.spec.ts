import { expect, test, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const screenshotDir = path.resolve(process.cwd(), '../docs/t9_web_screenshots')
type Request = {
  request_id: string
  request_type: string
  choices: string[]
  eligible_card_ids: string[]
  allowed_player_ids: string[]
  allow_pass: boolean
  min_count: number
}
type ServerMessage = {
  type: string
  request?: Request
  projection?: { players: Array<{ equipment: unknown[]; judgments: unknown[] }> }
}

function choose(request: Request): unknown {
  if (request.request_type === 'choose_option') {
    return request.choices.find((choice) => choice.startsWith('use:'))
      ?? (request.choices.includes('end_play_phase') ? 'end_play_phase' : request.choices[0])
  }
  if (request.request_type === 'yes_no') return false
  if (request.request_type === 'respond_with_card') return request.allow_pass ? { pass: true } : request.eligible_card_ids[0]
  if (request.request_type === 'choose_card') return request.eligible_card_ids[0]
  if (request.request_type === 'choose_cards') return request.eligible_card_ids.slice(0, request.min_count)
  if (request.request_type === 'choose_player') return request.allowed_player_ids[0]
  if (request.request_type === 'choose_players') return request.allowed_player_ids.slice(0, request.min_count)
  throw new Error('Unhandled server request: ' + request.request_type)
}

async function sendDecision(page: Page, request: Request, value: unknown) {
  await page.evaluate(({ requestId, decisionValue }) => {
    const socket = (window as Window & { __t9AcceptanceSocket?: WebSocket }).__t9AcceptanceSocket
    if (!socket || socket.readyState !== WebSocket.OPEN) throw new Error('Game WebSocket unavailable')
    socket.send(JSON.stringify({ type: 'SUBMIT_DECISION', version: 2, decision: { request_id: requestId, value: decisionValue } }))
  }, { requestId: request.request_id, decisionValue: value })
}

test('real WebSocket match captures equipment, judgment and result states', async ({ page }) => {
  test.setTimeout(180000)
  fs.mkdirSync(screenshotDir, { recursive: true })
  await page.addInitScript(() => {
    const NativeSocket = window.WebSocket
    window.WebSocket = class extends NativeSocket {
      constructor(url: string | URL, protocols?: string | string[]) {
        super(url, protocols)
        if (String(url).endsWith('/ws')) (window as Window & { __t9AcceptanceSocket?: WebSocket }).__t9AcceptanceSocket = this
      }
    }
  })
  const messages: ServerMessage[] = []
  page.on('websocket', (socket) => socket.on('framereceived', ({ payload }) => {
    try {
      const message = JSON.parse(String(payload)) as ServerMessage
      if (message.type) messages.push(message)
    } catch { /* Vite uses its own WebSocket. */ }
  }))
  await page.goto('/?seed=5')
  await page.getByLabel('玩家昵称').fill('验收玩家')
  await page.getByRole('button', { name: '单人游戏' }).click()

  let next = 0
  let equipment = false
  let judgment = false
  let finished = false
  for (let steps = 0; steps < 5000 && !finished; steps += 1) {
    await expect.poll(() => messages.length, { timeout: 30000 }).toBeGreaterThan(next)
    const message = messages[next++]
    if (message.type === 'DRAFT_REQUEST' && message.request) {
      await sendDecision(page, message.request, message.request.choices[0])
    } else if (message.type === 'PENDING_REQUEST' && message.request) {
      await sendDecision(page, message.request, choose(message.request))
    } else if (message.type === 'PROJECTION_UPDATE' && message.projection) {
      if (!equipment && message.projection.players.some((player) => player.equipment.length)) {
        await expect(page.locator('.equipment-token').first()).toBeVisible()
        await page.locator('.equipment-token').first().hover()
        await expect(page.getByRole('tooltip').first()).toBeVisible()
        await page.screenshot({ path: path.join(screenshotDir, 'equipment.png'), fullPage: true })
        equipment = true
      }
      if (!judgment && message.projection.players.some((player) => player.judgments.length)) {
        await expect(page.locator('.judgment-token').first()).toBeVisible()
        await page.screenshot({ path: path.join(screenshotDir, 'judgment.png'), fullPage: true })
        judgment = true
      }
    } else if (message.type === 'GAME_OVER') {
      await expect(page.getByRole('dialog', { name: '对局结果' })).toBeVisible()
      await page.screenshot({ path: path.join(screenshotDir, 'game_result.png'), fullPage: true })
      finished = true
    } else if (message.type === 'ERROR') {
      throw new Error('Server rejected scripted browser decision')
    }
  }
  expect(finished).toBe(true)
  expect(equipment).toBe(true)
  expect(judgment).toBe(true)
})

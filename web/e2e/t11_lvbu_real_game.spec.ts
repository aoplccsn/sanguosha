import { expect, test, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const review = path.resolve(process.cwd(), '../docs/t11/god_art/review/lvbu_final')
type Wire = { type: string; event?: { kind?: string; skill_id?: string; target_ids?: string[]; definition_id?: string } }

async function startReviewMatch(page: Page, label: string, capture = true) {
  const messages: Wire[] = []
  page.on('websocket', (socket) => socket.on('framereceived', ({ payload }) => {
    try { const message = JSON.parse(String(payload)) as Wire; if (message.type === 'PUBLIC_EVENT') messages.push(message) } catch { /* Vite HMR */ }
  }))
  await page.goto('/?seed=5&t11_lvbu=1' + (capture ? '&t11_capture=1' : ''))
  await page.getByLabel('玩家昵称').fill(label)
  await page.getByRole('button', { name: '单人游戏' }).click()
  await expect(page.getByRole('heading', { name: '择将入局' })).toBeVisible()
  await page.locator('.general-card').filter({ hasText: '神吕布' }).click()
  await page.getByRole('button', { name: '确认武将' }).click()
  await expect(page.locator('.game-page')).toBeVisible()
  await expect(page.locator('.player-self')).toContainText('神吕布')
  return messages
}

async function freezeCinematic(page: Page, ms: number) {
  await page.locator('.god-cinematic').evaluate((root, at) => {
    root.querySelectorAll('*').forEach((element) => element.getAnimations().forEach((animation) => { animation.pause(); animation.currentTime = at }))
  }, ms)
}

test('real Web match emits Wuqian and Shenfen, then displays all target impacts', async ({ page }) => {
  test.setTimeout(90000)
  fs.mkdirSync(review, { recursive: true })
  await page.setViewportSize({ width: 1366, height: 768 })
  const messages = await startReviewMatch(page, '神吕布验收')
  await page.screenshot({ path: path.join(review, 'idle_real.png') })
  await expect(page.getByRole('button', { name: '无前' })).toBeEnabled()
  await page.getByRole('button', { name: '无前' }).click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.player-panel.selectable')).toHaveCount(4)
  await page.locator('.player-panel.selectable').first().click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect.poll(() => messages.some((message) => message.event?.skill_id === 'wuwei')).toBe(true)
  await expect(page.locator('.god-cinematic-level-2')).toHaveCount(0)
  const empoweredSlash = page.getByRole('button', { name: /^杀 / }).first()
  await expect(empoweredSlash).toBeEnabled()
  await empoweredSlash.click()
  await page.getByRole('button', { name: '确定' }).click()
  await page.locator('.player-panel.selectable').first().click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.god-cinematic-level-2')).toBeVisible()
  await freezeCinematic(page, 650)
  await page.screenshot({ path: path.join(review, 'level2_real.png') })
  await page.keyboard.press('Escape')
  await expect(page.locator('.god-cinematic')).toHaveCount(0)

  await expect(page.getByRole('button', { name: '神愤' })).toBeEnabled()
  await page.getByRole('button', { name: '神愤' }).click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect.poll(() => messages.some((message) => message.event?.skill_id === 'shenfen')).toBe(true)
  await expect(page.locator('.god-cinematic-level-3')).toBeVisible()
  const targets = messages.find((message) => message.event?.skill_id === 'shenfen')?.event?.target_ids ?? []
  expect(targets).toHaveLength(4)
  await expect(page.locator('.god-cinematic-targets i')).toHaveCount(4)
  await freezeCinematic(page, 1250)
  await page.screenshot({ path: path.join(review, 'shenfen_real.png') })
  await page.keyboard.press('Escape')
  const damage = messages.filter((message) => message.event?.kind === 'DamageDealtEvent')
  expect(damage.length).toBeGreaterThanOrEqual(4)
  await expect(page.locator('.god-cinematic')).toHaveCount(0)
})

for (const attack of [
  { name: '杀', definition: 'basic.slash', nature: 'normal', file: 'slash_real.png' },
  { name: '火杀', definition: 'basic.fire_slash', nature: 'fire', file: 'fire_real.png' },
  { name: '雷杀', definition: 'basic.thunder_slash', nature: 'thunder', file: 'thunder_real.png' },
]) {
  test('real Web match plays God Lu Bu ' + attack.name, async ({ page }) => {
    test.setTimeout(60000)
    fs.mkdirSync(review, { recursive: true })
    await page.setViewportSize({ width: 1366, height: 768 })
    const messages = await startReviewMatch(page, '杀牌验收')
    const card = page.getByRole('button', { name: new RegExp('^' + attack.name + ' ') }).first()
    await expect(card).toBeEnabled()
    await card.click()
    await page.getByRole('button', { name: '确定' }).click()
    await expect(page.locator('.player-panel.selectable').first()).toBeVisible()
    await page.locator('.player-panel.selectable').first().click()
    await page.getByRole('button', { name: '确定' }).click()
    await expect(page.locator('.god-cinematic-' + attack.nature)).toBeVisible()
    await freezeCinematic(page, attack.nature === 'thunder' ? 570 : 480)
    await page.screenshot({ path: path.join(review, attack.file) })
    await expect.poll(() => messages.some((message) => message.event?.definition_id === attack.definition)).toBe(true)
  })
}

test('real Shenfen can be skipped without changing engine results', async ({ page }) => {
  test.setTimeout(60000)
  const messages = await startReviewMatch(page, '跳过验收', false)
  await page.getByRole('button', { name: '神愤' }).click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.god-cinematic-level-3')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.locator('.god-cinematic')).toHaveCount(0)
  await expect.poll(() => messages.filter((message) => message.event?.kind === 'DamageDealtEvent').length).toBeGreaterThanOrEqual(4)
})

test('reduced motion shortens real Shenfen and preserves every target', async ({ page }) => {
  test.setTimeout(60000)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const messages = await startReviewMatch(page, '低动态验收', false)
  await page.getByRole('button', { name: '神愤' }).click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect.poll(() => messages.some((message) => message.event?.skill_id === 'shenfen')).toBe(true)
  await expect(page.locator('.god-cinematic')).toHaveCount(0, { timeout: 5000 })
  expect(messages.find((message) => message.event?.skill_id === 'shenfen')?.event?.target_ids).toHaveLength(4)
})

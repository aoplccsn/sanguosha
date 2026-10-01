import { expect, test, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const review = path.resolve(process.cwd(), '../docs/t11/god_art/review/lvbu_final')
const sizes = [{ width: 1366, height: 768 }, { width: 1600, height: 900 }, { width: 1920, height: 1080 }]

async function game(page: Page, size: { width: number; height: number }) {
  await page.setViewportSize(size)
  await page.goto('/?seed=5&t11_lvbu=1')
  await page.getByLabel('玩家昵称').fill('性能验收')
  await page.getByRole('button', { name: '单人游戏' }).click()
  await page.locator('.general-card').filter({ hasText: '神吕布' }).click()
  await page.getByRole('button', { name: '确认武将' }).click()
  await expect(page.locator('.game-page')).toBeVisible()
  await page.getByLabel('战斗特效画质').selectOption('medium')
}

async function sample(page: Page, ms: number) {
  return page.evaluate(async (length) => {
    const deltas: number[] = []
    let last = 0
    const start = performance.now()
    await new Promise<void>((resolve) => {
      const frame = (now: number) => {
        if (last) deltas.push(now - last)
        last = now
        if (now - start < length) requestAnimationFrame(frame)
        else resolve()
      }
      requestAnimationFrame(frame)
    })
    const sorted = [...deltas].sort((a, b) => a - b)
    const median = sorted[Math.floor(sorted.length / 2)] ?? 0
    const p95 = sorted[Math.floor(sorted.length * .95)] ?? 0
    return { frames: deltas.length, fps: Math.round(deltas.length * 1000 / length), medianFrameMs: +median.toFixed(1), p95FrameMs: +p95.toFixed(1), longFrames: deltas.filter((delta) => delta > 34).length }
  }, ms)
}

async function slash(page: Page, name: string) {
  const card = page.getByRole('button', { name: new RegExp('^' + name + ' ') }).first()
  await expect(card).toBeEnabled()
  await card.click()
  await page.getByRole('button', { name: '确定' }).click()
  await page.locator('.player-panel.selectable').first().click()
  await page.getByRole('button', { name: '确定' }).click()
}

test('real God Lu Bu medium quality frame pacing at three viewport sizes', async ({ browser }) => {
  test.setTimeout(420000)
  fs.mkdirSync(review, { recursive: true })
  const records = []
  for (const size of sizes) {
    let context = await browser.newContext()
    let page = await context.newPage()
    await game(page, size)
    records.push({ size, scene: 'idle', ...await sample(page, 1600) })
    await page.getByRole('button', { name: '无前' }).click()
    await page.getByRole('button', { name: '确定' }).click()
    await page.locator('.player-panel.selectable').first().click()
    await page.getByRole('button', { name: '确定' }).click()
    await slash(page, '杀')
    await expect(page.locator('.god-cinematic-level-2')).toBeVisible()
    records.push({ size, scene: 'level2', ...await sample(page, 1200) })
    await page.getByRole('button', { name: '神愤' }).click()
    await page.getByRole('button', { name: '确定' }).click()
    await expect(page.locator('.god-cinematic-level-3')).toBeVisible()
    records.push({ size, scene: 'shenfen', ...await sample(page, 2100) })
    await context.close()
    for (const [scene, label] of [['slash', '杀'], ['fire_slash', '火杀'], ['thunder_slash', '雷杀']]) {
      context = await browser.newContext()
      page = await context.newPage()
      await game(page, size)
      await slash(page, label)
      await expect(page.locator('.god-cinematic')).toBeVisible()
      records.push({ size, scene, ...await sample(page, 900) })
      await context.close()
    }
  }
  fs.writeFileSync(path.join(review, 'performance_medium.json'), JSON.stringify({ method: 'Chromium requestAnimationFrame cadence during real Web matches; frame rate depends on test host and display refresh', records }, null, 2))
  expect(records).toHaveLength(18)
})

test('ordinary Web match idle baseline for viewport comparison', async ({ browser }) => {
  test.setTimeout(90000)
  const records = []
  for (const size of sizes) {
    const context = await browser.newContext()
    const page = await context.newPage()
    await page.setViewportSize(size)
    await page.goto('/?seed=5')
    await page.getByLabel('玩家昵称').fill('普通对局基线')
    await page.getByRole('button', { name: '单人游戏' }).click()
    await page.locator('.general-card').first().click()
    await page.getByRole('button', { name: '确认武将' }).click()
    await expect(page.locator('.game-page')).toBeVisible()
    await page.getByLabel('战斗特效画质').selectOption('medium')
    records.push({ size, scene: 'ordinary_idle', ...await sample(page, 1600) })
    await context.close()
  }
  fs.writeFileSync(path.join(review, 'performance_baseline.json'), JSON.stringify({ records }, null, 2))
})

test('God Lu Bu medium idle after portrait layer optimization', async ({ browser }) => {
  test.setTimeout(90000)
  const records = []
  for (const size of sizes) {
    const context = await browser.newContext()
    const page = await context.newPage()
    await game(page, size)
    records.push({ size, scene: 'god_lvbu_idle', ...await sample(page, 1600) })
    await context.close()
  }
  fs.writeFileSync(path.join(review, 'performance_god_idle.json'), JSON.stringify({ records }, null, 2))
})

for (const size of sizes) test(`isolated God Lu Bu cinematic ${size.width}x${size.height}`, async ({ browser }) => {
  test.setTimeout(90000)
  const records = []
  for (const scene of ['slash', 'shenfen'] as const) {
    const context = await browser.newContext()
    const page = await context.newPage()
    await game(page, size)
    if (scene === 'slash') await slash(page, '杀')
    else {
      await page.getByRole('button', { name: '神愤' }).click()
      await page.getByRole('button', { name: '确定' }).click()
    }
    await expect(page.locator('.god-cinematic')).toBeVisible()
    records.push({ size, scene, ...await sample(page, scene === 'slash' ? 900 : 2100) })
    await context.close()
  }
  fs.writeFileSync(path.join(review, `performance_cinematic_${size.width}.json`), JSON.stringify({ records }, null, 2))
})

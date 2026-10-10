import { test, expect, type Page } from '@playwright/test'

async function authorize(page: Page) {
  await page.getByText('更多工具', { exact: true }).click()
  await page.getByRole('button', { name: '测试模式', exact: true }).click()
  await page.getByLabel('测试权限码').fill('fixture-only-code')
  await page.getByRole('button', { name: '验证', exact: true }).click()
  await page.getByRole('button', { name: '创建测试房' }).click()
  await expect(page.getByLabel('搜索武将或技能')).toBeVisible()
}
async function wall(page: Page, scroll: boolean) {
  await expect.poll(() => page.locator('.general-card img').first().evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true)
  const info = await page.locator('.general-grid').evaluate(e => {
    const first = e.querySelector('.general-card')!
    const r = first.getBoundingClientRect()
    const d = document.querySelector('.general-detail')!.getBoundingClientRect()
    const shell = document.querySelector('.pregame-shell')!.getBoundingClientRect()
    const img = first.querySelector('img')!
    return { w: r.width, h: r.height, columns: getComputedStyle(e).gridTemplateColumns.split(' ').length,
      scroll: e.scrollHeight > e.clientHeight, ratio: d.width / shell.width, img: img.getBoundingClientRect().height,
      rendered: img.complete && img.naturalWidth > 0 }
  })
  expect(info.h / info.w).toBeCloseTo(4 / 3, 1)
  expect(info.img).toBeGreaterThan(info.h * .95)
  expect(info.rendered).toBe(true)
  expect(info.columns).toBeGreaterThanOrEqual(5)
  expect(info.columns).toBeLessThanOrEqual(7)
  expect(info.ratio).toBeGreaterThan(.25)
  expect(info.ratio).toBeLessThan(.30)
  if (scroll) expect(info.scroll).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
}

for (const [width, height] of [[1440, 900], [1920, 1080], [844, 390]]) {
  test(`T21.4 searchable test draft ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await page.goto('/?seed=21')
    await authorize(page)
    expect(await page.locator('.general-card').count()).toBeGreaterThanOrEqual(65)
    await expect(page.locator('.general-card img').first()).toHaveJSProperty('complete', true)
    await wall(page, true)
    await page.getByLabel('搜索武将或技能').fill('孙权')
    await expect(page.locator('.general-card')).toHaveCount(1)
    await page.locator('.general-card').click()
    await expect(page.locator('.general-detail')).toContainText('制衡')
    await expect(page.locator('.general-detail .dynamic-portrait img')).toBeVisible()
    const confirm = page.getByRole('button', { name: '确认武将' })
    await expect(confirm).toBeInViewport(); await confirm.click()
    await expect(page.locator('.player-panel')).toHaveCount(5)
  })
}

test('T21.4 normal ten-choice draft, 5/8 seats, landscape and reconnect', async ({ page }) => {
  for (const mode of ['military-five', 'military-eight']) {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/?seed=21')
    await page.getByLabel('对局模式').selectOption(mode)
    await page.getByRole('button', { name: '单人游戏', exact: true }).click()
    await expect(page.locator('.general-card')).toHaveCount(10)
    await wall(page, false)
    await page.setViewportSize({ width: 844, height: 390 })
    await wall(page, false)
    await page.locator('.general-card').first().click()
    await expect(page.getByRole('button', { name: '确认武将' })).toBeInViewport()
    await page.getByRole('button', { name: '确认武将' }).click()
    await expect(page.locator('.player-panel')).toHaveCount(mode === 'military-five' ? 5 : 8)
    await expect(page.locator('.player-self')).toBeInViewport()
    await page.reload()
    await page.getByRole('button', { name: '继续对局', exact: true }).click()
    await expect(page.locator('.player-self')).toHaveCount(1)
    await expect(page.locator('.player-panel')).toHaveCount(mode === 'military-five' ? 5 : 8)
    await page.getByRole('button', { name: '离开牌局' }).click()
    await expect(page.locator('.home-page')).toBeVisible()
  }
})

test('T21.4 five heroes crossfade and lazy videos with static failure fallback', async ({ page }) => {
  const requests: string[] = []
  page.on('request', r => { if (r.url().endsWith('.mp4')) requests.push(r.url()) })
  await page.clock.install()
  await page.goto('/')
  await expect(page.locator('.home-page')).toHaveAttribute('data-hero', 'zhugeliang')
  await expect(page.locator('.home-hero video')).toHaveCount(1)
  expect(requests.every(url => url.includes('fire_god_zhugeliang'))).toBe(true)
  expect(await page.locator('.home-hero video').evaluate((v: HTMLVideoElement) => v.muted && v.loop)).toBe(true)
  await page.clock.runFor(20_000)
  await expect(page.locator('.home-page')).toHaveAttribute('data-hero', 'lvbu')
  await expect(page.locator('.home-hero')).toHaveCount(2)
  expect(await page.locator('.hero-departing video').evaluate((v: HTMLVideoElement) => v.paused)).toBe(true)
  await page.clock.runFor(700)
  await expect(page.locator('.home-hero')).toHaveCount(1)
  for (const key of ['zhouyu', 'guanyu', 'ganning', 'zhugeliang']) {
    await page.getByRole('button', { name: '下一位神将' }).click()
    await expect(page.locator('.home-page')).toHaveAttribute('data-hero', key)
    await page.clock.runFor(700)
    await expect(page.locator('.home-hero')).toHaveCount(1)
    await expect(page.locator('.home-hero video')).toHaveCount(1)
  }
  await page.locator('.home-hero video').evaluate(v => v.dispatchEvent(new Event('error')))
  await expect(page.locator('.home-hero video')).toHaveCount(0)
  const poster = page.locator('.home-hero img')
  await expect(poster).toBeVisible()
  expect(await poster.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true)
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await page.clock.runFor(40_000)
  await expect(page.locator('.home-page')).toHaveAttribute('data-hero', 'zhugeliang')
})

test('T21.4 reduced motion keeps static heroes and join entry expands', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.clock.install()
  await page.goto('/')
  await page.clock.runFor(60_000)
  await expect(page.locator('.home-page')).toHaveAttribute('data-hero', 'zhugeliang')
  await expect(page.locator('.home-hero video')).toHaveCount(0)
  await page.getByRole('button', { name: '显示神甘宁' }).click()
  await expect(page.locator('.home-page')).toHaveAttribute('data-hero', 'ganning')
  await expect(page.getByLabel('房间码')).toHaveCount(0)
  await page.getByRole('button', { name: '加入房间', exact: true }).click()
  await expect(page.getByLabel('房间码')).toBeVisible()
})

test('T21.4 native dual BGM switches, shares mute/volume, and reuses players', async ({ page }) => {
  await page.addInitScript(() => {
    const Native = window.Audio
    ;(window as any).__music = []
    window.Audio = function (...args: ConstructorParameters<typeof Audio>) {
      const node = new Native(...args)
      ;(window as any).__music.push(node)
      return node
    } as typeof Audio
    window.Audio.prototype = Native.prototype
  })
  await page.goto('/')
  expect(await page.evaluate(() => (window as any).__music.length)).toBe(0)
  await page.getByLabel('玩家昵称').fill('BGM验收')
  await page.getByLabel('玩家昵称').click()
  const music = () => page.evaluate(() => (window as any).__music.map((a: HTMLAudioElement) => ({ src: a.src, paused: a.paused, volume: a.volume, muted: a.muted, time: a.currentTime })))
  await expect.poll(async () => (await music()).some((a: any) => a.src.includes('lobby_bgm.wav') && !a.paused && a.time > .1)).toBe(true)
  await page.getByLabel('背景音乐音量').fill('0.35')
  await page.getByRole('button', { name: '单人游戏', exact: true }).click()
  await expect(page.locator('.general-card')).toHaveCount(10)
  expect((await music()).length).toBe(1)
  await page.locator('.general-card').first().click()
  await page.getByRole('button', { name: '确认武将' }).click()
  await expect(page.locator('.player-self')).toBeVisible()
  await expect.poll(async () => (await music()).filter((a: any) => !a.paused).map((a: any) => a.src.split('/').pop())).toEqual(['main_bgm.mp3'])
  expect((await music())[1].volume).toBe(.35)
  await page.getByRole('button', { name: '背景音乐 开' }).click()
  expect((await music()).every((a: any) => a.paused && a.muted)).toBe(true)
  await page.getByRole('button', { name: '离开牌局' }).click()
  expect((await music()).every((a: any) => a.paused)).toBe(true)
  await page.getByRole('button', { name: '背景音乐 关' }).click()
  await expect.poll(async () => (await music()).filter((a: any) => !a.paused).map((a: any) => a.src.split('/').pop())).toEqual(['lobby_bgm.wav'])
  expect((await music()).length).toBe(2)
  expect((await music())[0].volume).toBe(.35)
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  expect((await music()).every((a: any) => a.paused)).toBe(true)
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: false })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect.poll(async () => (await music()).filter((a: any) => !a.paused).length).toBe(1)
})

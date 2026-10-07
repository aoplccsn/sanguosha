import { test, expect } from '@playwright/test'
import fs from 'node:fs'

test('BGM starts after portraits and both Guo Jia surfaces play', async ({ page }) => {
  test.setTimeout(150000)
  const output = process.env.BGM_EVIDENCE_DIR ?? '../docs/t20_2_2/local'
  fs.mkdirSync(output, { recursive: true })
  const requests: string[] = []
  const media: any[] = []
  const session = await page.context().newCDPSession(page)
  await session.send('Network.enable')
  session.on('Network.responseReceived', event => {
    if (/main_bgm|mobile_god_guojia.*mp4/.test(event.response.url)) media.push({
      url: event.response.url, status: event.response.status, protocol: event.response.protocol,
      contentType: event.response.mimeType, size: event.response.headers['content-length'],
    })
  })
  page.on('request', request => requests.push(request.url()))
  await page.addInitScript(() => {
    const NativeAudio = window.Audio
    window.Audio = function (...args: ConstructorParameters<typeof Audio>) {
      const audio = new NativeAudio(...args)
      ;(window as any).__bgm = audio
      return audio
    } as typeof Audio
    window.Audio.prototype = NativeAudio.prototype
  })
  await page.goto('/?seed=0', { waitUntil: 'networkidle' })
  expect(requests.some(url => url.includes('main_bgm'))).toBe(false)
  await page.getByRole('button', { name: '测试模式', exact: true }).click()
  await page.getByLabel('测试权限码').fill(process.env.BGM_TEST_CODE ?? 'fixture-only-code')
  await page.getByRole('button', { name: '验证', exact: true }).click()
  await page.getByRole('button', { name: '创建测试房', exact: true }).click()
  await page.getByLabel('搜索武将或技能').fill('神郭嘉')
  await page.getByRole('button', { name: /神郭嘉/ }).first().click()
  await page.getByRole('button', { name: '确认武将', exact: true }).click()
  const panel = page.locator('.player-panel.player-self')
  await expect(panel).toHaveAttribute('data-character-id', 'mobile_god_guojia')
  const playback: any = {}
  async function verify(selector: string, name: string) {
    await page.waitForFunction(sel => {
      const video = document.querySelector(sel) as HTMLVideoElement
      return video && video.readyState >= 2 && !video.paused && getComputedStyle(video).opacity === '1'
    }, selector, { timeout: 45000 })
    const video = page.locator(selector)
    const before = await video.evaluate((v: HTMLVideoElement) => v.currentTime)
    await expect.poll(() => video.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(before + .5)
    playback[name] = await video.evaluate((v: HTMLVideoElement) => ({ src: v.currentSrc, currentTime: v.currentTime, readyState: v.readyState, paused: v.paused }))
    playback[name].before = before
  }
  await verify('.player-panel.player-self video', 'PlayerPanel')
  await page.waitForFunction(() => {
    const audio = (window as any).__bgm as HTMLAudioElement
    return audio && audio.readyState >= 2 && !audio.paused && audio.currentTime > .5
  }, null, { timeout: 45000 })
  await page.screenshot({ path: output + '/player-panel.png', timeout: 10000 })
  await panel.locator('.portrait-button').click()
  await verify('.game-general-detail video', 'GeneralDetail')
  const audioBefore = await page.evaluate(() => (window as any).__bgm.currentTime)
  await expect.poll(() => page.evaluate(() => (window as any).__bgm.currentTime)).toBeGreaterThan(audioBefore + .5)
  const audio = await page.evaluate(() => {
    const a = (window as any).__bgm as HTMLAudioElement
    return { src: a.currentSrc, paused: a.paused, currentTime: a.currentTime, preload: a.preload, muted: a.muted, volume: a.volume, loop: a.loop }
  })
  expect(audio.src).toContain('/main_bgm.mp3')
  expect(audio.preload).toBe('none')
  expect(audio.muted).toBe(false)
  expect(audio.volume).toBe(.2)
  expect(audio.loop).toBe(true)
  expect(requests.some(url => url.includes('main_bgm.wav'))).toBe(false)
  if (process.env.BGM_REQUIRE_HTTP2) {
    expect(media.filter(entry => /main_bgm.mp3|mobile_god_guojia.*mp4/.test(entry.url)).length).toBeGreaterThanOrEqual(3)
    expect(media.every(entry => entry.protocol === 'h2')).toBe(true)
  }
  await page.screenshot({ path: output + '/general-detail.png', timeout: 10000 })
  fs.writeFileSync(output + '/playback.json', JSON.stringify({ result: 'PASS', audio, playback, media }, null, 2))
})

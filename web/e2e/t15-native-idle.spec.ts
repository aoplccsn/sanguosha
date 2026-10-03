import fs from 'node:fs'
import { expect, test, type Page } from '@playwright/test'

async function fixture(page: Page, query = '') {
  await page.route('**/src/state/GameContext.tsx', route => route.fulfill({ contentType: 'application/javascript', body: `export function useGame() { return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(...args){window.__t15Submitted=args}}} }` }))
  await page.route('**/src/idlePortraits.ts', route => route.fulfill({ contentType: 'application/javascript', body: `export function idlePortrait(id) {return window.__t15DynamicIds.includes(id) ? {video:window.__t15VideoUrl} : undefined}` }))
  await page.goto('/e2e/fixtures/t15.html' + query)
  await expect(page.locator('.player-panel')).toHaveCount(5)
}
test('native five-player lifecycle, target click, detail, resize and VFX', async ({ page }) => {
  const errors: string[]=[]
  page.on('pageerror', error=>errors.push(error.message))
  await fixture(page)
  await expect(page.locator('video')).toHaveCount(5)
  await expect.poll(()=>page.locator('video').evaluateAll(nodes=>nodes.every(n=>!(n as HTMLVideoElement).paused && (n as HTMLVideoElement).readyState>=2))).toBe(true)
  await page.getByRole('button',{name:/杀/}).click()
  const target=page.locator('[data-player-id="p2"]')
  await expect(target).toHaveClass(/selectable/)
  await target.locator('.portrait-button').click()
  await expect(target).toHaveClass(/selected-target/)
  await expect(page.locator('.game-general-detail')).toHaveCount(0)
  await expect(page.getByRole('button',{name:'确定'})).toBeEnabled()
  await expect(page.locator('.combat-vfx-layer')).toBeVisible()
  const within=await target.evaluate(panel=>{const frame=panel.querySelector('.portrait-button')!.getBoundingClientRect();const media=panel.querySelector('video')!.getBoundingClientRect();return media.width<=frame.width && media.height<=frame.height && getComputedStyle(panel.querySelector('video')!).pointerEvents==='none'})
  expect(within).toBe(true)
  await page.screenshot({path:'../docs/t15/browser-five-native.png',fullPage:true})
  await page.getByLabel('战斗特效画质').selectOption('medium')
  await expect(page.locator('video')).toHaveCount(5)
  await page.getByLabel('战斗特效画质').selectOption('low')
  await expect(page.locator('video')).toHaveCount(0)
  await page.getByLabel('战斗特效画质').selectOption('high')
  await expect(page.locator('video')).toHaveCount(5)
  await page.emulateMedia({reducedMotion:'reduce'})
  await expect(page.locator('video')).toHaveCount(0)
  await page.emulateMedia({reducedMotion:'no-preference'})
  await expect(page.locator('video')).toHaveCount(5)
  await page.locator('.player-self .portrait-button').click()
  await expect(page.locator('.game-general-detail video')).toHaveCount(1)
  await page.locator('.modal-close').click()
  await page.setViewportSize({width:700,height:950})
  await expect(page.locator('.hp-row')).toHaveCount(5)
  await expect(page.locator('.mini-skills')).toHaveCount(5)
  // Move one actual panel out of the viewport and restore it.
  await target.evaluate(el=>(el as HTMLElement).style.transform='translateX(-200vw)')
  await expect.poll(()=>target.locator('video').evaluate(n=>(n as HTMLVideoElement).paused)).toBe(true)
  await target.evaluate(el=>(el as HTMLElement).style.transform='')
  await expect.poll(()=>target.locator('video').evaluate(n=>!(n as HTMLVideoElement).paused)).toBe(true)
  // CDP background lifecycle delivers a real document visibilitychange.
  const cdp=await page.context().newCDPSession(page)
  await cdp.send('Page.setWebLifecycleState',{state:'frozen'})
  await cdp.send('Page.setWebLifecycleState',{state:'active'})
  await expect.poll(()=>target.locator('video').evaluate(n=>!(n as HTMLVideoElement).paused)).toBe(true)
  await page.evaluate(()=>{const w=window as any;w.__t15State.publicEvents=[{event_id:'slash-test',kind:'CardUsedEvent',definition_id:'basic.slash',source_id:'p3',target_ids:['p2']},{event_id:'dodge-test',kind:'CardRespondedEvent',definition_id:'basic.dodge',source_id:'p2'}];w.__t15Render()})
  await expect(page.locator('.combat-vfx-layer')).toBeVisible()
  expect(errors).toEqual([])
})
test('missing runtime and play rejection keep static with identical bounds',async({page})=>{
  await fixture(page,'?missing')
  await expect(page.locator('video')).toHaveCount(0)
  await expect(page.locator('.dynamic-portrait img')).toHaveCount(5)
  await page.locator('.player-self .portrait-button').click()
  await expect(page.locator('.game-general-detail video')).toHaveCount(0)
  await expect(page.locator('.game-general-detail img')).toBeVisible()
  await page.addInitScript(()=>{HTMLMediaElement.prototype.play=()=>Promise.reject(new Error('test autoplay rejection'))})
  await fixture(page)
  await expect(page.locator('video')).toHaveCount(0)
  await expect(page.locator('.dynamic-portrait img')).toHaveCount(5)
})
test('application home starts with zero video requests',async({page})=>{
  const videos:string[]=[]
  page.on('request',request=>{if(/\.(mp4|webm)(?:\?|$)/.test(request.url()))videos.push(request.url())})
  await page.goto('/')
  await expect(page.getByLabel('玩家昵称')).toBeVisible()
  await expect(page.locator('video')).toHaveCount(0)
  expect(videos).toEqual([])
})

test('single portrait native loop, five-video decoder measurements and visibility listener', async ({ page }) => {
  await fixture(page,'?single')
  await expect(page.locator('video')).toHaveCount(1)
  const single=page.locator('video')
  await expect.poll(()=>single.evaluate(n=>(n as HTMLVideoElement).readyState)).toBeGreaterThanOrEqual(2)
  const loop=await single.evaluate(async node=>{
    const video=node as HTMLVideoElement
    const before=node.getBoundingClientRect().toJSON()
    let prior=video.currentTime, wraps=0
    for(let i=0;i<24;i++){await new Promise(r=>setTimeout(r,50));if(video.currentTime<prior)wraps++;prior=video.currentTime}
    return {wraps,before,after:node.getBoundingClientRect().toJSON()}
  })
  expect(loop.wraps).toBeGreaterThan(0)
  expect(loop.after).toEqual(loop.before)
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))})
  await expect.poll(()=>single.evaluate(n=>(n as HTMLVideoElement).paused)).toBe(true)
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'))})
  await expect.poll(()=>single.evaluate(n=>!(n as HTMLVideoElement).paused)).toBe(true)
  await fixture(page)
  await expect(page.locator('video')).toHaveCount(5)
  const playback=await page.locator('video').evaluateAll(async nodes=>{
    await new Promise(r=>setTimeout(r,1500))
    return nodes.map(node=>{const video=node as HTMLVideoElement;const quality=video.getVideoPlaybackQuality();return {width:video.videoWidth,height:video.videoHeight,total:quality.totalVideoFrames,dropped:quality.droppedVideoFrames,paused:video.paused}})
  })
  expect(playback.every(v=>v.total>0&&!v.paused)).toBe(true)
  fs.writeFileSync('../docs/t15/browser-mechanism-metrics.json',JSON.stringify({fixture:'synthetic 160x240 WebM; final MP4 artwork not available',loop,playback},null,2))
})

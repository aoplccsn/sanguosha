import { expect, test, type Page } from '@playwright/test'
import fs from 'node:fs'

async function open(page: Page, query = '') {
  await page.addInitScript(() => localStorage.setItem('sanguosha.vfx.quality.v1', 'high'))
  await page.route('**/src/state/GameContext.tsx', route => route.fulfill({ contentType: 'application/javascript', body: `export function useGame() { return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(...args){window.__t15Submitted=args}}} }` }))
  await page.goto('/e2e/fixtures/t15.html?real&' + query)
  await expect(page.locator('.player-panel')).toHaveCount(5)
}
async function playing(page: Page, count: number) {
  await expect(page.locator('video')).toHaveCount(count)
  await expect.poll(()=>page.locator('video').evaluateAll(nodes=>nodes.every(n=>{
    const video=n as HTMLVideoElement
    return !video.paused && video.readyState>=2 && video.videoWidth>0 && video.videoWidth/video.videoHeight===9/16
  }))).toBe(true)
}

test('God Lu Bu final MP4 vertical slice: playback, first click, quality, detail and fallback', async({page})=>{
  await open(page,'only-lvbu')
  await playing(page,1)
  const target=page.locator('[data-player-id="p2"]')
  await page.getByRole('button',{name:/杀/}).click()
  await target.locator('.portrait-button').click()
  await expect(target).toHaveClass(/selected-target/)
  await expect(page.getByRole('button',{name:'确定'})).toBeEnabled()
  await page.screenshot({path:'../docs/t15/lvbu-vertical-slice.png',fullPage:true})
  await page.getByLabel('战斗特效画质').selectOption('medium')
  await playing(page,1)
  await page.getByLabel('战斗特效画质').selectOption('low')
  await expect(page.locator('video')).toHaveCount(0)
  await page.getByLabel('战斗特效画质').selectOption('high')
  await playing(page,1)
  await page.emulateMedia({reducedMotion:'reduce'})
  await expect(page.locator('video')).toHaveCount(0)
  await page.emulateMedia({reducedMotion:'no-preference'})
  await playing(page,1)
  await page.getByRole('button',{name:/杀/}).click()
  await target.locator('.portrait-button').click()
  await expect(page.locator('.game-general-detail video')).toHaveCount(1)
  await page.screenshot({path:'../docs/t15/lvbu-detail.png',fullPage:true})
  const before=await page.locator('.game-general-detail .dynamic-portrait').boundingBox()
  await page.locator('.game-general-detail video').evaluate(node=>node.dispatchEvent(new Event('error')))
  await expect(page.locator('.game-general-detail video')).toHaveCount(0)
  expect(await page.locator('.game-general-detail .dynamic-portrait').boundingBox()).toEqual(before)
  await page.setViewportSize({width:700,height:950})
  await expect(page.locator('.game-general-detail img')).toBeVisible()
})

test('all nine real MP4s and matched statics in both five-player lineups',async({page})=>{
  for(const query of ['', 'second']) {
    await open(page,query)
    await playing(page,5)
    const entries=await page.locator('.player-panel').evaluateAll(panels=>panels.map(panel=>{
      const img=panel.querySelector('img')!,video=panel.querySelector('video')!
      const a=img.getBoundingClientRect(),b=video.getBoundingClientRect()
      return {video:video.getAttribute('src'),static:img.getAttribute('src'),boundsMatch:a.width===b.width&&a.height===b.height,clickThrough:getComputedStyle(video).pointerEvents==='none'}
    }))
    expect(entries.every(e=>e.boundsMatch&&e.clickThrough)).toBe(true)
    await page.screenshot({path:'../docs/t15/final-lineup'+(query?'2':'1')+'.png',fullPage:true})
    for(const panel of await page.locator('.portrait-button').all()) {
      await panel.click()
      await expect(page.locator('.game-general-detail video')).toHaveCount(1)
      await expect.poll(()=>page.locator('.game-general-detail video').evaluate(n=>(n as HTMLVideoElement).readyState)).toBeGreaterThanOrEqual(2)
      await page.locator('.modal-close').click()
    }
    await page.getByLabel('战斗特效画质').selectOption('low')
    await expect(page.locator('video')).toHaveCount(0)
    await page.screenshot({path:'../docs/t15/final-static'+(query?'2':'1')+'.png',fullPage:true})
  }
})

test('five real videos pause offscreen/hidden, resume and coexist with beam Slash and Dodge',async({page})=>{
  const errors:string[]=[]
  page.on('pageerror',e=>errors.push(e.message))
  await open(page)
  await playing(page,5)
  await page.getByRole('button',{name:/杀/}).click()
  await page.evaluate(()=>{
    const panel=document.querySelector('[data-player-id="p2"]')!
    let clicked=0
    panel.addEventListener('click',()=>{clicked=performance.now()},{capture:true,once:true})
    const observer=new MutationObserver(()=>{if(panel.classList.contains('selected-target')){(window as any).__t15ClickLatency=performance.now()-clicked;observer.disconnect()}})
    observer.observe(panel,{attributes:true,attributeFilter:['class']})
  })
  await page.locator('[data-player-id="p2"] .portrait-button').click()
  await expect(page.locator('[data-player-id="p2"]')).toHaveClass(/selected-target/)
  const targetClickMs=await page.evaluate(()=>(window as any).__t15ClickLatency)
  expect(targetClickMs).toBeLessThan(200)
  fs.writeFileSync('../docs/t15/target-click-metrics.json',JSON.stringify({fiveDynamicVideos:true,firstPhysicalPortraitClick:true,selectedClassMutationMs:targetClickMs},null,2))
  await page.evaluate(()=>{const w=window as any;w.__t15State.publicEvents=[{event_id:'real-slash',kind:'CardUsedEvent',definition_id:'basic.slash',source_id:'p3',target_ids:['p2']},{event_id:'real-dodge',kind:'CardRespondedEvent',definition_id:'basic.dodge',source_id:'p2'}];w.__t15Render()})
  await expect(page.locator('.combat-vfx-layer')).toBeVisible()
  const target=page.locator('[data-player-id="p2"]')
  await target.evaluate(n=>(n as HTMLElement).style.transform='translateX(-200vw)')
  await expect.poll(()=>target.locator('video').evaluate(n=>(n as HTMLVideoElement).paused)).toBe(true)
  await target.evaluate(n=>(n as HTMLElement).style.transform='')
  await playing(page,5)
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))})
  await expect.poll(()=>page.locator('video').evaluateAll(nodes=>nodes.every(n=>(n as HTMLVideoElement).paused))).toBe(true)
  const held=await page.locator('video').evaluateAll(ns=>ns.map(n=>(n as HTMLVideoElement).currentTime))
  await page.waitForTimeout(15000)
  const afterHold=await page.locator('video').evaluateAll(ns=>ns.map(n=>(n as HTMLVideoElement).currentTime))
  expect(afterHold.every((t,i)=>Math.abs(t-held[i])<0.05)).toBe(true)
  await target.evaluate(n=>(n as HTMLElement).style.transform='translateX(-200vw)')
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'))})
  await expect.poll(()=>target.locator('video').evaluate(n=>(n as HTMLVideoElement).paused)).toBe(true)
  await expect.poll(()=>page.locator('.player-panel:not([data-player-id="p2"]) video').evaluateAll(ns=>ns.every(n=>!(n as HTMLVideoElement).paused))).toBe(true)
  await target.evaluate(n=>(n as HTMLElement).style.transform='')
  await playing(page,5)
  await page.setViewportSize({width:1000,height:800})
  await expect(page.locator('.hp-row')).toHaveCount(5)
  expect(errors).toEqual([])
})

test('real missing MP4 and autoplay rejection preserve matching static',async({page})=>{
  await page.route('**/assets/portraits/idle/*.mp4',route=>route.fulfill({status:404,body:''}))
  await open(page)
  await expect(page.locator('video')).toHaveCount(0)
  await expect(page.locator('.dynamic-portrait img')).toHaveCount(5)
  await page.unroute('**/assets/portraits/idle/*.mp4')
  await page.addInitScript(()=>{HTMLMediaElement.prototype.play=()=>Promise.reject(new Error('autoplay test'))})
  await open(page)
  await expect(page.locator('video')).toHaveCount(0)
})

test('real single and five MP4 download size, native loop and decoder performance',async({page})=>{
  test.setTimeout(60000)
  const metrics:any={single:{},five:{}}
  for(const [name,query,count] of [['single','only-lvbu',1],['five','',5]] as const){
    const cdp=await page.context().newCDPSession(page)
    await cdp.send('Network.clearBrowserCache')
    await cdp.detach()
    await open(page,query)
    await playing(page,count)
    if(count===5){await page.getByRole('button',{name:/杀/}).click();await page.locator('[data-player-id="p2"] .portrait-button').click();await expect(page.locator('[data-player-id="p2"]')).toHaveClass(/selected-target/)}
    const sample=await page.locator('video').evaluateAll(async nodes=>{
      const start=nodes.map(n=>(n as HTMLVideoElement).getVideoPlaybackQuality())
      let longTasks=0
      const observer=new PerformanceObserver(list=>{longTasks+=list.getEntries().length})
      observer.observe({type:'longtask',buffered:false})
      const times:number[]=[];let previous=performance.now()
      await new Promise<void>(resolve=>{const end=performance.now()+12000;function tick(now:number){times.push(now-previous);previous=now;if(now<end)requestAnimationFrame(tick);else resolve()}requestAnimationFrame(tick)})
      observer.disconnect()
      return {frameCadenceFps:1000/(times.reduce((a,b)=>a+b,0)/times.length),p95FrameMs:times.sort((a,b)=>a-b)[Math.floor(times.length*.95)],longTasks,playback:nodes.map((n,i)=>{const v=n as HTMLVideoElement,q=v.getVideoPlaybackQuality();return {src:v.getAttribute('src'),total:q.totalVideoFrames-start[i].totalVideoFrames,dropped:q.droppedVideoFrames-start[i].droppedVideoFrames,currentTime:v.currentTime,loop:v.loop,duration:v.duration,width:v.videoWidth,height:v.videoHeight,paused:v.paused}})}
    })
    expect(sample.playback.every(v=>v.total>200&&!v.paused&&v.loop&&v.duration===10)).toBe(true)
    const entries=await page.evaluate(()=>performance.getEntriesByType('resource').filter(e=>e.name.includes('/portraits/idle/')).map(e=>{const r=e as PerformanceResourceTiming;return {url:r.name,transferSize:r.transferSize,encodedBodySize:r.encodedBodySize}}))
    const paths=sample.playback.map(v=>v.src!)
    await page.locator('video').evaluateAll(nodes=>nodes.forEach(n=>n.dispatchEvent(new Event('error'))))
    const staticBaseline=await page.evaluate(async()=>{
      let previous=performance.now();const times:number[]=[]
      await new Promise<void>(resolve=>{const end=performance.now()+3000;function tick(now:number){times.push(now-previous);previous=now;if(now<end)requestAnimationFrame(tick);else resolve()}requestAnimationFrame(tick)})
      return {fps:1000/(times.reduce((a,b)=>a+b,0)/times.length),p95Ms:times.sort((a,b)=>a-b)[Math.floor(times.length*.95)]}
    })
    metrics[name]={...sample,interactiveBeamActive:count===5,staticBaseline,network:entries,uniqueRuntimeBytes:paths.reduce((sum,src)=>sum+fs.statSync('../assets/'+src.replace('/assets/','')).size,0)}
  }
  fs.writeFileSync('../docs/t15/final-browser-metrics.json',JSON.stringify(metrics,null,2))
})

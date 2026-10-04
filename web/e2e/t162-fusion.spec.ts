import {test,expect} from '@playwright/test'
import fs from 'node:fs'
const label=process.env.T162_LABEL??'before'
test('three portrait samples before after and matched static fallback',async({page})=>{
 await page.setViewportSize({width:1440,height:1000})
 await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
 await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
 await page.goto('/e2e/fixtures/t15.html?real')
 await expect(page.locator('.player-panel')).toHaveCount(5)
 await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2&&!n.paused))).toBe(true)
 // Freeze native video at the same loop time for reproducible comparison only.
 await page.locator('video').evaluateAll(ns=>ns.forEach(n=>{const v=n as HTMLVideoElement;v.pause();v.currentTime=.5}))
 await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>Math.abs((n as HTMLVideoElement).currentTime-.5)<.1&&!(n as HTMLVideoElement).seeking))).toBe(true)
 await page.screenshot({path:`../docs/t16_2/${label}-five.png`,fullPage:true})
 const entries:any[]=[]
 for(const [seat,name] of [['p2','lvbu'],['p3','guanyu'],['p1','zhangjiao']]){
  const panel=page.locator(`[data-player-id="${seat}"]`)
  await panel.screenshot({path:`../docs/t16_2/${label}-${name}-dynamic.png`})
  entries.push(await panel.evaluate(n=>{const media=n.querySelector('.dynamic-portrait')!;const img=media.querySelector('img')!,video=media.querySelector('video')!;const style=(el:Element)=>{const s=getComputedStyle(el);return {bounds:el.getBoundingClientRect().toJSON(),position:s.objectPosition,fit:s.objectFit,transform:s.transform,pointer:s.pointerEvents}};return {id:n.getAttribute('data-player-id'),mask:getComputedStyle(media).maskImage,img:style(img),video:style(video),loop:(video as HTMLVideoElement).loop}}))
 }
 await page.getByLabel('战斗特效画质').selectOption('low')
 await expect(page.locator('video')).toHaveCount(0)
 await page.screenshot({path:`../docs/t16_2/${label}-five-static.png`,fullPage:true})
 for(const [seat,name] of [['p2','lvbu'],['p3','guanyu'],['p1','zhangjiao']])await page.locator(`[data-player-id="${seat}"]`).screenshot({path:`../docs/t16_2/${label}-${name}-static.png`})
 fs.writeFileSync(`../docs/t16_2/${label}-geometry.json`,JSON.stringify(entries,null,2))
})


test('prototype mask survives decode failure, quality and visibility with matching media geometry',async({page})=>{
 await page.setViewportSize({width:1440,height:1000})
 await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
 await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
 await page.goto('/e2e/fixtures/t15.html?real')
 await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2&&!n.paused))).toBe(true)
 const records:any[]=[]
 for(const [seat,name] of [['p2','lvbu'],['p3','guanyu'],['p1','zhangjiao']]){
  const panel=page.locator(`[data-player-id="${seat}"]`),media=panel.locator('.dynamic-portrait')
  const before=await media.evaluate(n=>({bounds:n.getBoundingClientRect().toJSON(),mask:getComputedStyle(n).maskImage}))
  const video=panel.locator('video')
  const duration=await video.evaluate(n=>(n as HTMLVideoElement).duration)
  expect(duration).toBeGreaterThan(0)
  await video.evaluate(n=>{const v=n as HTMLVideoElement;v.currentTime=v.duration-.15})
  await expect.poll(()=>video.evaluate(n=>(n as HTMLVideoElement).currentTime),{intervals:[50,100,200]}).toBeLessThan(duration/2)
  await video.evaluate(n=>n.dispatchEvent(new Event('error')))
  await expect(video).toHaveCount(0)
  const after=await media.evaluate(n=>({bounds:n.getBoundingClientRect().toJSON(),mask:getComputedStyle(n).maskImage}))
  expect(after).toEqual(before)
  await panel.screenshot({path:`../docs/t16_2/error-${name}-static.png`})
  records.push({name,duration,loopWrapped:true,failureGeometryUnchanged:true,mask:after.mask})
 }
 await page.getByLabel('战斗特效画质').selectOption('low');await expect(page.locator('video')).toHaveCount(0)
 await page.getByLabel('战斗特效画质').selectOption('high');await expect(page.locator('video')).toHaveCount(2)
 // Nonfailed videos retain existing pause/resume behavior.
 const unaffected=page.locator('[data-player-id="p4"]')
 await unaffected.evaluate(n=>(n as HTMLElement).style.transform='translateX(-200vw)')
 await expect.poll(()=>unaffected.locator('video').evaluate(n=>(n as HTMLVideoElement).paused)).toBe(true)
 await unaffected.evaluate(n=>(n as HTMLElement).style.transform='')
 await expect.poll(()=>unaffected.locator('video').evaluate(n=>!(n as HTMLVideoElement).paused)).toBe(true)
 await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))})
 await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).paused))).toBe(true)
 await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'))})
 await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>!(n as HTMLVideoElement).paused))).toBe(true)
 await page.emulateMedia({reducedMotion:'reduce'});await expect(page.locator('video')).toHaveCount(0)
 await page.emulateMedia({reducedMotion:'no-preference'});await expect(page.locator('video')).toHaveCount(2)
 fs.writeFileSync('../docs/t16_2/fallback-loop.json',JSON.stringify(records,null,2))
 await page.evaluate(()=>{const w=window as any;w.__t15State.projection.players.push(...[6,7,8].map(n=>({...w.__t15State.projection.players[0],player_id:'p'+n,name:'玩家'+n,character_id:'caocao',character_name:'曹操',active:false})));w.__t15Render()})
 await expect(page.locator('.eight-seats .player-panel')).toHaveCount(8)
 await page.screenshot({path:'../docs/t16_2/after-eight-fallback.png',fullPage:true})
})

test('fixed mask alpha preserves face and weapon cores while feathering outer background',async({page})=>{
 await page.goto('/')
 const profiles=[{name:'lvbu',face:[260,148],weapon:[46,320]},{name:'guanyu',face:[247,110],weapon:[75,575]},{name:'zhangjiao',face:[238,185],weapon:[469,405]}]
 const stats=[]
 for(const profile of profiles){
  const data=await page.evaluate(async profile=>{const img=new Image();img.src=`/src/portraits/fusion/${profile.name}.svg`;await img.decode();const canvas=document.createElement('canvas');canvas.width=506;canvas.height=900;const ctx=canvas.getContext('2d')!;ctx.drawImage(img,0,0,506,900);const alpha=(p:number[])=>ctx.getImageData(p[0],p[1],1,1).data[3]/255;return {name:profile.name,face:alpha(profile.face),weapon:alpha(profile.weapon),corner:alpha([500,5]),topBackground:alpha([420,10])}},profile)
  console.log(JSON.stringify(data))
  expect(data.face).toBeGreaterThan(.97);expect(data.weapon).toBeGreaterThan(.9);expect(data.corner).toBeLessThan(.1);expect(data.topBackground).toBeLessThan(.25)
  stats.push(data)
 }
 fs.writeFileSync('../docs/t16_2/mask-alpha.json',JSON.stringify(stats,null,2))
})


test('face down mirrors the mask and media together, without mirroring UI',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
 await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
 await page.goto('/e2e/fixtures/t15.html?real')
 await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2))).toBe(true)
 await page.evaluate(()=>{const w=window as any;for(const p of w.__t15State.projection.players)p.face_up=false;w.__t15Render()})
 for(const seat of ['p1','p2','p3']){
  const panel=page.locator(`[data-player-id="${seat}"]`)
  await expect(panel).toHaveClass(/face-down/)
  expect(await panel.locator('.dynamic-portrait').evaluate(n=>getComputedStyle(n).transform)).toBe('matrix(-1, 0, 0, 1, 0, 0)')
  expect(await panel.locator('.dynamic-portrait > img, .dynamic-portrait > video').evaluateAll(ns=>ns.every(n=>getComputedStyle(n).transform==='none'))).toBe(true)
  expect(await panel.locator('.player-heading').evaluate(n=>getComputedStyle(n).transform)).toBe('none')
 }
 await page.screenshot({path:'../docs/t16_2/face-down.png',fullPage:true})
})

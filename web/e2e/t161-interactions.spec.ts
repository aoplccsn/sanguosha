import {test,expect} from '@playwright/test'
import fs from 'node:fs'

test('first target and final card/response clicks at zero one three five videos',async({page})=>{
 const metrics:any[]=[]
 for(const count of [0,1,3,5]){
  await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
  await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(...args){window.__submissions=(window.__submissions??[]).concat([args])}}}}`}))
  await page.route('**/src/idlePortraits.ts',async r=>{const response=await r.fetch();await r.fulfill({response,body:(await response.text()).replace('return assets[id]',`return ['forest_god_lvbu','wind_god_guanyu','fire_god_zhouyu','mountain_god_zhaoyun','wind_zhang_jiao'].slice(0,${count}).includes(id) ? assets[id] : undefined`)})})
  await page.goto('/e2e/fixtures/t15.html?real')
  await expect(page.locator('video')).toHaveCount(count)
  await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2))).toBe(true)
  await page.getByRole('button',{name:/杀/}).click()
  const target=page.locator('[data-player-id="p2"]')
  await expect(target).toHaveClass(/selectable/)
  await target.evaluate(panel=>{let start=0;panel.addEventListener('click',()=>start=performance.now(),{once:true,capture:true});const o=new MutationObserver(()=>{if(panel.classList.contains('selected-target')){(window as any).__latency=performance.now()-start;o.disconnect()}});o.observe(panel,{attributes:true,attributeFilter:['class']})})
  await target.locator('.portrait-button').click()
  await expect(target).toHaveClass(/selected-target/)
  const latency=await page.evaluate(()=>(window as any).__latency)
  expect(latency).toBeLessThan(200)
  expect(await page.evaluate(()=>(window as any).__submissions)).toBeUndefined()
  await expect(page.locator('.player-self')).toHaveClass(/active/)
  await page.getByRole('button',{name:'确定'}).click()
  expect(await page.evaluate(()=>(window as any).__submissions)).toEqual([['t15',{option:'use:slash-1',targets:['p2']}]])
  await page.evaluate(()=>{const w=window as any;w.__t15State.pendingRequest={request_id:'response',player_id:'p1',request_type:'respond_with_card',prompt:'请打出闪',choices:[],allowed_player_ids:[],required_definition_id:'basic.dodge',eligible_card_ids:['dodge-1'],allow_pass:true,min_count:1,max_count:1,subject_player_id:'p2',remaining_ms:60000};w.__t15State.projection={...w.__t15State.projection,hand:[{...w.__t15State.projection.hand[0],card_id:'dodge-1',name:'闪',definition_id:'basic.dodge'}]};w.__t15Render()})
  await page.getByRole('button',{name:/闪/}).click()
  expect(await page.evaluate(()=>(window as any).__submissions.length)).toBe(1)
  await page.getByRole('button',{name:'确定'}).click()
  expect(await page.evaluate(()=>(window as any).__submissions[1])).toEqual(['response','dodge-1'])
  metrics.push({count,firstTargetClickMs:latency,cardFinalConfirm:true,responseFinalConfirm:true})
  await page.unroute('**/src/state/GameContext.tsx');await page.unroute('**/src/idlePortraits.ts')
 }
 fs.writeFileSync('../docs/t16_1/interaction-metrics.json',JSON.stringify(metrics,null,2))
})

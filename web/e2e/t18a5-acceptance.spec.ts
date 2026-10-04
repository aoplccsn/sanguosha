import { test, expect } from '@playwright/test'
import fs from 'node:fs'
async function fixture(page: any, query='') {
 await page.addInitScript(()=>{localStorage.setItem('sanguosha.vfx.quality.v1','high');localStorage.setItem('sanguosha.web.speed','normal')})
 await page.route('**/src/state/GameContext.tsx', (r:any)=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
 await page.goto('/e2e/fixtures/t15.html?real&'+query)
 await expect(page.locator('.player-panel')).toHaveCount(5)
}
test('normal thinking is singular, timed, followed by named action and immediate human response',async({page})=>{
 await fixture(page,'only-lvbu')
 await page.evaluate(()=>{
  const w=window as any,s=w.__t15State;s.pendingRequest=null
  s.projection.players[0].character_name='曹操';s.projection.players[1].character_name='刘备'
  s.publicEvents=[{event_id:'thinking',kind:'AIThinkingEvent',source_id:'p1',complexity:'ordinary'},{event_id:'slash',kind:'CardUsedEvent',source_id:'p1',target_ids:['p2'],definition_id:'basic.slash',card_name:'杀'}]
  w.__t15Transitions=[];let last='';new MutationObserver(()=>{const text=document.querySelector('.event-stage')?.textContent||'';if(text!==last){w.__t15Transitions.push({text,time:performance.now()});last=text}}).observe(document.querySelector('#root')!,{subtree:true,childList:true,characterData:true});w.__t15Render()
 })
 await expect(page.locator('.event-stage')).toContainText('曹操 正在思考……')
 await expect(page.locator('.thinking')).toHaveCount(1)
 await page.waitForTimeout(300)
 await page.screenshot({path:'../docs/t18a5/thinking.png'})
 await expect(page.locator('.event-stage')).toContainText('曹操 对 刘备 使用【杀】')
 await expect(page.locator('[data-player-id="p1"]')).toHaveClass(/presenting-action/)
 await expect(page.locator('[data-player-id="p2"]')).toHaveClass(/event-target/)
 await expect(page.locator('.thinking')).toHaveCount(0)
 await page.screenshot({path:'../docs/t18a5/action.png'})
 const transitions=await page.evaluate(()=>(window as any).__t15Transitions)
 const elapsed=transitions.find((x:any)=>x.text.includes('使用'))!.time-transitions.find((x:any)=>x.text.includes('思考'))!.time
 expect(elapsed).toBeGreaterThanOrEqual(2300);expect(elapsed).toBeLessThan(2900)
 await page.evaluate(()=>{const w=window as any;w.__t15State.publicEvents=[...w.__t15State.publicEvents,{event_id:'think-again',kind:'AIThinkingEvent',source_id:'p3',complexity:'complex'}];w.__t15Render()})
 await expect(page.locator('.thinking')).toHaveCount(1)
 const humanStart=Date.now()
 await page.evaluate(()=>{const w=window as any;w.__t15State.seatId='p2';w.__t15State.pendingRequest={request_id:'human',player_id:'p2',request_type:'respond_with_card',prompt:'刘备进入响应：请打出闪',choices:[],eligible_card_ids:[],allowed_player_ids:[],min_count:0,max_count:1,allow_pass:true,remaining_ms:60000};w.__t15Render()})
 await expect(page.locator('.decision-prompt')).toContainText('刘备进入响应')
 await expect(page.locator('.thinking')).toHaveCount(0)
 const humanMs=Date.now()-humanStart;expect(humanMs).toBeLessThan(500)
 fs.writeFileSync('../docs/t18a5/thinking-timing.json',JSON.stringify({ordinaryMs:elapsed,humanPromptMs:humanMs,transitions},null,2))
})
test('nine native 360x640 PlayerPanel portraits and static fallback audit captures',async({page})=>{
 for(const query of ['', 'second']){
  await fixture(page,query)
  await page.setViewportSize({width:1600,height:1000})
  await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2))).toBe(true)
  for(const panel of await page.locator('.player-panel').all()){
   const id=await panel.getAttribute('data-character-id')
   if(query==='second' && id==='fire_god_zhouyu')continue
   await panel.locator('.portrait-button').click()
   await expect.poll(()=>page.locator('.game-general-detail video').evaluate(n=>(n as HTMLVideoElement).readyState)).toBeGreaterThanOrEqual(2)
   await page.locator('.game-general-detail').screenshot({path:'../docs/t18a5/'+id+'-detail.png'})
   await page.locator('.modal-close').click()
   await panel.evaluate(n=>{const p=n as HTMLElement;p.style.width='360px';p.style.height='640px';p.style.position='fixed';p.style.inset='100px auto auto 600px';p.style.zIndex='99'})
   // The fallback is only on screen before playback starts, so the static/dynamic
   // handoff can only be judged against the video's first painted frame. These 10s
   // masters are camera moves, so a live mid-loop capture is not the handoff state.
   await panel.locator('video').evaluate(async node=>{
    const v=node as HTMLVideoElement
    v.pause()
    if(v.currentTime>0) await new Promise<void>(resolve=>{v.addEventListener('seeked',()=>resolve(),{once:true});v.currentTime=0})
    await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())))
   })
   await panel.screenshot({path:'../docs/t18a5/'+id+'-dynamic.png'})
   await panel.locator('video').evaluate(n=>n.dispatchEvent(new Event('error')))
   await expect(panel.locator('video')).toHaveCount(0)
   await expect.poll(()=>panel.locator('img').evaluate(n=>(n as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
   await panel.screenshot({path:'../docs/t18a5/'+id+'-static.png'})
   await panel.evaluate(n=>(n as HTMLElement).removeAttribute('style'))
  }
 }
})
test('real single-player AI emits visible thinking after ending human turn',async({page})=>{
 test.setTimeout(60000)
 await page.goto('/?seed=3')
 await page.getByLabel('玩家昵称').fill('T18A5本地验收')
 await page.getByRole('button',{name:'单人游戏'}).click()
 await page.locator('.general-card').first().click()
 await page.getByRole('button',{name:'确认武将'}).click()
 await expect(page.locator('.game-page')).toBeVisible()
 await page.getByRole('button',{name:'结束出牌',exact:true}).click()
 await expect(page.locator('.decision-prompt')).toContainText('Discard 1')
 await page.locator('.hand-card').first().click()
 await page.getByRole('button',{name:'确定',exact:true}).click()
 await expect(page.locator('.thinking')).toHaveCount(1,{timeout:15000})
 await expect(page.locator('.event-stage')).toContainText('正在思考')
 await page.waitForTimeout(300)
 await page.screenshot({path:'../docs/t18a5/real-game-thinking.png'})
 await expect(page.locator('.thinking')).toHaveCount(0,{timeout:15000})
 fs.writeFileSync('../docs/t18a5/real-game.txt',await page.locator('.game-page').innerText())
})

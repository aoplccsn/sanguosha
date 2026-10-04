import {test,expect} from '@playwright/test'
import fs from 'node:fs'
test.beforeEach(async({page},testInfo)=>{
 if(testInfo.title.startsWith('network diagnostics')) return
 await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(...args){window.__submissions=(window.__submissions??[]).concat([args])}}}}`}))
 await page.goto('/e2e/fixtures/t15.html?real')
 await expect(page.locator('.player-panel')).toHaveCount(5)
})
test('incarnation hover, keyboard focus and touch detail retain first option click',async({page})=>{
 const catalog=await (await page.request.get('/api/catalog/generals')).json()
 await page.evaluate(catalog=>{const w=window as any;w.__t15State.generals=Object.fromEntries(catalog.map((g:any)=>[g.id,g]));w.__t15State.pendingRequest={...w.__t15State.pendingRequest,request_id:'huashen',prompt:'化身：选择武将及技能',choices:['caocao:jianxiong'],play_card_targets:undefined};w.__t15Render()},catalog)
 const choice=page.getByRole('button',{name:'曹操 · 奸雄',exact:true})
 await choice.hover();await expect(page.getByRole('tooltip')).toContainText('受到')
 await choice.focus();await expect(page.getByRole('tooltip')).toContainText('奸雄')
 await page.keyboard.press('Escape');await expect(page.getByRole('tooltip')).toHaveCount(0)
 await page.getByRole('button',{name:'查看曹操技能说明'}).click();await expect(page.getByRole('tooltip')).toContainText('体力')
 await choice.click();expect(await page.evaluate(()=>(window as any).__submissions)).toEqual([['huashen','caocao:jianxiong']])
})
test('three speeds have measured intervals; human request bypasses queue',async({page})=>{
 const metrics:Record<string,number>={}
 for(const speed of ['normal','slow','fast']){
  await page.getByLabel('对局速度').selectOption(speed)
  await page.evaluate(speed=>{const w=window as any;w.__t15State.pendingRequest=null;w.__t15State.publicEvents=[1,2,3].map(n=>({kind:'CardUsedEvent',event_id:speed+n,source_id:'p2',card_name:'杀'}));w.__t15Render()},speed)
  await page.evaluate(()=>{const w=window as any;w.__eventTimes={};const watch=()=>{const el=document.querySelector('[data-event-id]');if(el){const id=el.getAttribute('data-event-id')!;w.__eventTimes[id]??=performance.now()}};watch();new MutationObserver(watch).observe(document.querySelector('.game-board')!,{childList:true,subtree:true,attributes:true})})
  const first=page.locator(`[data-event-id="${speed}1"]`);await expect(first).toBeVisible()
  const started=Date.now();await expect(page.locator(`[data-event-id="${speed}2"]`)).toBeVisible();metrics[speed]=await page.evaluate(speed=>{const times=(window as any).__eventTimes;return times[speed+'2']-times[speed+'1']},speed)
  await page.evaluate(()=>{const w=window as any;w.__t15State.pendingRequest={request_id:'human',player_id:'p1',request_type:'respond_with_card',prompt:'请响应',choices:[],eligible_card_ids:[],allowed_player_ids:[],remaining_ms:60000,allow_pass:true};w.__t15Render()})
  await expect(page.getByText('请响应',{exact:true})).toBeVisible();await expect(page.locator('[data-event-id]')).toHaveCount(0)
 }
 expect(metrics.slow).toBeGreaterThan(metrics.normal+200);expect(metrics.fast).toBeLessThan(metrics.normal-200)
 fs.mkdirSync('../docs/t16',{recursive:true});fs.writeFileSync('../docs/t16/pacing-metrics.json',JSON.stringify(metrics,null,2))
})
test('five and eight seat visual layouts, live portraits, target beam and first click',async({page})=>{
 await page.setViewportSize({width:1440,height:1000})
 await expect(page.locator('.dynamic-portrait')).toHaveCount(5)
 await page.getByRole('button',{name:/杀/}).click();await page.locator('[data-player-id="p2"] .portrait-button').click();await expect(page.locator('[data-player-id="p2"]')).toHaveClass(/selected-target/)
 await expect(page.locator('canvas.combat-vfx-layer')).toBeVisible()
 await page.screenshot({path:'../docs/t16/five.png',fullPage:true})
 await page.evaluate(()=>{const w=window as any;w.__t15State.projection.players=[...w.__t15State.projection.players,...[6,7,8].map(n=>({...w.__t15State.projection.players[0],player_id:'p'+n,name:'玩家'+n,character_id:'caocao',character_name:'曹操',active:false}))];w.__t15Render()})
 await expect(page.locator('.eight-seats .player-panel')).toHaveCount(8)
 const boxes=await page.locator('.player-panel').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}))
 for(let a=0;a<boxes.length;a++)for(let b=a+1;b<boxes.length;b++){const x=boxes[a],y=boxes[b];expect(x.x+x.w<=y.x||y.x+y.w<=x.x||x.y+x.h<=y.y||y.y+y.h<=x.y).toBe(true)}
 await page.screenshot({path:'../docs/t16/eight.png',fullPage:true})
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'../docs/t16/eight-mobile.png',fullPage:true})
})
test('network diagnostics performs actual local HTTP/assets/WS/heartbeat and uses current origin',async({page})=>{
 await page.unroute('**/src/state/GameContext.tsx')
 const sockets:string[]=[];page.on('websocket',ws=>sockets.push(ws.url()))
 await page.goto('/network-diagnostics');await page.getByRole('button',{name:'重新检测'}).click()
 await expect(page.getByText(/HTTP：正常/)).toBeVisible({timeout:25000})
 const report=page.locator('pre');await expect(report).toContainText('静态资源：正常');await expect(report).toContainText('实时连接：正常');await expect(report).toContainText('持续连接：正常')
 expect(sockets.some(url=>url===new URL(page.url()).origin.replace(/^http/,'ws')+'/api/network/ws')).toBe(true)
 await expect(page.getByRole('button',{name:'复制诊断结果'})).toBeVisible()
 fs.writeFileSync('../docs/t16/network-local-'+new URL(page.url()).port+'.txt',await report.innerText())
 await page.screenshot({path:'../docs/t16/network.png',fullPage:true})
})

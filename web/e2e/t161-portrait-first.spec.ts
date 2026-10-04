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
 fs.mkdirSync('../docs/t16_1',{recursive:true});fs.writeFileSync('../docs/t16_1/pacing-metrics.json',JSON.stringify(metrics,null,2))
})
test('five and eight seat visual layouts, live portraits, target beam and first click',async({page})=>{
 await page.setViewportSize({width:1440,height:1000})
 await expect(page.locator('.dynamic-portrait')).toHaveCount(5)
 await page.getByRole('button',{name:/杀/}).click();await page.locator('[data-player-id="p2"] .portrait-button').click();await expect(page.locator('[data-player-id="p2"]')).toHaveClass(/selected-target/)
 await expect(page.locator('canvas.combat-vfx-layer')).toBeVisible()
 await page.evaluate(()=>{const w=window as any;const p=w.__t15State.projection;p.hand=[p.hand[0],...[2,3,4,5].map(n=>({...p.hand[0],card_id:'card-'+n,name:n%2?'闪':'桃',definition_id:n%2?'basic.dodge':'basic.peach'}))];p.players[1].equipment=[{card_id:'weapon',name:'青龙偃月刀',definition_id:'equipment.green_dragon_blade',details:'武器 · 范围 3'}];p.players[1].skill_labels=['无双','神愤'];w.__t15Render()})
 await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2&&!n.paused))).toBe(true)
 await page.screenshot({path:'../docs/t16_1/five.png',fullPage:true})
 await page.evaluate(()=>{const w=window as any;w.__t15State.projection.players=[...w.__t15State.projection.players,...[6,7,8].map(n=>({...w.__t15State.projection.players[0],player_id:'p'+n,name:'玩家'+n,character_id:'caocao',character_name:'曹操',active:false}))];w.__t15Render()})
 await expect(page.locator('.eight-seats .player-panel')).toHaveCount(8)
 const boxes=await page.locator('.player-panel').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}))
 for(let a=0;a<boxes.length;a++)for(let b=a+1;b<boxes.length;b++){const x=boxes[a],y=boxes[b];expect(x.x+x.w<=y.x||y.x+y.w<=x.x||x.y+x.h<=y.y||y.y+y.h<=x.y).toBe(true)}
 await page.screenshot({path:'../docs/t16_1/eight.png',fullPage:true})
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'../docs/t16_1/eight-mobile.png',fullPage:true})
})
test('network diagnostics performs actual local HTTP/assets/WS/heartbeat and uses current origin',async({page})=>{
 await page.unroute('**/src/state/GameContext.tsx')
 const sockets:string[]=[];page.on('websocket',ws=>sockets.push(ws.url()))
 await page.goto('/network-diagnostics');await page.getByRole('button',{name:'重新检测'}).click()
 await expect(page.getByText(/HTTP：正常/)).toBeVisible({timeout:25000})
 const report=page.locator('pre');await expect(report).toContainText('静态资源：正常');await expect(report).toContainText('实时连接：正常');await expect(report).toContainText('持续连接：正常')
 expect(sockets.some(url=>url===new URL(page.url()).origin.replace(/^http/,'ws')+'/api/network/ws')).toBe(true)
 await expect(page.getByRole('button',{name:'复制诊断结果'})).toBeVisible()
 fs.mkdirSync('../docs/t16_1',{recursive:true});fs.writeFileSync('../docs/t16_1/network-local-'+new URL(page.url()).port+'.txt',await report.innerText())
 await page.screenshot({path:'../docs/t16_1/network.png',fullPage:true})
})


test('portrait area, dense edge information and seat separation at desktop and tablet sizes',async({page})=>{
 const metrics:any[]=[]
 for(const size of [{width:1440,height:1000},{width:1366,height:768},{width:1024,height:768}]){
  await page.setViewportSize(size)
  for(const count of [5,8]){
   await page.evaluate(count=>{const w=window as any;const p=w.__t15State.projection;p.players=p.players.slice(0,5);if(count===8)p.players.push(...[6,7,8].map(n=>({...p.players[0],player_id:'p'+n,name:'玩家'+n,character_id:'caocao',character_name:'曹操',active:false})));p.players[1].equipment=[{card_id:'weapon',name:'青龙偃月刀',definition_id:'equipment.green_dragon_blade',details:'武器 · 范围 3'},{card_id:'armor',name:'八卦阵',definition_id:'equipment.eight_diagram',details:'防具'}];p.players[1].judgments=[{card_id:'delay',name:'乐不思蜀',details:'跳过出牌阶段'}];p.players[1].skill_labels=['无双','神愤'];p.players[1].marks={rage:4};w.__t15Render()},count)
   await expect(page.locator('.player-panel')).toHaveCount(count)
   const layout=await page.locator('.player-panel').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();const portrait=n.querySelector('.portrait-button')!.getBoundingClientRect();const caption=n.querySelector('.seat-caption')!.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,portraitRatio:portrait.width*portrait.height/(r.width*r.height),captionRatio:caption.height/r.height,border:getComputedStyle(n).borderTopWidth}}))
   for(const r of layout){expect(r.portraitRatio).toBeGreaterThan(.95);expect(r.captionRatio).toBeLessThan(.45);expect(r.border).toBe('0px');expect(r.x).toBeGreaterThanOrEqual(0);expect(r.x+r.w).toBeLessThanOrEqual(size.width);expect(r.y+r.h).toBeLessThanOrEqual(size.height)}
   for(let a=0;a<layout.length;a++)for(let b=a+1;b<layout.length;b++){const x=layout[a],y=layout[b];expect(x.x+x.w<=y.x||y.x+y.w<=x.x||x.y+x.h<=y.y||y.y+y.h<=x.y).toBe(true)}
   expect(await page.locator('.dynamic-portrait, .dynamic-portrait img, .dynamic-portrait video').evaluateAll(ns=>ns.every(n=>getComputedStyle(n).pointerEvents==='none'))).toBe(true)
   await page.getByRole('button',{name:/杀/}).click()
   const target=page.locator('[data-player-id="p2"]')
   await expect.poll(()=>target.evaluate(n=>getComputedStyle(n,'::after').borderBottomColor)).toBe('rgba(242, 215, 141, 0.6)')
   const legal=await target.evaluate(n=>getComputedStyle(n,'::after').boxShadow)
   await target.locator('.portrait-button').click({position:{x:70,y:75}})
   await expect(target).toHaveClass(/selected-target/)
   await expect.poll(()=>target.evaluate(n=>getComputedStyle(n,'::after').borderBottomColor)).toBe('rgb(255, 227, 160)')
   expect(await target.evaluate(n=>getComputedStyle(n,'::after').boxShadow)).not.toBe(legal)
   const prompt=await page.locator('.decision-prompt').boundingBox()
   // Controls are beside the local portrait; its face stays clear.
   const face=await page.locator('.player-self .portrait-button').boundingBox()
   expect(prompt!.x).toBeGreaterThanOrEqual(face!.x+face!.width-2)
   await target.locator('.equipment-token').first().hover();await expect(target.locator('.equipment-preview').first()).toBeVisible()
   await page.mouse.move(size.width/2,50)
   await page.screenshot({path:`../docs/t16_1/${count}-seats-${size.width}x${size.height}.png`,fullPage:true})
   await page.getByRole('button',{name:'取消',exact:true}).click()
   await expect(target).not.toHaveClass(/selected-target/)
   await expect(page.getByRole('button',{name:'确定',exact:true})).toBeDisabled()
   expect(await page.evaluate(()=>(window as any).__submissions)).toBeUndefined()
   metrics.push({count,...size,layout})
   // Clear the selected card for the next iteration.
   await page.getByRole('button',{name:'取消',exact:true}).click()
  }
 }
 fs.writeFileSync('../docs/t16_1/layout-metrics.json',JSON.stringify(metrics,null,2))
})


test('Slash and Dodge VFX render against full portrait seats',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 const canvas=page.locator('canvas.combat-vfx-layer')
 for(const [kind,definition_id,text] of [['CardUsedEvent','basic.slash','使用'],['CardRespondedEvent','basic.dodge','打出']]){
  await page.evaluate(({kind,definition_id})=>{const w=window as any;w.__t15State.pendingRequest=null;w.__t15State.publicEvents=[...w.__t15State.publicEvents,{event_id:kind,kind,definition_id,source_id:'p3',target_ids:['p2'],card_name:'杀'}];w.__t15Render()},{kind,definition_id})
  await expect(page.locator(`[data-event-id="${kind}"]`)).toContainText(text)
  await expect.poll(()=>canvas.evaluate((c:HTMLCanvasElement)=>{const data=c.getContext('2d')!.getImageData(0,0,c.width,c.height).data;for(let i=3;i<data.length;i+=4)if(data[i]>0)return true;return false}),{intervals:[25,50,100]}).toBe(true)
  await page.screenshot({path:`../docs/t16_1/${definition_id}.png`,fullPage:true})
 }
 expect(errors).toEqual([])
})

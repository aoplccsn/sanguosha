import {test,expect} from '@playwright/test'
async function start(page:any,request:any,caseName:string){
  const wire:any[]=[]
  page.on('websocket',(s:any)=>s.on('framereceived',(f:any)=>{try{const m=JSON.parse(String(f.payload));if(m.type==='PUBLIC_EVENT'||m.type==='PENDING_REQUEST')wire.push({...m,time:Date.now()})}catch{}}))
  const res=await request.post('http://127.0.0.1:8008/audit/fixture/'+caseName);expect(res.ok()).toBe(true)
  const record=await res.json()
  await page.addInitScript((record:any)=>{localStorage.setItem('sanguosha.web.session.v1',JSON.stringify(record));localStorage.setItem('sanguosha.web.speed','normal')},record)
  await page.goto('/')
  await page.getByRole('button',{name:'继续对局',exact:true}).click()
  await expect(page.locator('.game-page')).toBeVisible()
  return wire
}
test('A AI Cao Cao Slash -> human Liu Bei Dodge, persistent turn and semantic responder',async({page,request})=>{
  await page.setViewportSize({width:1440,height:1000});const wire=await start(page,request,'A')
  await expect(page.locator('[data-player-id="p2"] .turn-badge')).toContainText('出牌')
  await expect(page.locator('.event-stage')).toHaveAttribute('data-stage','target',{timeout:20000})
  await page.screenshot({path:'../docs/t18a8/A-trajectory.png'})
  await expect(page.locator('[data-player-id="p1"] .responder-state')).toContainText('响应【杀】',{timeout:20000})
  await expect(page.locator('[data-player-id="p1"] .responder-state')).toContainText('请出【闪】')
  await expect(page.locator('.base-card img')).toHaveAttribute('alt','杀')
  expect((await page.locator('.base-card').boundingBox())!.width).toBeGreaterThanOrEqual(120)
  expect((await page.locator('.base-card').boundingBox())!.width).toBeLessThanOrEqual(155)
  expect(await page.locator('.base-card').evaluate((n:any)=>getComputedStyle(n).pointerEvents)).toBe('none')
  const used=wire.find(m=>m.event?.kind==='CardUsedEvent')
  const pending=wire.find(m=>m.type==='PENDING_REQUEST'&&m.request?.required_definition_id==='basic.dodge')
  expect(pending.time-used.time).toBeLessThan(250)
  await page.screenshot({path:'../docs/t18a8/A-slash-response.png'})
  await page.locator('.hand').getByRole('button',{name:/^闪 /}).first().click();await page.getByRole('button',{name:'确定',exact:true}).click()
  await expect(page.locator('.response-card img')).toHaveAttribute('alt','闪')
  await page.screenshot({path:'../docs/t18a8/A-dodge.png'})
  await expect(page.locator('[data-player-id="p1"].responding')).toHaveCount(0)
})
test('B human Slash -> AI seat thinking then visible Dodge',async({page,request})=>{
  await page.setViewportSize({width:1440,height:1000});await start(page,request,'B')
  await page.locator('.hand').getByRole('button',{name:/^杀 /}).click();await page.locator('[data-player-id="p2"].selectable').click()
  const begun=Date.now();await page.getByRole('button',{name:'确定',exact:true}).click()
  await expect(page.locator('[data-player-id="p2"]')).toHaveClass(/responding.*thinking/)
  await expect(page.locator('[data-player-id="p2"] .responder-state')).toContainText('请出【闪】')
  await expect(page.locator('.event-stage')).not.toContainText('思考')
  await expect(page.locator('.response-card img')).toHaveAttribute('alt','闪',{timeout:20000})
  expect(Date.now()-begun).toBeGreaterThanOrEqual(3500)
  await page.screenshot({path:'../docs/t18a8/B-ai-dodge.png'})
})
for(const [caseName,card,response] of [['C','南蛮入侵','杀'],['D','万箭齐发','闪']])test(caseName+' authoritative AOE fanout and ordered response',async({page,request})=>{
  await start(page,request,caseName)
  await expect(page.locator('.base-card img')).toHaveAttribute('alt',card,{timeout:25000})
  await expect(page.locator('.aoe-badge')).toHaveCount(4)
  await expect(page.locator('.event-stage')).toHaveAttribute('data-stage','target')
  await page.screenshot({path:'../docs/t18a8/'+caseName+'-trajectories.png'})
  await expect(page.locator('[data-player-id="p1"] .responder-state')).toContainText('请出【'+response+'】')
  await page.screenshot({path:'../docs/t18a8/'+caseName+'-fanout.png'})
  await page.locator('.hand').getByRole('button',{name:new RegExp('^'+response+' ')}).first().click();await page.getByRole('button',{name:'确定',exact:true}).click()
  await expect(page.locator('[data-player-id="p2"].responding')).toBeVisible({timeout:15000})
  await expect(page.locator('[data-player-id="p1"] .aoe-badge')).toHaveText('已结算')
})
test('E both counter commands and root card stay visible',async({page,request})=>{
  await start(page,request,'E')
  await expect(page.getByRole('button',{name:'使用无懈',exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'不响应',exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'本次不无懈',exact:true})).toBeVisible()
  await expect(page.locator('.base-card img')).toHaveAttribute('alt','南蛮入侵')
  await page.screenshot({path:'../docs/t18a8/E-controls.png'})
  await page.getByRole('button',{name:'本次不无懈',exact:true}).click()
  await expect(page.getByRole('button',{name:'本次不无懈',exact:true})).toHaveCount(0)
})
test('F counter and counter-counter retain original trick and final parity',async({page,request})=>{
  await start(page,request,'F')
  await page.locator('.hand').getByRole('button',{name:/^无懈可击 /}).click();await page.getByRole('button',{name:'使用无懈',exact:true}).click()
  await expect(page.locator('.base-card img')).toHaveAttribute('alt','南蛮入侵')
  await expect(page.locator('.response-card img')).toHaveAttribute('alt','无懈可击')
  await expect(page.locator('.nullification-status')).toContainText('无懈×1')
  await expect(page.locator('.nullification-status')).toContainText('无懈×2',{timeout:30000})
  await expect(page.locator('.nullification-status')).toContainText('锦囊有效')
  await page.screenshot({path:'../docs/t18a8/F-counter-chain.png'})
})
for(const size of [{width:390,height:844},{width:430,height:932}])test('mobile '+size.width+' semantic response and controls visible',async({page,request})=>{
  await page.setViewportSize(size);await start(page,request,'A')
  await expect(page.locator('[data-player-id="p1"] .responder-state')).toContainText('请出【闪】',{timeout:20000})
  await expect(page.getByRole('button',{name:'确定',exact:true})).toBeInViewport()
  await expect(page.locator('.base-card')).toBeInViewport()
  await page.screenshot({path:'../docs/t18a8/mobile-'+size.width+'.png',fullPage:true})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.locator('.hand').getByRole('button',{name:/^闪 /}).first().click()
  await page.getByRole('button',{name:'确定',exact:true}).click()
  await expect(page.locator('.response-card img')).toHaveAttribute('alt','闪',{timeout:10000})
  expect((await page.locator('.response-card').boundingBox())!.width).toBeLessThanOrEqual(105)
  await page.screenshot({path:'../docs/t18a8/mobile-flash-'+(await page.locator('.player-panel').count())+'-'+size.width+'.png',fullPage:true})
})

for(const size of [{width:390,height:844},{width:430,height:932}])test('eight-player mobile '+size.width+' keeps response and controls readable',async({page,request})=>{
  await page.setViewportSize(size);await start(page,request,'A8')
  await expect(page.locator('.player-panel')).toHaveCount(8)
  await expect(page.locator('[data-player-id="p1"] .responder-state')).toContainText('请出【闪】',{timeout:20000})
  await expect(page.getByRole('button',{name:'确定',exact:true})).toBeInViewport()
  await expect(page.locator('.base-card')).toBeInViewport()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.screenshot({path:'../docs/t18a8/mobile-eight-'+size.width+'.png',fullPage:true})
  await page.locator('.hand').getByRole('button',{name:/^闪 /}).first().click()
  await page.getByRole('button',{name:'确定',exact:true}).click()
  await expect(page.locator('.response-card img')).toHaveAttribute('alt','闪',{timeout:10000})
  expect((await page.locator('.response-card').boundingBox())!.width).toBeLessThanOrEqual(105)
  await page.screenshot({path:'../docs/t18a8/mobile-flash-'+(await page.locator('.player-panel').count())+'-'+size.width+'.png',fullPage:true})
})

for(const size of [{width:1440,height:1000},{width:390,height:844},{width:430,height:932}])for(const [caseName,card] of [['C','南蛮入侵'],['D','万箭齐发'],['E','南蛮入侵']])test('compact '+size.width+' '+caseName+' does not overlap interaction',async({page,request})=>{
 await page.setViewportSize(size);await start(page,request,caseName)
 await expect(page.locator('.base-card img')).toHaveAttribute('alt',card,{timeout:30000})
 await expect(page.locator('.decision-prompt')).toBeVisible({timeout:30000})
 const boxes=await page.evaluate(()=>{
  const card=document.querySelector('.base-card')!.getBoundingClientRect()
  const intersects=(r:DOMRect)=>card.left<r.right&&card.right>r.left&&card.top<r.bottom&&card.bottom>r.top
  return {width:card.width,overlapButtons:Array.from(document.querySelectorAll('.decision-prompt button,.hand button,.skill-bar button')).some(n=>intersects(n.getBoundingClientRect())),overlapSeats:Array.from(document.querySelectorAll('.player-panel')).some(n=>intersects(n.getBoundingClientRect())),pointer:getComputedStyle(document.querySelector('.base-card')!).pointerEvents}
 })
 expect(boxes.width).toBeLessThanOrEqual(size.width>720?155:105)
 expect(boxes.overlapButtons).toBe(false);expect(boxes.overlapSeats).toBe(false);expect(boxes.pointer).toBe('none')
 if(caseName==='E'){
  await page.locator('.hand').getByRole('button',{name:/^无懈可击 /}).click();await page.getByRole('button',{name:'使用无懈',exact:true}).click()
  await expect(page.locator('.response-card img')).toHaveAttribute('alt','无懈可击')
 }
 await page.screenshot({path:'../docs/t18a8/compact-'+size.width+'-'+caseName+'.png',fullPage:true})
})

for(const size of [{width:1440,height:1000},{width:390,height:844},{width:430,height:932}])for(const [caseName,card] of [['C','南蛮入侵'],['D','万箭齐发'],['E','南蛮入侵']])test('eight compact '+size.width+' '+caseName+' does not overlap interaction',async({page,request})=>{
 await page.setViewportSize(size);await start(page,request,caseName+'8')
 await expect(page.locator('.base-card img')).toHaveAttribute('alt',card,{timeout:30000})
 await expect(page.locator('.decision-prompt')).toBeVisible({timeout:30000})
 const boxes=await page.evaluate(()=>{
  const card=document.querySelector('.base-card')!.getBoundingClientRect()
  const intersects=(r:DOMRect)=>card.left<r.right&&card.right>r.left&&card.top<r.bottom&&card.bottom>r.top
  return {width:card.width,overlapButtons:Array.from(document.querySelectorAll('.decision-prompt button,.hand button,.skill-bar button')).some(n=>intersects(n.getBoundingClientRect())),overlapSeats:Array.from(document.querySelectorAll('.player-panel')).some(n=>intersects(n.getBoundingClientRect())),pointer:getComputedStyle(document.querySelector('.base-card')!).pointerEvents}
 })
 expect(boxes.width).toBeLessThanOrEqual(size.width>720?155:105)
 expect(boxes.overlapButtons).toBe(false);expect(boxes.overlapSeats).toBe(false);expect(boxes.pointer).toBe('none')
 if(caseName==='E'){
  await page.locator('.hand').getByRole('button',{name:/^无懈可击 /}).click();await page.getByRole('button',{name:'使用无懈',exact:true}).click()
  await expect(page.locator('.response-card img')).toHaveAttribute('alt','无懈可击')
 }
 await page.screenshot({path:'../docs/t18a8/compact-eight-'+size.width+'-'+caseName+'.png',fullPage:true})
})

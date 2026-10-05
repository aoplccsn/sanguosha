import { fileURLToPath } from 'node:url'
import { test, expect, type Page } from '@playwright/test'
const screenshot = (name: string) => fileURLToPath(new URL('../../docs/t18a9/' + name, import.meta.url))
const fixture = async (request: any, kind: string) => {
 const res = await request.post('/audit/fixture/' + kind); expect(res.ok()).toBeTruthy(); return res.json()
}
async function enter(page: Page, record: any) {
 await page.addInitScript((r) => {
  localStorage.setItem('sanguosha.web.session.v1', JSON.stringify(r))
  const Native = window.WebSocket
  ;(window as any).__sockets = []
  window.WebSocket = class extends Native { constructor(url: string | URL, protocols?: string | string[]) { super(url, protocols); (window as any).__sockets.push(this) } }
 }, record)
 await page.goto('/'); await page.getByRole('button', {name:'继续对局',exact:true}).click()
 await expect(page.locator('.game-page')).toBeVisible()
}
async function images(page: Page, selector: string) {
 await expect.poll(() => page.locator(selector).evaluateAll(nodes => nodes.every(n => (n as HTMLImageElement).complete && (n as HTMLImageElement).naturalWidth > 0))).toBeTruthy()
 const urls = await page.locator(selector).evaluateAll(nodes => nodes.map(n => (n as HTMLImageElement).src))
 expect(urls.every(u => !u.includes('default_card'))).toBeTruthy()
}
test('76 catalog portraits and every registered card art load over production HTTP', async ({request}) => {
 const catalog = await (await request.get('/api/catalog/generals')).json(); expect(catalog).toHaveLength(76)
 const urls = catalog.map((g:any) => g.portrait); expect(new Set(urls).size).toBe(76)
 const manifest = await (await request.get('/assets/manifest.json')).json()
 const cardPaths = [...new Set(Object.entries(manifest).filter(([key]) => /^(basic|trick|delayed|equipment)\./.test(key)).map(([,v]) => '/assets/' + v))]
 for (const url of [...urls, ...cardPaths]) {
  const response = await request.get(String(url)); expect(response.status(),String(url)).toBe(200)
  expect(response.headers()['content-type']).toMatch(/^image\/(webp|png)/)
  expect((await response.body()).length).toBeGreaterThan(100)
 }
 console.log('production smoke:', urls.length, 'portraits;', cardPaths.length, 'card arts')
})
for (const size of [{width:1440,height:1000},{width:390,height:844},{width:430,height:932}]) {
 test('snatch hidden back and public equipment ' + size.width, async ({page,request}) => {
  await page.setViewportSize(size); const records = await fixture(request,'snatch')
  const wire:any[]=[]; page.on('websocket',s=>s.on('framereceived',f=>{try{wire.push(JSON.parse(String(f.payload)))}catch{}}))
  await enter(page,records[0]); const panel=page.getByRole('dialog',{name:'顺手牵羊'})
  await expect(panel).toBeVisible(); await images(page,'.hand img'); await images(page,'.temporary-cards .hand-card img')
  await expect(panel.getByRole('button',{name:'取消',exact:true})).toHaveCount(0)
  const latest = wire.filter(m=>m.type==='PROJECTION_UPDATE').at(-1).projection
  expect(latest.hand.length).toBeGreaterThan(0)
  for(const player of latest.players.filter((p:any)=>p.player_id!=='p1')) { expect(player.hand).toBeUndefined(); expect(player.revealed_hand).toEqual([]) }
  const req=wire.filter(m=>m.type==='PENDING_REQUEST').at(-1).request
  expect(req.eligible_card_ids.filter((id:string)=>id.startsWith('hidden-hand:'))).toHaveLength(2)
  await panel.getByRole('button',{name:'暗置手牌 1',exact:true}).click()
  await expect(panel.getByRole('button',{name:'确认',exact:true})).toBeEnabled()
  await expect(panel.getByRole('button',{name:'确认',exact:true})).toBeInViewport()
  await page.screenshot({path:screenshot(`snatch-${size.width}.png`)})
  await panel.getByRole('button',{name:'确认',exact:true}).click(); await expect(panel).toHaveCount(0)
  await expect(page.locator('.game-notice')).toHaveCount(0,{timeout:5000})
 })
}
test('snatch publicly visible equipment is selected and obtained authoritatively', async ({page,request}) => {
 const records=await fixture(request,'snatch');await enter(page,records[0]);const panel=page.getByRole('dialog',{name:'顺手牵羊'})
 await panel.getByRole('button',{name:/诸葛连弩/}).click();await panel.getByRole('button',{name:'确认',exact:true}).click()
 await expect(panel).toHaveCount(0);await expect(page.locator('.hand').getByRole('button',{name:/诸葛连弩/})).toBeVisible()
})
test('harvest has sequential authoritative selection, observer restriction and refresh recovery', async ({browser,request}) => {
 test.setTimeout(180000); const records=await fixture(request,'harvest'); const contexts=[]; const pages:Page[]=[]
 try {
  for(const record of records) { const context=await browser.newContext(); contexts.push(context); const page=await context.newPage(); pages.push(page); await enter(page,record) }
  for(let i=0;i<8;i++) {
   const page=pages[i];const panel=page.getByRole('dialog',{name:'五谷丰登'})
   await expect(panel.locator('.hand-card')).toHaveCount(8-i)
   if(i===0) { await expect(pages[1].getByRole('dialog').getByRole('button',{name:'确认',exact:true})).toHaveCount(0); await page.screenshot({path:screenshot('harvest-desktop.png')}) }
   if(i===1) { await page.setViewportSize({width:390,height:844}); await page.screenshot({path:screenshot('harvest-390.png')}); await page.setViewportSize({width:430,height:932}); await page.screenshot({path:screenshot('harvest-430.png')}); await page.reload();await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(panel.locator('.hand-card')).toHaveCount(7) }
   await panel.locator('.hand-card').first().click();await panel.getByRole('button',{name:'确认',exact:true}).click()
  }
  for(const page of pages) await expect(page.getByRole('dialog',{name:'五谷丰登'})).toHaveCount(0)
 } finally { for(const context of contexts) await context.close() }
})
test('compact slash remains click-through and recovered banner disappears',async({page,request})=>{
 const records=await fixture(request,'slash');await page.setViewportSize({width:1440,height:1000});await enter(page,records[0])
 await page.locator('.hand').getByRole('button',{name:/^杀 /}).first().click();await page.getByRole('button',{name:'选择目标曹丕',exact:true}).click();await page.getByRole('button',{name:'确定',exact:true}).click()
 await expect(page.locator('.center-action-card').first()).toBeVisible()
 const card=page.locator('.center-action-card').first();const box=await card.boundingBox();expect(box!.width).toBeGreaterThanOrEqual(85);expect(box!.width).toBeLessThanOrEqual(110)
 expect(await card.evaluate(n=>getComputedStyle(n).pointerEvents)).toBe('none')
 await page.screenshot({path:screenshot('slash-desktop.png')})
 for(const size of [{width:390,height:844},{width:430,height:932}]) {await page.setViewportSize(size);const mobile=await card.boundingBox();expect(mobile!.width).toBeGreaterThanOrEqual(58);expect(mobile!.width).toBeLessThanOrEqual(78);await page.screenshot({path:screenshot(`slash-${size.width}.png`)})}
 await page.evaluate(()=>{const sockets=(window as any).__sockets;sockets.at(-1).close()})
 await expect(page.getByText('连接恢复中…',{exact:true})).toBeVisible()
 await expect(page.getByText('连接恢复中…',{exact:true})).toHaveCount(0,{timeout:12000})
 await expect(page.getByText('连接已恢复',{exact:true})).toHaveCount(0,{timeout:4000})
 await expect(page.getByText('当前响应已更新',{exact:true})).toHaveCount(0)
})

test('same-request snapshots never spam notices, rejection expires, failed reconnect is finite', async ({page,request}) => {
 const records=await fixture(request,'snatch')
 let socket:any; let first=true; let attempts=0
 await page.routeWebSocket('**/ws', s=> {
  attempts++; if(!first){s.onMessage(()=>s.close());return}; first=false;socket=s
  s.onMessage(raw=>{const m=JSON.parse(String(raw));if(m.type==='RECONNECT') {
   s.send(JSON.stringify({type:'WELCOME',...{room_code:records[0].roomCode,seat_id:'p1',reconnect_token:'test'}}))
   s.send(JSON.stringify({type:'PROJECTION_UPDATE',active_request_id:'r',projection:{players:[{player_id:'p1',name:'你',character_name:'赵云',character_id:'zhaoyun',faction:'蜀',identity_label:'主公',active:true,alive:true,hp:4,max_hp:4,hand_count:0,equipment:[],judgments:[],skill_labels:[],attack_range:1}],hand:[],shared_cards:[],current_phase:'play',turn_number:1,deck_count:100,discard_count:0,result:null,discard_top:null}}))
   s.send(JSON.stringify({type:'PENDING_REQUEST',request:{request_id:'r',player_id:'p1',request_type:'choose_option',prompt:'请选择',choices:['end_play_phase'],eligible_card_ids:[],allowed_player_ids:[],allow_pass:false,min_count:1,max_count:1,remaining_ms:60000}}))
  }})
 })
 await enter(page,records[0]);
 for(let i=0;i<4;i++) socket.send(JSON.stringify({type:'PENDING_REQUEST',request:{request_id:'r',player_id:'p1',request_type:'choose_option',prompt:'请选择',choices:['end_play_phase'],eligible_card_ids:[],allowed_player_ids:[],allow_pass:false,min_count:1,max_count:1,remaining_ms:59000-i}}))
 await expect(page.getByText('当前响应已更新',{exact:true})).toHaveCount(0)
 socket.send(JSON.stringify({type:'ERROR',request_id:'r',message:'stale request'}))
 await expect(page.getByText('当前响应已更新',{exact:true})).toBeVisible()
 await expect(page.getByText('当前响应已更新',{exact:true})).toHaveCount(0,{timeout:3000})
 await page.clock.install();await socket.close()
 await expect(page.getByText('连接恢复中…',{exact:true})).toBeVisible()
 for(let i=2;i<=6;i++) {
  await page.clock.runFor(8000);await expect.poll(()=>attempts).toBeGreaterThanOrEqual(i)
  await expect.poll(()=>page.evaluate(()=>(window as any).__sockets.at(-1).readyState)).toBe(3)
 }
 await expect(page.getByRole('button',{name:'重新连接',exact:true})).toBeVisible()
 await expect(page.getByText('连接恢复中…',{exact:true})).toHaveCount(0)
})

test('dismantlement reuses the zone panel and discards selected equipment',async({page,request})=>{
 const records=await fixture(request,'dismantle');await enter(page,records[0]);const panel=page.getByRole('dialog',{name:'过河拆桥'})
 await expect(panel).toContainText('请选择弃置的一张牌');await panel.getByRole('button',{name:/诸葛连弩/}).click();await panel.getByRole('button',{name:'确认',exact:true}).click()
 await expect(panel).toHaveCount(0);await expect(page.locator('[data-player-id="p2"] .equipment-token')).toHaveCount(0)
 await expect(page.locator('.hand').getByRole('button',{name:/诸葛连弩/})).toHaveCount(0)
})
test('harvest counter response stays actionable inside the temporary panel',async({browser,request})=>{
 const records=await fixture(request,'harvest_interrupt');const first=await browser.newContext(),second=await browser.newContext()
 try {
  const a=await first.newPage(),b=await second.newPage();await enter(a,records[0]);await enter(b,records[1]);const panel=a.getByRole('dialog',{name:'五谷丰登'})
  await panel.locator('.hand-card').first().click();await panel.getByRole('button',{name:'确认',exact:true}).click()
  await expect(panel.getByRole('button',{name:'本次不无懈',exact:true})).toBeVisible()
  await expect(panel.locator('.temporary-content')).toContainText('当前响应手牌')
  await panel.getByRole('button',{name:'本次不无懈',exact:true}).click()
  await expect(b.getByRole('dialog',{name:'五谷丰登'}).getByRole('button',{name:'确认',exact:true})).toBeVisible()
 } finally {await first.close();await second.close()}
})

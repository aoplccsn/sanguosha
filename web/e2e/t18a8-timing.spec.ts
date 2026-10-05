import { test, expect } from '@playwright/test'
import fs from 'node:fs'
async function start(page:any,request:any,name:string){
 const events:any[]=[];const projections:any[]=[]
 page.on('websocket',(socket:any)=>socket.on('framereceived',(f:any)=>{try{const m=JSON.parse(String(f.payload));if(m.type==='PUBLIC_EVENT')events.push({...m.event,time:Date.now()});if(m.type==='PROJECTION_UPDATE')projections.push({...m.projection,time:Date.now()})}catch{}}))
 const res=await request.post('http://127.0.0.1:8008/audit/fixture/'+name);expect(res.ok()).toBe(true)
 const record=await res.json()
 await page.addInitScript((r:any)=>{localStorage.setItem('sanguosha.web.session.v1',JSON.stringify(r));localStorage.setItem('sanguosha.web.speed','normal')},record)
 await page.goto('/');await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(page.locator('.game-page')).toBeVisible()
 return {events,projections}
}
for(const [name,count] of [['P',0],['Q',1],['R',3]] as const)test('measured '+count+' action AI turn',async({page,request})=>{
 const begun=Date.now();const {events,projections}=await start(page,request,name)
 await expect(page.locator('.game-hud')).toContainText('第 2 回合',{timeout:100000})
 const ending=events.find(e=>e.kind==='TurnEndedEvent'&&e.player_id==='p5')
 const used=events.filter(e=>e.kind==='CardUsedEvent'&&e.source_id==='p5')
 expect(used).toHaveLength(count)
 expect((ending?.time??Date.now())-begun).toBeGreaterThanOrEqual(5000)
 for(let i=1;i<used.length;i++)expect(used[i].time-used[i-1].time).toBeGreaterThanOrEqual(3500)
 fs.writeFileSync('../docs/t18a8/timing-'+name+'.json',JSON.stringify({elapsedMs:(ending?.time??Date.now())-begun,used,events,projections},null,2))
 await page.screenshot({path:'../docs/t18a8/timing-'+name+'.png'})
})
test('AI Dodge and its own reading window',async({page,request})=>{
 const {events}=await start(page,request,'B')
 await page.locator('.hand').getByRole('button',{name:/^杀 /}).click();await page.locator('[data-player-id="p2"].selectable').click()
 const begun=Date.now();await page.getByRole('button',{name:'确定',exact:true}).click()
 await expect(page.locator('.response-card img')).toHaveAttribute('alt','闪',{timeout:25000})
 const elapsedMs=Date.now()-begun
 expect(elapsedMs).toBeGreaterThanOrEqual(4500)
 const card=page.locator('.response-card img');await page.waitForTimeout(4000);await expect(card).toHaveAttribute('alt','闪')
 fs.writeFileSync('../docs/t18a8/timing-dodge.json',JSON.stringify({elapsedMs,events},null,2))
})
test('AI Nullification has a readable decision and response',async({page,request})=>{
 const {events}=await start(page,request,'N')
 await page.locator('.hand').getByRole('button',{name:/^无中生有 /}).click()
 const begun=Date.now();await page.getByRole('button',{name:'确定',exact:true}).click()
 await expect(page.locator('[data-player-id="p2"].thinking')).toBeVisible()
 await expect(page.locator('.response-card img')).toHaveAttribute('alt','无懈可击',{timeout:25000})
 const elapsedMs=Date.now()-begun;expect(elapsedMs).toBeGreaterThanOrEqual(4500)
 await page.waitForTimeout(4000);await expect(page.locator('.response-card img')).toHaveAttribute('alt','无懈可击')
 await page.screenshot({path:'../docs/t18a8/ai-nullification.png'})
 fs.writeFileSync('../docs/t18a8/timing-nullification.json',JSON.stringify({elapsedMs,events},null,2))
})
test('seven completely skipped AI turns remain distinct for a whole eight-seat round',async({page,request})=>{
 const {events,projections}=await start(page,request,'X8')
 const begun=Date.now();await page.getByRole('button',{name:'结束出牌',exact:true}).click()
 await expect(page.locator('.game-hud')).toContainText('第 8 回合',{timeout:60000})
 await expect(page.locator('[data-player-id="p1"] .turn-badge')).toBeVisible({timeout:10000})
 const turns=events.filter(e=>e.kind==='TurnStartedEvent')
 expect(turns.slice(0,3).map(e=>e.player_id)).toEqual(['p2','p3','p4'])
 for(let i=1;i<turns.length;i++)expect(turns[i].time-turns[i-1].time).toBeGreaterThanOrEqual(5400)
 fs.writeFileSync('../docs/t18a8/timing-empty-eight.json',JSON.stringify({elapsedMs:Date.now()-begun,turns,projections},null,2))
})

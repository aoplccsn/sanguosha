import { test, expect } from '@playwright/test'
import fs from 'node:fs'
for (const mode of ['military-five','military-eight']) test(mode+' real several turns presentation audit',async({page})=>{
  test.setTimeout(1800000)
  const requests: any[] = [], events:any[] = [], errors:string[]=[];let ownProjection:any=null
  page.on('pageerror',e=>errors.push(e.message))
  page.on('websocket',socket=>socket.on('framereceived',frame=>{try{const m=JSON.parse(String(frame.payload));if(m.type==='PROJECTION_UPDATE')ownProjection=m.projection;if(m.type==='PENDING_REQUEST')requests.push(m.request);if(m.type==='PUBLIC_EVENT')events.push({...m.event, receivedAt:Date.now()})}catch{}}))
  await page.setViewportSize({width:1440,height:1000})
  await page.addInitScript(()=>{
    localStorage.setItem('sanguosha.web.speed','normal')
    const Original=window.WebSocket
    window.WebSocket=class extends Original{constructor(url:string|URL,protocols?:string|string[]){super(url,protocols);(window as any).__auditSocket=this}} as typeof WebSocket
  })
  await page.goto('/?seed=3')
  await page.getByLabel('玩家昵称').fill('T18A8回合验收')
  await page.getByLabel('对局模式',{exact:true}).selectOption(mode)
  await page.getByRole('button',{name:'单人游戏',exact:true}).click()
  await page.locator('.general-card').first().click()
  await page.getByRole('button',{name:'确认武将',exact:true}).click()
  await expect(page.locator('.game-page')).toBeVisible()
  await page.evaluate(()=>{
    const w=window as any;w.__observations=[];let previous=''
    w.__observeTimer=setInterval(()=>{const stage=document.querySelector('.event-stage');const seats=Array.from(document.querySelectorAll('.player-panel')).map(n=>({id:n.getAttribute('data-player-id'),classes:n.className,timer:n.querySelector('.seat-timer')?.textContent}));const row={time:performance.now(),hud:document.querySelector('.game-hud')?.textContent,action:stage?.textContent,stage:stage?.getAttribute('data-stage'),card:stage?.querySelector('img')?.getAttribute('alt'),seats};const key=JSON.stringify({...row,time:0,seats:seats.map(x=>({...x,timer:!!x.timer}))});if(key!==previous){w.__observations.push(row);previous=key}},100)
  })
  const answered=new Set<string>();let captures=0;let lastStage='';const started=Date.now();let lastProgress=0
  while(Date.now()-started<1600000){
    const hud=await page.evaluate(()=>document.querySelector('.game-hud')?.textContent??'')
    expect(await page.locator('.game-page').count(), 'audit must keep a real game mounted').toBe(1)
    const turn=Number(hud.match(/第 (\d+) 回合/)?.[1]??0)
    if(turn >= (mode === 'military-eight' ? 17 : 11) || await page.locator('.result-overlay').count())break
    const r=requests.at(-1)
    if(r&&!answered.has(r.request_id)){
      answered.add(r.request_id)
      let value:any
      if(r.request_type==='yes_no')value=false
      else if(r.request_type==='respond_with_card')value=r.eligible_card_ids[0]??{pass:true}
      else if(r.request_type==='choose_option'){
        const defensive=(ownProjection?.hand??[]).find((c:any)=>(c.definition_id==='basic.peach'||c.definition_id.startsWith('equipment.'))&&r.choices.includes('use:'+c.card_id))
        value=defensive?'use:'+defensive.card_id:r.choices.includes('end_play_phase')?'end_play_phase':r.choices[0]
      }
      else if(r.request_type==='choose_cards'){
        const keep=(id:string)=>{const c=ownProjection?.hand?.find((c:any)=>c.card_id===id);return c?.definition_id==='basic.peach'?5:c?.definition_id==='basic.dodge'?4:c?.definition_id==='trick.nullification'?3:0}
        value=[...r.eligible_card_ids].sort((a:string,b:string)=>keep(a)-keep(b)).slice(0,r.min_count)
      }
      else if(r.request_type==='choose_card')value=r.eligible_card_ids[0]
      else if(r.request_type==='choose_players')value=r.allowed_player_ids.slice(0,r.min_count)
      else value=r.allowed_player_ids[0]
      await page.evaluate(({r,value})=>(window as any).__auditSocket.send(JSON.stringify({type:'SUBMIT_DECISION',version:2,decision:{request_id:r.request_id,value}})),{r,value})
    }
    const stage=await page.evaluate(()=>document.querySelector('.event-stage')?.getAttribute('data-event-id')??'')
    if(stage && stage!==lastStage && captures<28){lastStage=stage;await page.screenshot({path:'../docs/t18a8/'+mode+'-'+String(++captures).padStart(2,'0')+'.png'})}
    if(Date.now()-lastProgress>30000){lastProgress=Date.now();fs.writeFileSync('../docs/t18a8/'+mode+'-progress.json',JSON.stringify({elapsedMs:Date.now()-started,turn,events:events.length,hud},null,2))}
    await page.waitForTimeout(200)
  }
  const observations=await page.evaluate(()=>{const w=window as any;clearInterval(w.__observeTimer);return w.__observations})
  fs.writeFileSync('../docs/t18a8/'+mode+'-observations.json',JSON.stringify({elapsedMs:Date.now()-started,events,observations,requests:requests.map(r=>({id:r.request_id,type:r.request_type,player:r.player_id})),errors},null,2))
  const turns=events.filter(e=>e.kind==='TurnStartedEvent').map(e=>e.turn_number)
  expect(Math.max(...turns)).toBeGreaterThanOrEqual(mode === 'military-eight' ? 17 : 11)
  expect(errors).toEqual([])
  expect(events.some(e=>e.kind==='AIThinkingEvent')).toBe(true)
  expect(events.some(e=>e.kind==='CardUsedEvent')).toBe(true)
  expect(new Set(events.filter(e=>e.kind==='AIThinkingEvent').map(e=>e.source_id)).size).toBeGreaterThanOrEqual(2)
  expect(observations.some((row:any)=>row.seats.some((seat:any)=>seat.classes.includes('thinking')))).toBe(true)
  expect(observations.some((row:any)=>row.card)).toBe(true)
  await page.screenshot({path:'../docs/t18a8/'+mode+'-final.png'})
})

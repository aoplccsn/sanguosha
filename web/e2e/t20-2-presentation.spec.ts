import {test,expect} from '@playwright/test'
for(const width of [390,1440]) test(`T20.2 Chinese battle, suit inks, status rings and Guo Jia ${width}`,async({page,request})=>{
 await page.setViewportSize({width,height:1000})
 await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
 await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
 const catalog=await (await request.get('/api/catalog/generals')).json()
 await page.goto('/e2e/fixtures/t15.html?real')
 await page.evaluate(catalog=>{
  const w=window as any,s=w.__t15State
  s.generals=Object.fromEntries(catalog.map((g:any)=>[g.id,g]));s.pendingRequest=null
  s.projection.players.forEach((p:any,i:number)=>{p.character_id=i===0?'mobile_god_guojia':'zhaoyun';p.character_name=i===0?'神郭嘉':'赵云';p.skill_labels=i===0?['慧识','天翊','辉逝']:['龙胆'];p.chained=i===1})
  s.projection.waiting={key:'waiting',player_id:'p3',responding:true,thinking:false,remaining_ms:60000,required_definition_id:'basic.dodge',response_to:'basic.slash'}
  s.projection.hand=['♥','♦','♠','♣'].map((suit,i)=>({...s.projection.hand[0],suit,card_id:'suit-'+i,rank:'7'}))
  w.__t15Render()
 },catalog)
 const portrait=page.locator('.player-self video');await expect(portrait).toHaveAttribute('src',/mobile_god_guojia.panel.mp4/)
 await expect.poll(()=>portrait.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.2)
 await expect(page.locator('.hand .suit-red')).toHaveCount(2);await expect(page.locator('.hand .suit-black')).toHaveCount(2)
 expect(await page.locator('.hand .suit-red').first().evaluate(e=>getComputedStyle(e).color)).toBe('rgb(160, 50, 43)')
 expect(await page.locator('.hand .suit-black').first().evaluate(e=>getComputedStyle(e).color)).toBe('rgb(52, 56, 58)')
 const chain=page.locator('[data-player-id="p2"]'),waiting=page.locator('[data-player-id="p3"]')
 expect(await chain.evaluate(e=>getComputedStyle(e).outlineColor)).toBe('rgb(100, 133, 128)')
 expect(await waiting.evaluate(e=>getComputedStyle(e,'::after').borderRightColor)).toBe('rgb(222, 180, 109)')
 await page.getByRole('button',{name:'查看神郭嘉详情',exact:true}).click()
 const detail=page.locator('.game-general-detail');await expect(detail).toHaveAttribute('data-portrait-mode','dynamic')
 const video=detail.locator('video');await expect(video).toHaveAttribute('src',/mobile_god_guojia.mp4/)
 await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.2)
 await page.screenshot({path:`../docs/t20_2/guojia-detail-${width}.png`})
 await detail.locator('.modal-close').click()
 await page.evaluate(()=>{
  const w=window as any,s=w.__t15State
  s.pendingRequest={request_id:'response-new',player_id:'p1',request_type:'respond_with_card',prompt:'Respond with a card or pass',required_definition_id:'basic.slash',eligible_card_ids:['suit-0'],choices:[],allowed_player_ids:[],min_count:0,max_count:1,allow_pass:true,remaining_ms:60000}
  s.projection.combat={root_id:'aoe',source_id:'p2',definition_id:'trick.savage_assault',target_ids:['p1'],resolved_target_ids:[],current_target_id:'p1',nullification_count:0,cancelled:false}
  w.__t15Render()
 })
 await expect(page.locator('.decision-prompt')).toContainText('请打出一张【杀】响应【南蛮入侵】')
 expect(await page.locator('.decision-prompt').innerText()).not.toMatch(/response|target|confirm|cancel|discard|choose|skill_id|request_type|ViewAs/)
 await page.screenshot({path:`../docs/t20_2/battle-${width}.png`})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 // Native playback failure must still display the extracted poster.
 await page.route('**/mobile_god_guojia*.mp4',r=>r.abort())
 await page.reload();await page.evaluate(catalog=>{const w=window as any,s=w.__t15State;s.generals=Object.fromEntries(catalog.map((g:any)=>[g.id,g]));Object.assign(s.projection.players[0],{character_id:'mobile_god_guojia',character_name:'神郭嘉',skill_labels:['慧识']});w.__t15Render()},catalog)
 const fallback=page.locator('.player-self .dynamic-portrait img')
 await expect.poll(()=>fallback.evaluate((v:HTMLImageElement)=>v.complete&&v.naturalWidth>0)).toBe(true)
})

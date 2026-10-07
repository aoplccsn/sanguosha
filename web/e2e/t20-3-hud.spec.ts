import {test,expect,type Page} from '@playwright/test'

async function fixture(page:Page,count:number) {
 await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
 await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(id,value){window.__decision={id,value}}}}}`}))
 await page.goto('/e2e/fixtures/t15.html?real')
 await prepare(page,count)
}
async function prepare(page:Page,count:number) {
 const catalog=await (await page.request.get('/api/catalog/generals')).json()
 await page.evaluate(({catalog,count})=>{
  const w=window as any,s=w.__t15State
  s.roomCode='T203';s.generals=Object.fromEntries(catalog.map((g:any)=>[g.id,g]))
  const sample=s.projection.players[1]
  s.projection.players=Array.from({length:count},(_,i)=>({...sample,player_id:'p'+(i+1),name:'玩家'+(i+1),character_id:i===0?'sunquan':'zhaoyun',character_name:i===0?'孙权':'赵云',identity_label:i===0?'主公':'未知',skill_labels:i===0?['制衡','救援']:['龙胆'],active:i===0}))
  s.projection.hand=Array.from({length:26},(_,i)=>({...s.projection.hand[0],card_id:'hand-'+i}))
  s.projection.players[0].equipment=[{...s.projection.hand[0],card_id:'eq',name:'诸葛连弩',definition_id:'equipment.weapon.crossbow',equipment_slot:'weapon'}]
  s.pendingRequest={request_id:'cost',player_id:'p1',request_type:'choose_cards',prompt:'【制衡】选择手牌或装备',choices:[],eligible_card_ids:['eq',...s.projection.hand.map((c:any)=>c.card_id)],allowed_player_ids:[],min_count:1,max_count:27,remaining_ms:60000}
  s.projection.waiting={key:'response',player_id:'p2',responding:true,thinking:false,remaining_ms:60000,required_definition_id:'basic.dodge',response_to:'basic.slash'}
  w.__t15Render()
 },{catalog,count})
 await expect(page.locator('.player-panel')).toHaveCount(count)
}

for(const [width,height,count] of [[1440,1000,5],[844,390,5],[932,430,8],[844,390,2],[852,393,4],[915,412,8]]) {
 test(`T20.3 HUD ${width}x${height} ${count} seats`,async({page})=>{
  await page.setViewportSize({width,height});await fixture(page,count)
  await expect(page.getByText('请横屏游玩')).not.toBeVisible()
  const areas=await page.locator('.skill-area,.equipment-area,.hand,.player-self').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}}))
  expect(areas.every(r=>r.x>=0&&r.right<=width&&r.y>=0&&r.bottom<=height)).toBe(true)
  const skills=await page.locator('.skill-area').boundingBox(),hand=await page.locator('.hand').boundingBox()
  expect(skills!.x+skills!.width).toBeLessThanOrEqual(hand!.x)
  const button=page.getByRole('button',{name:'查看制衡技能说明'}).first()
  await button.click();await expect(page.getByRole('tooltip')).toContainText('制衡');await page.mouse.move(0,0);await button.blur()
  const eq=page.getByRole('button',{name:'装备 诸葛连弩'})
  await eq.click();await expect(eq).toHaveAttribute('aria-pressed','true');await expect(eq).toHaveClass(/selected/)
  await eq.click();await expect(eq).toHaveAttribute('aria-pressed','false')
  await eq.click();await page.getByRole('button',{name:'确定',exact:true}).click()
  expect(await page.evaluate(()=>(window as any).__decision.value)).toEqual(['eq'])
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.screenshot({path:`../docs/t20_3/hud-${count}-${width}.png`})
 })
}

test('T20.3 identity notes survive refresh and remain browser-private',async({page,browser})=>{
 await page.setViewportSize({width:1440,height:1000});await fixture(page,5)
 const note=page.locator('[data-player-id="p2"] .identity-note-trigger')
 for(const [label,mark] of [['忠臣','忠？'],['反贼','反？'],['内奸','内？']]) { await note.click();await page.getByRole('button',{name:label,exact:true}).click();await expect(note).toHaveText(mark) }
 await page.reload();await prepare(page,5);await expect(note).toHaveText('内？')
 const context=await browser.newContext();const other=await context.newPage()
 await fixture(other,5);await expect(other.locator('[data-player-id="p2"] .identity-note-trigger')).toHaveText('标记')
 await context.close()
 await page.evaluate(()=>{const w=window as any;Object.assign(w.__t15State.projection.players[1],{alive:false,identity_label:'忠臣'});w.__t15Render()})
 await expect(note).toHaveCount(0)
})

test('T20.3 portrait gate keeps selection and the same portrait across rotation',async({page})=>{
 await page.setViewportSize({width:844,height:390});await fixture(page,5)
 await page.getByRole('button',{name:'装备 诸葛连弩'}).click()
 await page.evaluate(()=>{(window as any).__portrait=document.querySelector('.player-self .dynamic-portrait')})
 await page.setViewportSize({width:390,height:844});await expect(page.getByText('请横屏游玩')).toBeVisible()
 await page.setViewportSize({width:844,height:390});await expect(page.getByText('请横屏游玩')).not.toBeVisible()
 await expect(page.getByRole('button',{name:'装备 诸葛连弩'})).toHaveAttribute('aria-pressed','true')
 expect(await page.evaluate(()=>(window as any).__portrait===document.querySelector('.player-self .dynamic-portrait'))).toBe(true)
})

for(const [width,height] of [[1440,1000],[844,390]]) test(`T20.3 local dynamic and fallback viewport ${width}`,async({page})=>{
 await page.setViewportSize({width,height});await fixture(page,5)
 await page.evaluate(()=>{const w=window as any;Object.assign(w.__t15State.projection.players[0],{character_id:'mobile_god_guojia',character_name:'神郭嘉',skill_labels:['慧识','天翊','辉逝']});w.__t15Render()})
 const panel=page.locator('.player-self'),video=panel.locator('video')
 await expect(video).toHaveCount(1);await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.2)
 const rects=await panel.locator('.dynamic-portrait > img,.dynamic-portrait > video').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return [r.width,r.height,getComputedStyle(e).objectFit]}))
 expect(rects[0]).toEqual(rects[1])
 await page.screenshot({path:`../docs/t20_3/local-dynamic-${width}.png`})
 await video.dispatchEvent('error');await expect(video).toHaveCount(0)
 await expect(panel.locator('.dynamic-portrait > img')).toBeVisible()
 await page.screenshot({path:`../docs/t20_3/local-fallback-${width}.png`})
})

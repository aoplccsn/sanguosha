import {test,expect,type Page} from '@playwright/test'
import {fileURLToPath} from 'node:url'
const shot=(name:string)=>fileURLToPath(new URL('../../docs/t18a10/screenshots/'+name+'.png',import.meta.url))
async function enter(page:Page,r:any){
 await page.addInitScript(r=>localStorage.setItem('sanguosha.web.session.v1',JSON.stringify(r)),r)
 await page.goto('/');await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(page.locator('.game-page')).toBeVisible()
}
async function fixture(request:any,caseName:string,mode='military-eight',general='mountain_zuoci'){
 const res=await request.post('/audit/new/'+caseName+'?mode='+mode+'&general='+general);expect(res.ok()).toBeTruthy();return res.json()
}
for(const mode of ['military-five','military-eight'])for(const size of [{width:1440,height:1000},{width:390,height:844},{width:430,height:932}]){
 test('seat order and nonoverlap '+mode+' '+size.width,async({page,request})=>{
  await page.setViewportSize(size);const records=await fixture(request,'layout',mode);await enter(page,records[3])
  const expected=[...records.slice(4),...records.slice(0,3)].map((r:any)=>r.seatId)
  expect(await page.locator('.game-board > .player-panel').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('data-player-id')))).toEqual(expected)
  const boxes=await page.locator('.game-board > .player-panel').evaluateAll(nodes=>nodes.map(n=>{const b=n.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height}}))
  for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];expect(Math.min(a.x+a.w,b.x+b.w)<=Math.max(a.x,b.x)+1||Math.min(a.y+a.h,b.y+b.h)<=Math.max(a.y,b.y)+1).toBeTruthy()}
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await expect(page.locator('.chain-mark')).toHaveCount(2);await expect(page.locator('.equipment-token').filter({hasText:'绝影 +1'})).toBeVisible();await expect(page.locator('.equipment-token').filter({hasText:'赤兔 -1'})).toBeVisible()
  await page.screenshot({path:shot(mode+'-'+size.width),fullPage:true})
 })
}
test('real acquired Qixi cancellation then normal Peach',async({page,request})=>{
 const records=await fixture(request,'qixi');await enter(page,records[0]);const skill=page.getByRole('button',{name:'奇袭',exact:true}).first();await skill.click()
 const slash=page.locator('.hand .hand-card').filter({hasText:'杀'}).first();await slash.click();await slash.click();await slash.click()
 await page.getByRole('button',{name:'取消选中'}).click();const peach=page.locator('.hand .hand-card').filter({hasText:'桃'});await expect(peach).toHaveAttribute('aria-disabled','false');await peach.click()
 await page.screenshot({path:shot('qixi-cancel-normal')});await page.getByRole('button',{name:'确定',exact:true}).click();await expect(page.locator('.player-self .hp-row')).toHaveAttribute('aria-label',/3 \/ 4/)
})
for(const caseName of ['fire','fire_none'])test('AI reveal and suit flow '+caseName,async({page,request})=>{
 const records=await fixture(request,caseName);await enter(page,records[0]);await request.post('/audit/advance/'+records[0].roomCode)
 await expect(page.locator('.public-resolution-card')).toBeVisible();await expect(page.locator('.public-resolution-card')).toContainText('桃')
 await page.screenshot({path:shot(caseName+'-ai-reveal')})
 if(caseName==='fire_none'){await expect(page.locator('.event-stage')).toContainText('没有可弃置',{timeout:15000});await page.screenshot({path:shot('fire-no-suit')});await expect(page.locator('.event-stage')).toContainText('未造成伤害',{timeout:15000})}
 else {await page.reload();await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(page.locator('.public-resolution-card')).toContainText('桃');await expect(page.locator('.decision-prompt')).toContainText('♥')}
})
test('dismantlement hides hand until public discard',async({page,request})=>{
 const records=await fixture(request,'dismantle');await enter(page,records[0]);const panel=page.getByRole('dialog',{name:'过河拆桥'});await expect(panel.getByRole('button',{name:'暗置手牌 1',exact:true})).toBeVisible();await panel.getByRole('button',{name:'暗置手牌 1',exact:true}).click();await panel.getByRole('button',{name:'确认',exact:true}).click();await expect(page.locator('.public-resolution-card')).toBeVisible();await page.screenshot({path:shot('dismantle-public-hand')})
})
test('three discarded cards share one public presentation',async({page,request})=>{
 const records=await fixture(request,'layout');await enter(page,records[0]);await request.post('/audit/discard/'+records[0].roomCode);await expect(page.locator('.public-resolution-card')).toHaveCount(3);await page.screenshot({path:shot('discard-three')})
})
for(const caseName of ['savage','archery','counter_single','counter_group','harvest','takeover'])test('interaction '+caseName,async({page,request})=>{
 await page.setViewportSize({width:430,height:932});const records=await fixture(request,caseName);await enter(page,records[0])
 if(caseName==='counter_single')await expect(page.getByRole('button',{name:'本轮不再询问'})).toHaveCount(0)
 if(['counter_group','savage','archery'].includes(caseName)){await expect(page.getByRole('button',{name:'本轮不再询问'})).toBeVisible();await expect(page.locator('.decision-prompt')).toContainText('赵云');await expect(page.locator('.aoe-current')).toHaveAttribute('data-player-id','p2')}
 if(caseName==='harvest')await expect(page.getByRole('dialog',{name:'五谷丰登'})).toBeVisible()
 if(caseName==='takeover')await expect(page.getByText('AI 托管',{exact:true})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();await page.screenshot({path:shot(caseName),fullPage:true})
})
test('103 GeneralDetail descriptions and two missing generals',async({page,request})=>{
 const catalog=await (await request.get('/api/catalog/generals')).json();expect(catalog).toHaveLength(103)
 const records=await fixture(request,'layout');await enter(page,records[0])
 for(const g of catalog){
  for(const skill of g.skills){expect(skill.name).toBeTruthy();expect(skill.description.length).toBeGreaterThan(9);expect(skill.description).not.toMatch(/TODO|placeholder|规则摘要|待补/i)}
  await request.post('/audit/general/'+records[0].roomCode+'/'+g.id);const button=page.locator('.player-self .portrait-button');await expect(button).toHaveAttribute('aria-label','查看'+g.name+'详情');await button.click();const panel=page.locator('.game-general-detail');await expect(panel).toBeVisible();await expect(panel.locator('h3')).toHaveCount(g.skills.length)
  for(const skill of g.skills)await expect(panel).toContainText(skill.description)
  if(['fire_wolong','fire_yuan_shao'].includes(g.id))await page.screenshot({path:shot(g.id)})
  await panel.locator('.modal-close').click()
 }
})

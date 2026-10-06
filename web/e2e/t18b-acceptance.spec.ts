import {test,expect,type Page} from '@playwright/test'
import {fileURLToPath} from 'node:url'
const out=(name:string)=>fileURLToPath(new URL('../../docs/t18b/browser/'+name,import.meta.url))
async function enter(page:Page,request:any,kind:string,general?:string){
 const data=await (await request.post('/audit/new/'+kind+(general?'?general='+general:''))).json()
 await page.goto('/');await page.evaluate(r=>localStorage.setItem('sanguosha.web.session.v1',JSON.stringify(r)),data[0]);await page.reload()
 await page.getByRole('button',{name:'继续对局',exact:true}).click()
 return data
}
async function images(page:Page,selector:string){await expect.poll(()=>page.locator(selector).evaluateAll(nodes=>nodes.length>0&&nodes.every(n=>(n as HTMLImageElement).complete&&(n as HTMLImageElement).naturalWidth>0))).toBeTruthy()}
async function noOverflow(page:Page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy()}

test('103 production portraits, 43 card arts and all 13 dynamic sets use production HTTP',async({request})=>{
 const catalog=await (await request.get('/api/catalog/generals')).json();expect(catalog).toHaveLength(103);expect(catalog.every((g:any)=>g.implemented&&g.playable)).toBeTruthy()
 const manifest=await (await request.get('/assets/manifest.json')).json()
 const cards=[...new Set(Object.entries(manifest).filter(([key])=>/^(basic|trick|delayed|equipment)\./.test(key)).map(([,v])=>'/assets/'+v))];expect(cards).toHaveLength(43)
 for(const path of [...catalog.map((g:any)=>g.portrait),...cards]){const r=await request.get(String(path));expect(r.status(),String(path)).toBe(200);expect(r.headers()['content-type']).toMatch(/^image\/(png|webp)/);expect((await r.body()).length).toBeGreaterThan(100)}
 const idle=await (await request.get('/assets/idle_portraits.json')).json();expect(Object.keys(idle)).toHaveLength(13)
 for(const item of Object.values(idle) as any[])for(const path of new Set([item.video,item.panelVideo].filter(Boolean))){const r=await request.get(path);expect(r.status(),path).toBe(200);expect(r.headers()['content-type']).toMatch(/^video\/mp4/);expect((await r.body()).length).toBeGreaterThan(10000);const range=await request.get(path,{headers:{Range:'bytes=0-1023'}});expect(range.status()).toBe(206);expect((await range.body()).length).toBe(1024)}
})

for(const size of [{width:390,height:844},{width:430,height:932}]){
 test('all 23 new ordinary details on mobile '+size.width,async({browser,request})=>{
  const generals=(await (await request.get('/api/catalog/generals')).json()).filter((g:any)=>g.pack==='yj2012'||g.pack==='yj2013');expect(generals).toHaveLength(23)
  for(const g of generals){const context=await browser.newContext({viewport:size});const page=await context.newPage();try{
   await enter(page,request,'portrait',g.id);await expect(page.locator('.game-page')).toBeVisible();await images(page,'[data-player-id="p1"] .portrait-button img')
   await page.getByRole('button',{name:'查看'+g.name+'详情',exact:true}).click();const detail=page.locator('.game-general-detail');await expect(detail).toBeVisible();await images(page,'.game-general-detail img')
   for(const skill of g.skills)await expect(detail).toContainText(skill.name)
   await noOverflow(page);await page.screenshot({path:out('detail-'+g.id+'-'+size.width+'.png')})
  }finally{await context.close()}}
 })
 test('four god videos, resize and reduced-motion fallbacks '+size.width,async({browser,request})=>{
  const generals=(await (await request.get('/api/catalog/generals')).json()).filter((g:any)=>g.pack==='new_gods');expect(generals).toHaveLength(4)
  for(const g of generals){const context=await browser.newContext({viewport:size});const page=await context.newPage();try{
   await enter(page,request,'portrait',g.id);await expect(page.locator('.game-page')).toBeVisible()
   const panel=page.locator('[data-player-id="p1"] video');await expect(panel).toHaveCount(1);await expect.poll(()=>panel.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.2)
   expect(await panel.evaluate((v:HTMLVideoElement)=>v.loop&&v.muted&&!v.error&&v.poster===v.parentElement!.querySelector('img')!.src)).toBeTruthy()
   await page.screenshot({path:out('panel-'+g.id+'-'+size.width+'.png')})
   await page.getByRole('button',{name:'查看'+g.name+'详情',exact:true}).click();const detail=page.locator('.game-general-detail');await expect(detail).toBeVisible();const video=detail.locator('video');await expect(video).toHaveCount(1)
   await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.2);expect(await video.getAttribute('src')).toContain(g.id+'.mp4');await video.evaluate((v:HTMLVideoElement)=>{v.currentTime=v.duration-.1});await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeLessThan(1);await noOverflow(page)
   await page.screenshot({path:out('dynamic-detail-'+g.id+'-'+size.width+'.png')})
   await page.setViewportSize({width:size.width===390?430:390,height:size.height});await noOverflow(page)
   await page.emulateMedia({reducedMotion:'reduce'});await expect(detail.locator('video')).toHaveCount(0);await images(page,'.game-general-detail img');await page.screenshot({path:out('fallback-'+g.id+'-'+size.width+'.png')})
  }finally{await context.close()}}
 })
 test('Zongxuan private choice, ordered submission and reconnect '+size.width,async({page,request})=>{
  await page.setViewportSize(size);await enter(page,request,'zongxuan');const panel=page.getByRole('dialog',{name:'纵玄'});await expect(panel).toBeVisible();await images(page,'.temporary-cards img');await noOverflow(page)
  const cards=panel.locator('.hand-card');await expect(cards).toHaveCount(3)
  await cards.nth(2).click();await cards.nth(0).click();await expect(panel.getByRole('button',{name:'确定',exact:true})).toBeEnabled();await page.reload();await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(panel).toBeVisible();await expect(panel.locator('.hand-card.selected')).toHaveCount(2);await expect(panel.getByRole('button',{name:'确定',exact:true})).toBeEnabled()
  await page.screenshot({path:out('zongxuan-reconnect-'+size.width+'.png')});await panel.getByRole('button',{name:'确定',exact:true}).click();await expect(panel).toHaveCount(0)
 })
 test('Poxi authorized hand and Duorui equipment choices '+size.width,async({browser,request})=>{
  for(const kind of ['poxi','duorui']){const context=await browser.newContext({viewport:size});const page=await context.newPage();try{
   await enter(page,request,kind);await expect(page.locator('.game-page')).toBeVisible();await noOverflow(page)
   if(kind==='poxi'){const panel=page.getByRole('dialog',{name:'魄袭'});await expect(panel).toBeVisible();await expect(panel.locator('.hand-card')).toHaveCount(4);await images(page,'.temporary-cards img')}
   else await expect(page.getByRole('button',{name:'武器栏',exact:true})).toBeVisible()
   await page.screenshot({path:out(kind+'-'+size.width+'.png')});await page.reload();await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(page.locator('.game-page')).toBeVisible();await noOverflow(page)
  }finally{await context.close()}}
 })
 test('new god draft selection and native dynamic detail '+size.width,async({page,request})=>{
  await page.setViewportSize(size);await enter(page,request,'draft','shadow_god_liubei');await expect(page.locator('.pregame-page')).toBeVisible();await expect(page.locator('.general-card')).toHaveCount(10)
  await page.locator('.general-card').filter({hasText:'神刘备'}).click();await expect(page.locator('.general-detail')).toContainText('龙怒');await page.locator('.general-detail').scrollIntoViewIfNeeded();const video=page.locator('.general-detail video');await expect(video).toHaveCount(1);await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.2)
  await noOverflow(page);await page.screenshot({path:out('draft-god-'+size.width+'.png')});await page.getByRole('button',{name:'确认武将',exact:true}).click();await expect(page.locator('.game-page')).toBeVisible()
 })
}

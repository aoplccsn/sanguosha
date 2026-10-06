import {test,expect} from '@playwright/test'
const ids=['mobile_god_lusu','mobile_god_taishici','mobile_god_sunce','mountain_god_simayi','mobile_god_guojia','mobile_god_xunyu']
for(const width of [390,1440])test('T19 six portraits, descriptions and reconnect '+width,async({browser,request})=>{
 const catalog=await (await request.get('/api/catalog/generals')).json();expect(catalog).toHaveLength(108)
 for(const id of ids){
  const g=catalog.find((g:any)=>g.id===id);expect(g).toBeTruthy()
  const context=await browser.newContext({viewport:{width,height:1000}});const page=await context.newPage()
  try{
   const r=await (await request.post('/audit/new/portrait?general='+id)).json()
   await page.goto('/');await page.evaluate(r=>localStorage.setItem('sanguosha.web.session.v1',JSON.stringify(r)),r[0]);await page.reload()
   await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(page.locator('.game-page')).toBeVisible()
   await page.getByRole('button',{name:'查看'+g.name+'详情',exact:true}).click();const detail=page.locator('.game-general-detail');await expect(detail).toBeVisible()
   for(const skill of g.skills)await expect(detail).toContainText(skill.name)
   const img=detail.locator('img').first();expect(await img.evaluate((v:HTMLImageElement)=>v.complete&&v.naturalWidth>0)).toBeTruthy()
   if(id!=='mobile_god_guojia'){const video=detail.locator('video');await expect(video).toHaveCount(1);await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.2)}
   await page.screenshot({path:'../docs/t19/detail-'+id+'-'+width+'.png'})
   await page.reload();await page.getByRole('button',{name:'继续对局',exact:true}).click();await expect(page.locator('.game-page')).toBeVisible()
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  }finally{await context.close()}
 }
})

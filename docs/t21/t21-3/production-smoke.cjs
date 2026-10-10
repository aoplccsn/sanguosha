const { chromium } = require('../../../web/node_modules/playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
;(async () => {
 const browser = await chromium.launch()
 const origin = process.env.BASE_URL || 'http://127.0.0.1:8023'
 const problems = []
 try {
  for (const [mode, count] of [['military-five',5],['military-eight',8]]) {
   const a = await browser.newContext({viewport:{width:1440,height:900}})
   const b = await browser.newContext({viewport:{width:1440,height:900}})
   const host = await a.newPage(), guest = await b.newPage()
   for (const page of [host,guest]) {
    page.on('pageerror',e=>problems.push(String(e)))
    page.on('console',m=>{if(m.type()==='error') problems.push(m.text())})
    page.on('response',r=>{if(r.status()>=400) problems.push(r.status()+' '+r.url())})
   }
   await host.goto(origin+'/?seed=21')
   await host.getByLabel('玩家昵称').fill('生产验收房主')
   await host.getByLabel('对局模式').selectOption(mode)
   await host.locator('.home-hero video').waitFor({state:'visible'})
   await host.waitForFunction(()=>document.querySelector('.home-hero video')?.readyState>=2)
   if(count===5) await host.screenshot({path:__dirname+'/production-home.png'})
   await host.getByRole('button',{name:'创建多人房间',exact:true}).click()
   await host.locator('.room-code-box strong').waitFor()
   const code = (await host.locator('.room-code-box strong').textContent()).trim()
   await guest.goto(origin+'/room/'+code)
   await guest.getByLabel('玩家昵称').fill('生产验收来宾')
   await guest.getByRole('button',{name:'加入房间',exact:true}).click()
   await guest.getByRole('button',{name:'准备',exact:true}).click()
   await host.getByRole('button',{name:'开始游戏',exact:true}).click()
   for(const page of [host,guest]) {
    await page.locator('.general-card').first().click()
    await page.getByRole('button',{name:'确认武将',exact:true}).click()
   }
   await host.locator('.game-page').waitFor()
   await guest.locator('.game-page').waitFor()
   assert.equal(await host.locator('.player-panel').count(),count)
   await host.screenshot({path:__dirname+'/production-table-'+count+'.png'})
   await guest.reload()
   await guest.getByRole('button',{name:'继续对局',exact:true}).click()
   await guest.locator('.game-page').waitFor()
   assert.equal(await guest.locator('.player-panel').count(),count)
   assert.ok((await guest.locator('.player-self').textContent()).includes('生产验收来宾'))
   await guest.evaluate(()=>localStorage.setItem('sanguosha.vfx.quality.v1','low'))
   await guest.reload()
   await guest.getByRole('button',{name:'继续对局',exact:true}).click()
   await guest.locator('.game-page').waitFor()
   assert.equal(await guest.locator('.player-panel video').count(),0)
   assert.ok(await guest.locator('.player-panel img').evaluateAll(imgs=>imgs.every(i=>i.complete&&i.naturalWidth>0)))
   for(const page of [host,guest]) await page.getByRole('button',{name:'离开牌局',exact:true}).click()
   await a.close(); await b.close()
   console.log('PASS production '+count+' seats: create/join/draft/reconnect/static fallback')
  }
  assert.deepEqual(problems,[])
  console.log('PASS no asset 404, console or runtime errors')
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)})

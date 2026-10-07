import {test,expect,type Page} from '@playwright/test'

async function realScene(page:Page) {
 await page.goto('/?seed=6');await page.getByRole('button',{name:'创建多人房间'}).click()
 const code=(await page.locator('.room-code-box strong').innerText()).trim()
 const response=await page.request.post(`/api/t203/scene/${code}`);expect(response.ok()).toBe(true)
 const cards=await response.json()
 await expect(page.locator('.player-self')).toHaveAttribute('data-character-id','sunquan')
 await expect(page.locator('.player-self .player-heading')).toContainText('忠臣')
 return {code,...cards}
}
for(const recast of [false,true]) test(`T20.3 real three-survivor loyalist ${recast?'recast':'chain'}`,async({page})=>{
 const scene=await realScene(page)
 await page.locator(`[data-card-id="${scene.chain}"]`).click({position:{x:4,y:25}})
 await expect(page.locator('.player-panel.selectable')).toHaveCount(3)
 await expect(page.getByRole('button',{name:'使用',exact:true})).toBeDisabled()
 if(recast) await page.getByRole('button',{name:'重铸',exact:true}).click()
 else {
  await page.locator('[data-player-id="p1"] .portrait-button').click()
  await page.locator('[data-player-id="p3"] .portrait-button').click()
  await page.getByRole('button',{name:'使用',exact:true}).click()
 }
 await expect.poll(async()=>await (await page.request.post(`/api/t203/state/${scene.code}`)).json()).toMatchObject({chained:recast?[]:['p1','p3'],discard:expect.arrayContaining([scene.chain])})
})

test('T20.3 real equipment payload and rotation preserve room and WebSocket',async({page})=>{
 await page.setViewportSize({width:844,height:390})
 let sockets=0;page.on('websocket',()=>sockets++)
 const scene=await realScene(page)
 const socketsBefore=sockets
 await page.getByRole('button',{name:'制衡',exact:true}).first().click();await page.getByRole('button',{name:'确定',exact:true}).click()
 const equipment=page.getByRole('button',{name:'装备 诸葛连弩'})
 await equipment.click();await expect(equipment).toHaveAttribute('aria-pressed','true')
 await equipment.click();await expect(equipment).toHaveAttribute('aria-pressed','false')
 await equipment.click()
 await page.setViewportSize({width:390,height:844});await expect(page.getByText('请横屏游玩')).toBeVisible()
 await page.setViewportSize({width:932,height:430});await expect(equipment).toHaveAttribute('aria-pressed','true')
 expect(sockets).toBe(socketsBefore)
 await page.getByRole('button',{name:'确定',exact:true}).click()
 await expect.poll(async()=>await (await page.request.post(`/api/t203/state/${scene.code}`)).json()).toMatchObject({discard:expect.arrayContaining([scene.equipment])})
})

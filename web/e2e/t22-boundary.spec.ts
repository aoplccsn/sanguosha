import { test, expect } from '@playwright/test'
const ids = ['xu_sheng','ju_shou','zhong_hui','li_ru','ling_tong','zhu_ran','fa_zheng','cao_xiu','wei_yan','zhang_fei']
for (const [index,key] of ids.entries()) {
 test('T22 select portrait and reconnect boundary_'+key, async ({page,request})=>{
  const id='boundary_'+key
  const catalog=await (await request.get('/api/catalog/generals')).json()
  const general=catalog.find((g:{id:string})=>g.id===id)
  expect(general).toBeTruthy()
  const image=await request.get(general.portrait)
  expect(image.ok()).toBeTruthy()
  await page.goto('/?seed=22')
  await page.getByRole('combobox',{name:'对局模式'}).selectOption(index%2 ? 'military-eight':'military-five')
  await page.getByText('更多工具',{exact:true}).click()
  await page.getByRole('button',{name:'测试模式',exact:true}).click()
  await page.getByLabel('测试权限码').fill('t22-local-smoke')
  await page.getByRole('button',{name:'验证',exact:true}).click()
  await page.getByRole('button',{name:'创建测试房',exact:true}).click()
  await page.getByLabel('搜索武将或技能').fill(general.name)
  await page.getByRole('button',{name:new RegExp(general.name)}).first().click()
  await page.getByRole('button',{name:'确认武将',exact:true}).click()
  await expect(page.locator('.game-page')).toBeVisible()
  await expect(page.locator('.player-panel.player-self')).toHaveAttribute('data-character-id',id)
  await expect(page.locator('.player-panel')).toHaveCount(index%2 ? 8:5)
  await page.reload()
  await page.getByText('更多工具',{exact:true}).click()
  await page.getByRole('button',{name:'继续对局',exact:true}).click()
  await expect(page.locator('.player-panel.player-self')).toHaveAttribute('data-character-id',id)
  if(index===1 || index===9) await page.screenshot({path:'../docs/t22/web-'+key+'.png',fullPage:true})
 })
}

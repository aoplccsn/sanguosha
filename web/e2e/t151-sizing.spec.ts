import { test, expect } from '@playwright/test'
import fs from 'node:fs'
test('measure panel and detail layout at DPR one and two',async({browser})=>{
 const data:any[]=[]
 for(const dpr of [1,2])for(const width of [1440,1000,720,700,390]){
  const context=await browser.newContext({viewport:{width,height:950},deviceScaleFactor:dpr})
  const page=await context.newPage()
  await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
  await page.goto('/e2e/fixtures/t15.html?real')
  await expect(page.locator('.player-panel')).toHaveCount(5)
  const panels=await page.locator('.portrait-button').evaluateAll(ns=>ns.map(n=>{const r=n.querySelector('.dynamic-portrait')!.getBoundingClientRect();return {width:r.width,height:r.height}}))
  await page.locator('.player-self .portrait-button').click()
  await expect(page.locator('.game-general-detail')).toBeVisible()
  const detail=await page.locator('.game-general-detail .dynamic-portrait').evaluate(n=>{const r=n.getBoundingClientRect();return {width:r.width,height:r.height}})
  data.push({viewport:width,dpr,panels,detail})
  await context.close()
 }
 fs.writeFileSync('../docs/t15_1/display-sizes.json',JSON.stringify(data,null,2))
})

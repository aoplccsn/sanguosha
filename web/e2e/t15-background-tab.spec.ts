import fs from 'node:fs'
import { expect, test } from '@playwright/test'

test('actual background tab pauses final portraits and restores only eligible videos',async({page,context})=>{
  test.skip(process.env.T15_NATIVE_WINDOW !== '1', 'Requires a desktop exposing native tab/window visibility; this automated desktop keeps document.hidden=false even after minimize. Lifecycle behavior is covered by controlled browser events in t15-final-idle.spec.ts.')
  await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
  await page.route('**/src/state/GameContext.tsx',route=>route.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
  await page.goto('/e2e/fixtures/t15.html?real')
  await expect(page.locator('video')).toHaveCount(5)
  await expect.poll(()=>page.locator('video').evaluateAll(nodes=>nodes.every(n=>!(n as HTMLVideoElement).paused&&(n as HTMLVideoElement).readyState>=2))).toBe(true)
  // A web-opened tab shares the actual browser window. context.newPage() may
  // create another visible window, which does not hide the original document.
  const cdp=await context.newCDPSession(page)
  await cdp.send('Emulation.setFocusEmulationEnabled',{enabled:false})
  const [foreground]=await Promise.all([page.waitForEvent('popup'),page.evaluate(()=>window.open('about:blank','_blank'))])
  await foreground.bringToFront()
  const nativeWindow=await cdp.send('Browser.getWindowForTarget')
  let mode='background-tab'
  if(!await page.evaluate(()=>document.hidden)){
    mode='native-window-minimize'
    await cdp.send('Browser.setWindowBounds',{windowId:nativeWindow.windowId,bounds:{windowState:'minimized'}})
  }
  await expect.poll(()=>page.evaluate(()=>document.hidden)).toBe(true)
  fs.writeFileSync('../docs/t15/native-visibility-metrics.json',JSON.stringify({mode,actualDocumentHidden:true,simulatedProperty:false},null,2))
  await expect.poll(()=>page.locator('video').evaluateAll(nodes=>nodes.every(n=>(n as HTMLVideoElement).paused))).toBe(true)
  await cdp.send('Browser.setWindowBounds',{windowId:nativeWindow.windowId,bounds:{windowState:'normal'}})
  await page.bringToFront()
  await expect.poll(()=>page.evaluate(()=>document.hidden)).toBe(false)
  await expect.poll(()=>page.locator('video').evaluateAll(nodes=>nodes.every(n=>!(n as HTMLVideoElement).paused))).toBe(true)
  await page.getByLabel('战斗特效画质').selectOption('low')
  await foreground.bringToFront()
  await page.bringToFront()
  await expect(page.locator('video')).toHaveCount(0)
  await foreground.close()
  await cdp.detach()
})

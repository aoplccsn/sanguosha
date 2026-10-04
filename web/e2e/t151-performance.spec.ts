import { test, expect } from '@playwright/test'
import fs from 'node:fs'
test('profile static and one three five visible portraits',async({page,context})=>{
 test.setTimeout(180000)
 const out:any={label:process.env.T151_LABEL??'before',scenarios:[]}
 for(const count of [0,1,3,5]){
  await page.addInitScript(()=>localStorage.setItem('sanguosha.vfx.quality.v1','high'))
  await page.route('**/src/state/GameContext.tsx',r=>r.fulfill({contentType:'application/javascript',body:`export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},submitDecision(){}}}}`}))
  await page.route('**/src/idlePortraits.ts',async r=>{
   const response=await r.fetch();const body=await response.text()
   // Use real registered resources, restricting count only for measurement.
   await r.fulfill({response,body:body.replace('return assets[id]',`return ['forest_god_lvbu','wind_god_guanyu','fire_god_zhouyu','mountain_god_zhaoyun','wind_zhang_jiao'].slice(0,${count}).includes(id) ? assets[id] : undefined`)})
  })
  await page.addInitScript(()=>{
   const w=window as any;if(w.__calls)return;w.__calls={play:0,pause:0,observer:0,mutations:0}
   for(const method of ['play','pause'] as const){const original=HTMLMediaElement.prototype[method];(HTMLMediaElement.prototype as any)[method]=function(...args:any[]){w.__calls[method]++;return original.apply(this,args as [])}}
   const Original=IntersectionObserver;window.IntersectionObserver=class extends Original{constructor(...args:ConstructorParameters<typeof IntersectionObserver>){super(...args);w.__calls.observer++}}
  })
  const cdp=await context.newCDPSession(page);await cdp.send('Network.clearBrowserCache');await cdp.send('Performance.enable')
  await page.goto('/e2e/fixtures/t15.html?real')
  await expect(page.locator('video')).toHaveCount(count)
  if(count) await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2))).toBe(true)
  await page.getByRole('button',{name:/杀/}).click();await page.locator('[data-player-id="p2"] .portrait-button').click()
  const start=await cdp.send('Performance.getMetrics')
  await cdp.send('Media.enable');const media:any[]=[];cdp.on('Media.playerPropertiesChanged',e=>media.push(e))
  await cdp.send('Tracing.start',{categories:'devtools.timeline,disabled-by-default-devtools.timeline,media,cc',transferMode:'ReturnAsStream'})
  const sample=await page.evaluate(async()=>{
   const w=window as any,videos=Array.from(document.querySelectorAll('video')),calls={...w.__calls}
   const nodes=videos.slice();let changed=0
   const observer=new MutationObserver(records=>{changed+=records.filter(r=>r.type==='childList'||['src','poster'].includes(r.attributeName??'')).length});observer.observe(document.querySelector('.game-board')!,{subtree:true,childList:true,attributes:true,attributeFilter:['src','poster']})
   const start=videos.map(v=>v.getVideoPlaybackQuality());let longTasks=0
   const tasks=new PerformanceObserver(l=>longTasks+=l.getEntries().length);tasks.observe({type:'longtask'})
   const times:number[]=[];let last=performance.now();const end=last+6000
   await new Promise<void>(resolve=>{function frame(now:number){times.push(now-last);last=now;if(now<end)requestAnimationFrame(frame);else resolve()}requestAnimationFrame(frame)})
   // An ordinary projection update with unchanged character/media props.
   w.__t15State.projection={...w.__t15State.projection,deck_count:119};w.__t15Render();await new Promise(r=>setTimeout(r,100))
   observer.disconnect();tasks.disconnect()
   return {fps:1000/(times.reduce((a,b)=>a+b)/times.length),p95:times.sort((a,b)=>a-b)[Math.floor(times.length*.95)],longTasks,dpr:devicePixelRatio,memory:(performance as any).memory?.usedJSHeapSize,callsBefore:calls,callsAfter:w.__calls,mediaMutations:changed,stableVideoNodes:nodes.every((v,i)=>v===document.querySelectorAll('video')[i]),videos:videos.map((v,i)=>{const q=v.getVideoPlaybackQuality(),rect=v.getBoundingClientRect();return {src:v.getAttribute('src'),decode:[v.videoWidth,v.videoHeight],css:[rect.width,rect.height],effective:[rect.width*devicePixelRatio,rect.height*devicePixelRatio],total:q.totalVideoFrames-start[i].totalVideoFrames,dropped:q.droppedVideoFrames-start[i].droppedVideoFrames}})}
  })
  const done=new Promise<any>(resolve=>cdp.once('Tracing.tracingComplete',resolve));await cdp.send('Tracing.end');const complete=await done
  let raw='';while(true){const chunk=await cdp.send('IO.read',{handle:complete.stream});raw+=chunk.data;if(chunk.eof)break}await cdp.send('IO.close',{handle:complete.stream})
  const events=JSON.parse(raw).traceEvents;const buckets:any={}
  for(const e of events){if(e.ph==='X'&&e.dur){const key=e.name;const b=buckets[key]??={count:0,ms:0};b.count++;b.ms+=e.dur/1000}}
  const finish=await cdp.send('Performance.getMetrics');const a=Object.fromEntries(start.metrics.map((m:any)=>[m.name,m.value]));const delta=Object.fromEntries(finish.metrics.map((m:any)=>[m.name,m.value-(a[m.name]??0)]))
  const network=await page.evaluate(()=>performance.getEntriesByType('resource').filter(e=>e.name.includes('/portraits/idle/')).map(e=>({url:e.name,transfer:(e as PerformanceResourceTiming).transferSize,body:(e as PerformanceResourceTiming).encodedBodySize})))
  out.scenarios.push({count,...sample,performanceDelta:delta,network,mediaProperties:media,traceDurations:buckets})
  await cdp.detach();await page.unroute('**/src/idlePortraits.ts');await page.unroute('**/src/state/GameContext.tsx')
 }
 fs.writeFileSync('../docs/t15_1/'+out.label+'-performance.json',JSON.stringify(out,null,2))
 console.log(JSON.stringify(out.scenarios.map((s:any)=>({count:s.count,fps:s.fps,longTasks:s.longTasks,stable:s.stableVideoNodes,calls:s.callsAfter,mutations:s.mediaMutations,task:s.performanceDelta.TaskDuration,script:s.performanceDelta.ScriptDuration}))))
})

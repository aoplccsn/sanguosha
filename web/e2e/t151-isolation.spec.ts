import {test,expect} from '@playwright/test'
import fs from 'node:fs'
test('isolate native video cadence without React or game CSS',async({page})=>{
 const manifest=JSON.parse(fs.readFileSync('../assets/idle_portraits.json','utf8'));const results=[]
 for(const count of [0,1,3,5]){await page.goto('/');await page.setContent('<body></body>');for(const e of Object.values(manifest).slice(0,count) as any[])await page.evaluate(src=>{const v=document.createElement('video');v.src=src;v.muted=true;v.loop=true;v.autoplay=true;v.style.cssText='width:68px;height:90px;object-fit:cover';document.body.append(v)},e.panelVideo);await expect.poll(()=>page.locator('video').evaluateAll(ns=>ns.every(n=>(n as HTMLVideoElement).readyState>=2))).toBe(true);results.push(await page.evaluate(async()=>{let p=performance.now();const a:number[]=[];const end=p+4000;await new Promise<void>(r=>{function f(t:number){a.push(t-p);p=t;t<end?requestAnimationFrame(f):r()}requestAnimationFrame(f)});return {count:document.querySelectorAll('video').length,fps:1000/(a.reduce((x,y)=>x+y)/a.length)}}))}
 fs.writeFileSync('../docs/t15_1/native-isolation.json',JSON.stringify(results,null,2));console.log(results)
})

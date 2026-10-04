import { afterEach, expect, it, vi } from 'vitest'
import { diagnosticReport, runNetworkProbe } from './networkProbe'
afterEach(()=>{vi.useRealTimers();vi.unstubAllGlobals()})
class Socket {
 static OPEN=1
 static last:Socket
 readyState=1
 handlers:Record<string,((event:any)=>void)[]>={}
 constructor(public url:URL){Socket.last=this;queueMicrotask(()=>this.emit('open'))}
 addEventListener(kind:string,fn:(event:any)=>void){(this.handlers[kind]??=[]).push(fn)}
 emit(kind:string,event:any={}){this.handlers[kind]?.forEach(fn=>fn(event))}
 send(){this.emit('message',{data:JSON.stringify({type:'PONG'})})}
 close(){this.readyState=3;this.emit('close')}
}
it('checks health, exact asset, current-origin handshake, pong and persistence, exports only allowlisted data',async()=>{
 vi.useFakeTimers();vi.stubGlobal('WebSocket',Socket)
 vi.stubGlobal('fetch',vi.fn(async(path:string)=>({ok:true,json:async()=>({status:'ok'}),text:async()=>path.includes('network-probe')?'sanguosha-network-asset-v1':''})))
 const pending=runNetworkProbe(new AbortController().signal,6000)
 await vi.advanceTimersByTimeAsync(6001)
 const result=await pending
 expect(result).toMatchObject({http:true,assets:true,websocket:true,pong:true,persistent:true,disconnects:0})
 expect(Socket.last.url.host).toBe(location.host)
 expect(diagnosticReport({...result, secret:'token'} as any)).not.toContain('token')
})
it('reports HTTP/asset/handshake failure without exposing raw server messages',async()=>{
 vi.useFakeTimers();vi.stubGlobal('WebSocket',Socket);vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('private token')))
 const pending=runNetworkProbe(new AbortController().signal)
 await vi.advanceTimersByTimeAsync(1);Socket.last.emit('error')
 const result=await pending;expect(result.http).toBe(false);expect(result.assets).toBe(false);expect(result.persistent).toBe(false)
 expect(diagnosticReport(result)).not.toContain('private')
})

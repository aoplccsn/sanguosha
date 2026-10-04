import { websocketUrl } from './GameConnection'
export interface NetworkResult {
  http: boolean; assets: boolean; websocket: boolean; pong: boolean; persistent: boolean
  rtt: number | null; disconnects: number; browser: string; timestamp: string
}
export async function runNetworkProbe(signal: AbortSignal, duration = 15000): Promise<NetworkResult> {
  const result: NetworkResult = { http: false, assets: false, websocket: false, pong: false, persistent: false,
    rtt: null, disconnects: 0, browser: navigator.userAgent, timestamp: new Date().toISOString() }
  const check = async (path: string, asset = false) => {
    const response = await fetch(path, { cache: 'no-store', signal: AbortSignal.any([signal, AbortSignal.timeout(8000)]) })
    if (!response.ok) return false
    if (asset) return (await response.text()).trim() === 'sanguosha-network-asset-v1'
    const health = await response.json()
    return health.ok === true || health.status === 'ok'
  }
  const checks = await Promise.allSettled([check('/health'), check('/network-probe.txt', true)])
  result.http = checks[0].status === 'fulfilled' && checks[0].value
  result.assets = checks[1].status === 'fulfilled' && checks[1].value
  if (signal.aborted) return result
  await new Promise<void>(resolve => {
    const url = new URL(websocketUrl(location.protocol, location.host))
    url.pathname = '/api/network/ws'
    const socket = new WebSocket(url)
    let opened = false, completed = false, sent = 0, lastPong = 0, count = 0
    let interval: number | undefined, finishTimer: number | undefined
    const finish = () => {
      if (completed) return
      completed = true
      window.clearTimeout(timeout); window.clearTimeout(finishTimer); window.clearInterval(interval)
      signal.removeEventListener('abort', finish)
      socket.close(); resolve()
    }
    const timeout = window.setTimeout(finish, 8000)
    signal.addEventListener('abort', finish, { once: true })
    socket.addEventListener('open', () => {
      opened = true; result.websocket = true; window.clearTimeout(timeout)
      const ping = () => { if (socket.readyState === WebSocket.OPEN) { sent = performance.now(); socket.send(JSON.stringify({ type: 'PING' })) } }
      ping(); interval = window.setInterval(ping, 2000)
      finishTimer = window.setTimeout(() => { result.persistent = count >= 3 && performance.now() - lastPong < 4500; finish() }, duration)
    })
    socket.addEventListener('message', event => {
      try { if (JSON.parse(String(event.data)).type === 'PONG') {
        result.pong = true; lastPong = performance.now(); count++; result.rtt = Math.round(lastPong - sent)
      } } catch { /* The probe never exports raw messages. */ }
    })
    socket.addEventListener('close', () => { if (!completed) { if (opened) result.disconnects++; finish() } })
    socket.addEventListener('error', finish)
  })
  return result
}
export function diagnosticReport(result: NetworkResult) {
  const status = (value: boolean) => value ? '正常' : '失败'
  return ['三国杀网络诊断', `HTTP：${status(result.http)}`, `静态资源：${status(result.assets)}`,
    `实时连接：${status(result.websocket)}`, `心跳响应：${status(result.pong)}`, `持续连接：${status(result.persistent)}`,
    `往返延迟：${result.rtt === null ? '无法测量' : result.rtt + ' ms'}`, `断线次数：${result.disconnects}`,
    `浏览器：${result.browser}`, `时间：${result.timestamp}`].join('\n')
}

import { useEffect, useRef, useState } from 'react'
import { diagnosticReport, runNetworkProbe, type NetworkResult } from '../connection/networkProbe'
export function NetworkDiagnostics() {
  const [result, setResult] = useState<NetworkResult | null>(null)
  const [running, setRunning] = useState(false)
  const [notice, setNotice] = useState('')
  const active = useRef<AbortController | null>(null)
  useEffect(() => () => active.current?.abort(), [])
  async function run() {
    const controller = new AbortController(); active.current?.abort(); active.current = controller
    setRunning(true); setResult(null); setNotice('')
    try { const next = await runNetworkProbe(controller.signal); if (!controller.signal.aborted) setResult(next) }
    catch { if (!controller.signal.aborted) setNotice('检测失败，请重新检测') }
    finally { if (!controller.signal.aborted) setRunning(false) }
  }
  return <main className="home-page"><section className="paper-panel network-diagnostics">
    <p className="eyebrow">连接检查</p><h1>网络诊断</h1><p>检测网页服务、静态资源及实时心跳。持续连接检测约需十五秒。</p>
    <p>结果不包含房间、手牌、身份、令牌、地址或位置信息。</p>
    <button className="brush-button primary" disabled={running} onClick={run}>{running ? '检测中…' : '重新检测'}</button>
    {running && <p role="status">正在检查连接，请保持页面开启…</p>}
    {result && <><pre role="status">{diagnosticReport(result)}</pre><button className="brush-button" onClick={async () => {
      try { await navigator.clipboard.writeText(diagnosticReport(result)); setNotice('诊断结果已复制') } catch { setNotice('复制失败，可选择上方文字手动复制') }
    }}>复制诊断结果</button></>}
    {notice && <p role="status">{notice}</p>}<p><a href="/">返回游戏</a></p>
  </section></main>
}

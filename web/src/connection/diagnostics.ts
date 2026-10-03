export interface DecisionSample {
  click_to_send_ms: number
  send_to_ack_ms: number
  receive_to_accept_ms: number | null
  accept_to_ack_ms: number | null
  ack_to_projection_ms: number | null
  total_ms: number | null
  send_to_server_receive_ms?: number | null
  network_clock_estimate?: boolean
  t0_click_ms?: number
  t1_send_ms?: number
  t2_server_receive_ms?: number
  t3_accept_ms?: number
  t4_ack_emit_ms?: number
  t5_ack_receive_ms?: number
  t6_projection_emit_ms?: number
  t7_render_ms?: number
}

export const diagnostics = {
  decisions: [] as DecisionSample[],
  ping_rtt_ms: [] as number[],
  server_clock_offset_ms: null as number | null,
}

if (typeof window !== 'undefined') {
  Object.assign(window, { sanguoshaDiagnostics: diagnostics })
}

export function recordPing(milliseconds: number, serverTime?: number) {
  diagnostics.ping_rtt_ms.push(Math.round(milliseconds * 100) / 100)
  if (diagnostics.ping_rtt_ms.length > 100) diagnostics.ping_rtt_ms.shift()
  if (serverTime !== undefined) diagnostics.server_clock_offset_ms = serverTime - (Date.now() - milliseconds / 2)
}

export function recordDecision(sample: DecisionSample) {
  diagnostics.decisions.push(sample)
  if (diagnostics.decisions.length > 100) diagnostics.decisions.shift()
  if (import.meta.env.DEV) console.debug('[game] decision timing', sample)
}

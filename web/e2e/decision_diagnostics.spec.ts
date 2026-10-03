import { expect, test } from '@playwright/test'
import { writeFile } from 'node:fs/promises'
import path from 'node:path'

test('real local Durable Object decisions record click through visible completion', async ({ browser }) => {
  test.skip(process.env.REAL_ROOM_DIAGNOSTICS !== '1', 'Requires the local Cloudflare runtime')
  test.setTimeout(180000)
  const context = await browser.newContext()
  const samples: Array<Record<string, number | null>> = []
  const rtt: number[] = []
  for (let index = 0; index < 10; index++) {
    const page = await context.newPage()
    await page.goto('/')
    await page.getByLabel('玩家昵称').fill('本地时序验收')
    await page.getByRole('button', { name: '单人游戏' }).click()
    await expect(page.locator('.general-grid .general-card').first()).toBeVisible({ timeout: 30000 })
    await page.locator('.general-grid .general-card').first().click()
    await page.getByRole('button', { name: '确认武将' }).click()
    await expect(page.locator('.game-page')).toBeVisible({ timeout: 30000 })
    await expect.poll(async () => page.evaluate(() =>
      (window as any).sanguoshaDiagnostics.decisions.some((sample: any) => sample.total_ms !== null))).toBe(true)
    const metrics = await page.evaluate(() => (window as any).sanguoshaDiagnostics)
    for (const sample of metrics.decisions) {
      if (sample.total_ms === null) continue
      samples.push({
        click_to_send_ms: sample.click_to_send_ms,
        send_to_server_receive_estimate_ms: sample.send_to_server_receive_ms,
        server_receive_to_accept_ms: sample.receive_to_accept_ms,
        accept_to_ack_ms: sample.accept_to_ack_ms,
        send_to_ack_ms: sample.send_to_ack_ms,
        ack_to_projection_render_ms: sample.ack_to_projection_ms,
        total_click_to_render_ms: sample.total_ms,
        ack_emit_to_projection_emit_ms: sample.t6_projection_emit_ms - sample.t4_ack_emit_ms,
      })
    }
    rtt.push(...metrics.ping_rtt_ms)
    await page.getByRole('button', { name: '离开牌局' }).click()
    await page.close()
  }
  await context.close()
  expect(samples).toHaveLength(10)
  const summarize = (values: number[]) => {
    values.sort((a, b) => a - b)
    const middle = Math.floor(values.length / 2)
    return { count: values.length, median: values.length % 2 ? values[middle]
      : (values[middle - 1] + values[middle]) / 2, p95: values[Math.ceil(values.length * .95) - 1] }
  }
  const summary = Object.fromEntries(Object.keys(samples[0]).map((field) => [field,
    summarize(samples.map((sample) => sample[field]).filter((value): value is number => value !== null))]))
  const result = { environment: 'local Cloudflare Durable Object with Chromium',
    network_one_way_is_clock_offset_estimate: true, samples, summary, ping_rtt_ms: summarize(rtt) }
  await writeFile(path.resolve('../docs/T14_2_BROWSER_METRICS.json'), JSON.stringify(result, null, 2) + '\n')
  console.log(JSON.stringify(result.summary))
})

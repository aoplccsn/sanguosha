import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs'

// T21 manual-review screenshots. Not pixel snapshots: only structural assertions.
const dir = `../docs/t21/${process.env.T21_PHASE ?? 'after'}`
fs.mkdirSync(dir, { recursive: true })
const shot = (page: Page, name: string) => page.screenshot({ path: `${dir}/${name}.png` })

const card = (id: string, name: string, definition_id: string, suit = '♠', rank = '7', equipment_slot = '') =>
  ({ card_id: id, name, suit, rank, definition_id, category: definition_id.split('.')[0], equipment_slot, details: name + '：卡牌说明' })
const ids = ['sunquan', 'forest_god_lvbu', 'caocao', 'mountain_god_zhaoyun', 'zhouyu', 'wind_god_guanyu', 'liubei', 'fire_god_zhugeliang']
const hand = [card('h1', '杀', 'basic.slash'), card('h2', '闪', 'basic.dodge', '♥', '2'), card('h3', '桃', 'basic.peach', '♥', 'Q'),
  card('h4', '决斗', 'trick.duel', '♣', 'A'), card('h5', '南蛮入侵', 'trick.savage_assault', '♠', 'K'), card('h6', '无懈可击', 'trick.nullification', '♦', 'Q'),
  card('h7', '杀', 'basic.slash', '♦', '9'), card('h8', '火攻', 'trick.fire_attack', '♥', '3')]

async function fixture(page: Page, count: number, mutate: string) {
  await page.addInitScript(() => localStorage.setItem('sanguosha.vfx.quality.v1', 'medium'))
  await page.route('**/src/state/GameContext.tsx', r => r.fulfill({ contentType: 'application/javascript', body: `export function useGame(){return {state:window.__t15State,actions:{returnHome(){},clearError(){},setPresentationSpeed(){},submitDecision(id,value){window.__decision={id,value}}}}}` }))
  await page.goto('/e2e/fixtures/t15.html?real')
  const catalog = await (await page.request.get('/api/catalog/generals')).json()
  await page.evaluate(({ catalog, count, ids, hand, mutate }) => {
    const w = window as any, s = w.__t15State
    s.roomCode = 'T21'; s.generals = Object.fromEntries(catalog.map((g: any) => [g.id, g]))
    s.projection.players = Array.from({ length: count }, (_, i) => {
      const g = s.generals[ids[i]]
      return { player_id: 'p' + (i + 1), name: '玩家' + (i + 1), character_id: ids[i], character_name: g?.name ?? ids[i], identity_label: i === 0 ? '主公' : '未知',
        hp: 3 + (i % 2), max_hp: 4, hand_count: 3 + i % 4, alive: true, active: i === 0, faction: '群', chained: i === 2, equipment: [], judgments: [], attack_range: 1, effective_distance: 1 + (i % 3),
        skill_labels: (g?.skills ?? []).map((k: any) => k.name), marks: i === 3 ? { ren: 2 } : {} }
    })
    const [self, , third] = s.projection.players
    self.equipment = [
      { card_id: 'eq1', name: '诸葛连弩', suit: '♣', rank: 'A', definition_id: 'equipment.weapon.crossbow', category: 'equipment', equipment_slot: 'weapon', details: '连弩' },
      { card_id: 'eq2', name: '八卦阵', suit: '♠', rank: '2', definition_id: 'equipment.armor.eight_trigrams', category: 'equipment', equipment_slot: 'armor', details: '八卦' },
      { card_id: 'eq3', name: '的卢', suit: '♣', rank: '5', definition_id: 'equipment.horse.dilu', category: 'equipment', equipment_slot: 'defensive_horse', details: '+1' }]
    self.judgments = [{ card_id: 'j1', name: '乐不思蜀', suit: '♥', rank: '6', definition_id: 'delayed.indulgence', category: 'delayed', equipment_slot: '', details: '乐' }]
    third.equipment = [{ card_id: 'eq4', name: '赤兔', suit: '♥', rank: '5', definition_id: 'equipment.horse.chitu', category: 'equipment', equipment_slot: 'offensive_horse', details: '-1' }]
    s.projection.hand = hand
    s.pendingRequest = { request_id: 'play', player_id: 'p1', request_type: 'choose_option', prompt: 'Choose a play action or end the play phase',
      choices: ['use:h1', 'use:h3', 'use:h4', 'use:h5', 'use:h7', 'end_play_phase'], allowed_player_ids: [], eligible_card_ids: [], allow_pass: false, min_count: 0, max_count: 0, remaining_ms: 30000,
      play_card_targets: { 'use:h1': { targets: ['p2', 'p3', 'p' + count], min: 1, max: 1 }, 'use:h7': { targets: ['p2', 'p3'], min: 1, max: 1 }, 'use:h4': { targets: s.projection.players.slice(1).map((p: any) => p.player_id), min: 1, max: 1 } } }
    new Function('s', mutate)(s)
    w.__t15Render()
  }, { catalog, count, ids, hand, mutate })
  await expect(page.locator('.player-panel')).toHaveCount(count)
}

async function noOverlap(page: Page) {
  const boxes = await page.locator('.game-board > .player-panel').evaluateAll(es => es.map(e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom] }))
  const local = await page.locator('.self-area').evaluate(e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom] })
  const hit = (a: number[], b: number[]) => a[0] < b[2] - 1 && b[0] < a[2] - 1 && a[1] < b[3] - 1 && b[1] < a[3] - 1
  for (const [i, a] of boxes.entries()) {
    for (const b of boxes.slice(i + 1)) expect(hit(a, b), 'seats overlap').toBe(false)
    expect(hit(a, local), 'seat overlaps local area').toBe(false)
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
}

for (const count of [5, 8]) for (const [w, h] of [[1920, 1080], [1440, 900], [1366, 768], [1024, 768]]) {
  test(`T21 table ${count} seats ${w}x${h}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h })
    await fixture(page, count, `s.projection.waiting={key:'r',player_id:'p3',responding:true,thinking:false,remaining_ms:9000,total_ms:15000,required_definition_id:'basic.dodge',response_to:'basic.slash'}`)
    if (process.env.T21_PHASE !== 'baseline') await noOverlap(page)
    await shot(page, `table-${count}-${w}x${h}`)
  })
}

test('T21 card and target selection', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await fixture(page, 8, '')
  await page.getByRole('button', { name: '杀 ♠7' }).click()
  await expect(page.locator('.hand-card.selected')).toHaveCount(1)
  await shot(page, 'card-selected')
  await expect(page.locator('.player-panel.selectable')).toHaveCount(3)
  await page.locator('[data-player-id="p3"] .portrait-button').click()
  await expect(page.locator('[data-player-id="p3"]')).toHaveClass(/selected-target/)
  expect(await page.evaluate(() => (window as any).__decision)).toBeUndefined()
  await page.locator('[data-player-id="p2"] .portrait-button').hover()
  await shot(page, 'target-selected')
  await page.getByRole('button', { name: '确定', exact: true }).click()
  expect(await page.evaluate(() => (window as any).__decision.value)).toEqual({ option: 'use:h1', targets: ['p3'] })
})

test('T21 complex multi-select request', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await fixture(page, 5, `s.pendingRequest={request_id:'zh',player_id:'p1',request_type:'choose_cards',prompt:'【制衡】选择任意张手牌或装备弃置',choices:[],eligible_card_ids:['eq1','eq2','eq3','h1','h2','h3','h4','h5','h6','h7','h8'],allowed_player_ids:[],allow_pass:true,min_count:1,max_count:7,remaining_ms:30000}`)
  for (const name of ['杀 ♠7', '闪 ♥2', '决斗 ♣A']) await page.getByRole('button', { name }).click()
  await page.getByRole('button', { name: '装备 八卦阵' }).click()
  await shot(page, 'complex-request')
})

test('T21 AOE and nullification resolution', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await fixture(page, 8, `s.projection.combat={source_id:'p2',definition_id:'trick.savage_assault',card_name:'南蛮入侵',target_ids:['p3','p4','p5','p6','p7','p8','p1'],current_target_id:'p5',resolved_target_ids:['p3','p4'],nullification_count:1,top_response:{source_id:'p4',definition_id:'trick.nullification'}};
    s.pendingRequest={request_id:'nu',player_id:'p1',request_type:'respond_with_card',prompt:'Respond with a card or pass',choices:[],eligible_card_ids:['h6'],allowed_player_ids:[],required_definition_id:'trick.nullification',allow_pass:true,allow_root_trick_pass:true,min_count:1,max_count:1,remaining_ms:12000};
    s.projection.players[0].active=false;s.projection.players[1].active=true`)
  await shot(page, 'aoe-nullification')
})

test('T21 real draft, 5 and 8 seat tables, refresh reconnect', async ({ page }) => {
  const errors: string[] = []
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|favicon|\.mp4|net::/.test(m.text())) errors.push(m.text()) })
  page.on('pageerror', e => errors.push(String(e)))
  for (const mode of ['military-five', 'military-eight']) {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/?seed=21')
    await page.getByLabel('对局模式').selectOption(mode)
    await page.getByRole('button', { name: '单人游戏', exact: true }).click()
    await expect(page.locator('.general-card').first()).toBeVisible()
    if (mode === 'military-five') await shot(page, 'draft')
    await page.locator('.general-card').first().click()
    await page.getByRole('button', { name: '确认武将' }).click()
    await expect(page.locator('.player-panel')).toHaveCount(mode === 'military-five' ? 5 : 8)
    await page.waitForTimeout(2500)
    await shot(page, `real-${mode}`)
    const seats = await page.locator('.player-panel').count()
    await expect(page.locator('.player-self')).toHaveCount(1)
    if (process.env.T21_PHASE !== 'baseline') await noOverlap(page)
    await page.reload()
    await page.getByRole('button', { name: '继续对局', exact: true }).click()
    await expect(page.locator('.player-panel')).toHaveCount(seats)
    await expect(page.locator('.player-self')).toHaveCount(1)
    await page.getByRole('button', { name: '离开牌局' }).click()
  }
  expect(errors).toEqual([])
})

// T21.1 orientation: landscape uses the mobile table; portrait is a usable fallback, never a gate.
for (const [w, h, count] of [[844, 390, 5], [915, 412, 8], [390, 844, 5], [412, 915, 8]]) {
  test(`T21.1 mobile ${w > h ? 'landscape' : 'portrait'} ${count} seats`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h })
    await fixture(page, count, '')
    await expect(page.getByText('请横屏游玩')).toHaveCount(0)
    await expect(page.locator('.player-panel:visible')).toHaveCount(count)
    if (w > h) {
      const x = async (sel: string) => (await page.locator(sel).boundingBox())!
      const [eq, hand, skills, self] = [await x('.equipment-area'), await x('.hand'), await x('.skill-area'), await x('.player-self')]
      expect(eq.x + eq.width).toBeLessThanOrEqual(hand.x + 1)
      expect(hand.x + hand.width).toBeLessThanOrEqual(skills.x + 1)
      expect(skills.x + skills.width).toBeLessThanOrEqual(self.x + 1)
      await noOverlap(page)
    }
    // Full play flow: card → target → Confirm, everything reachable in this orientation.
    await page.getByRole('button', { name: '杀 ♠7' }).click()
    await page.locator('[data-player-id="p3"] .portrait-button').click()
    const confirm = page.getByRole('button', { name: '确定', exact: true })
    await confirm.scrollIntoViewIfNeeded(); await expect(confirm).toBeInViewport()
    await expect(page.getByRole('button', { name: '取消选中' })).toBeInViewport()
    await shot(page, `mobile-${w}x${h}-${count}`)
    await confirm.click()
    expect(await page.evaluate(() => (window as any).__decision.value)).toEqual({ option: 'use:h1', targets: ['p3'] })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('T21.1 failed fullscreen and orientation lock still enters and plays', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const page = await context.newPage()
  await page.addInitScript(() => {
    (window as any).__lockCalls = 0
    Element.prototype.requestFullscreen = () => Promise.reject(new Error('denied'))
    Object.defineProperty(screen, 'orientation', { configurable: true, value: { type: 'portrait-primary', lock: () => { (window as any).__lockCalls++; return Promise.reject(new Error('NotSupportedError')) } } })
  })
  await page.goto('/?seed=21')
  await page.getByRole('button', { name: '单人游戏', exact: true }).tap()
  await page.locator('.general-card').first().tap()
  await page.getByRole('button', { name: '确认武将' }).tap()
  await expect(page.locator('.player-self')).toBeVisible()
  await expect(page.locator('.hand')).toBeVisible()
  await expect(page.getByText('请横屏游玩')).toHaveCount(0)
  expect(await page.evaluate(() => (window as any).__lockCalls)).toBeGreaterThan(0)
  await shot(page, 'mobile-lock-failed-portrait')
  await page.setViewportSize({ width: 844, height: 390 })  // manual rotation later re-lays out
  await expect(page.locator('.self-area .player-self')).toBeInViewport()
  await context.close()
})

test('T21.2 portrait close-ups', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await fixture(page, 8, `s.projection.players[0].character_id='fire_god_zhouyu';s.projection.players[3].character_id='fire_god_zhugeliang';s.projection.players[5].character_id='thunder_god_ganning';s.projection.players.forEach(p=>p.character_name=s.generals[p.character_id].name)`)
  await page.waitForTimeout(1500)
  const rects = await page.locator('.player-panel').evaluateAll(ps => ps.map(p => {
    const b = p.querySelector('.portrait-button')!.getBoundingClientRect()
    const m = [...p.querySelectorAll('.dynamic-portrait > img, .dynamic-portrait > video')].map(e => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return [Math.round(r.width), Math.round(r.height), cs.objectFit, cs.objectPosition, (e as HTMLVideoElement).videoWidth ?? 0, (e as HTMLVideoElement).videoHeight ?? 0, (e as HTMLImageElement).naturalWidth ?? 0, (e as HTMLImageElement).naturalHeight ?? 0] })
    return [p.getAttribute('data-character-id'), Math.round(b.width), Math.round(b.height), m]
  }))
  console.log(JSON.stringify(rects))
  for (const id of ['p1', 'p2', 'p4', 'p6']) await page.locator(`[data-player-id="${id}"]`).screenshot({ path: `${dir}/portrait-${id}.png` })
})

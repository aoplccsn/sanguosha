import { test, expect } from '@playwright/test'

for (const [mode, seats] of [['military-five', 5], ['military-eight', 8]] as const) {
  test('T19.2 protected test room completes 榻谟 in ' + mode, async ({ page }) => {
    await page.goto('/?seed=0')
    await page.getByRole('combobox', { name: '对局模式' }).selectOption(mode)
    await page.getByRole('button', { name: '测试模式' }).click()
    await page.getByLabel('测试权限码').fill('fixture-only-code')
    await page.getByRole('button', { name: '验证' }).click()
    await expect(page.getByRole('button', { name: '创建测试房' })).toBeVisible()
    await page.getByRole('button', { name: '创建测试房' }).click()
    await expect(page.getByText('测试房 · 自选武将')).toBeVisible()
    await page.getByLabel('搜索武将或技能').fill('神鲁肃')
    await page.getByRole('button', { name: /神鲁肃/ }).first().click()
    await page.getByRole('button', { name: '确认武将' }).click()
    await page.getByRole('button', { name: '魏', exact: true }).click()
    await expect(page.getByText('榻谟：调整非主公角色座次？')).toBeVisible({ timeout: 30000 })
    await page.getByRole('button', { name: '发动 / 是' }).click()
    await expect(page.getByText('榻谟：按新座次顺序选择全部非主公角色')).toBeVisible()
    const candidates = page.locator('.player-panel.selectable .portrait-button')
    await expect(candidates).toHaveCount(seats - 1)
    await expect(page.locator('.player-panel.player-self.selectable .portrait-button')).toBeVisible()
    for (let i = 0; i < seats - 1; i++) await candidates.nth(i).click()
    await expect(page.getByRole('button', { name: '确定' })).toBeEnabled()
    await page.getByRole('button', { name: '确定' }).click()
    await expect(page.getByText('榻谟：按新座次顺序选择全部非主公角色')).toHaveCount(0)
  })
}

const quickGenerals = [
  'mobile_god_taishici', 'mobile_god_sunce', 'mountain_god_simayi',
  'mobile_god_guojia', 'mobile_god_xunyu',
]
for (const id of quickGenerals) {
  test('T19.2 test room selects and reconnects ' + id, async ({ page, request }) => {
    const catalog = await (await request.get('/api/catalog/generals')).json()
    const general = catalog.find((item: { id: string }) => item.id === id)
    expect(general).toBeTruthy()
    await page.goto('/?seed=0')
    await page.getByRole('button', { name: '测试模式' }).click()
    await page.getByLabel('测试权限码').fill('fixture-only-code')
    await page.getByRole('button', { name: '验证' }).click()
    await page.getByRole('button', { name: '创建测试房' }).click()
    await page.getByLabel('搜索武将或技能').fill(general.name)
    await page.getByRole('button', { name: new RegExp(general.name) }).first().click()
    await page.getByRole('button', { name: '确认武将' }).click()
    await expect(page.locator('.game-page')).toBeVisible()
    await expect(page.locator('.player-panel.player-self')).toHaveAttribute('data-character-id', id)
    await page.reload()
    await page.getByRole('button', { name: '继续对局' }).click()
    await expect(page.locator('.player-panel.player-self')).toHaveAttribute('data-character-id', id)
  })
}

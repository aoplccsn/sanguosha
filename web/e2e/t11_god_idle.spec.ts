import { expect, test } from '@playwright/test'

test('Lu Bu idle moves character layers and blinks naturally', async ({ page }) => {
  await page.clock.install()
  await page.addInitScript(() => { Math.random = () => 0 })
  await page.goto('/t11/god-lvbu-preview')
  const portrait = page.locator('.god-preview-hero .god-portrait')
  for (const part of ['body', 'head', 'hair-back', 'hair-front', 'cloth-back', 'cloth-front']) {
    const animation = await portrait.locator('.god-' + part).evaluate((element) => getComputedStyle(element).animationName)
    expect(animation).not.toBe('none')
  }
  await expect(portrait.locator('.god-body')).toHaveAttribute('mask', /body-mask/)
  const grip = await portrait.locator('.god-strike-limb').evaluate((element) => getComputedStyle(element).animationName)
  expect(grip).toContain('lvbuGrip')
  await page.clock.fastForward(2850)
  await expect(portrait.locator('.god-blink-frame.visible')).toHaveCount(1)
  await page.clock.fastForward(120)
  await expect(portrait.locator('.god-blink-frame.visible')).toHaveCount(0)
})

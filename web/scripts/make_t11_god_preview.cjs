const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const out = 'C:\\Sanguosha\\docs\\t11\\god_art\\review'
const images = '../../../../assets/gods/forest_god_lvbu/'
const html = '<!doctype html><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#141014;color:#eee;font-family:Segoe UI,Microsoft YaHei,sans-serif;padding:44px}h1{font-size:36px;margin:0 0 24px}.row{display:flex;align-items:flex-start;gap:48px}.portrait{position:relative;overflow:hidden;background:#1b1010;border:2px solid #a76d43;isolation:isolate}.portrait.large{width:360px;height:600px}.portrait.small{width:70px;height:92px}.portrait img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center top}.small img{width:240%;height:240%;left:-70%;top:-20%}.background{transform:scale(1.025)}.body{transform:translateY(-.4%) scale(1.008)}.static{width:360px;height:600px;object-fit:cover;object-position:center top;border:2px solid #a76d43}p{font-size:18px;color:#c7b6a8}</style><h1>神吕布 · 分层动态样板对位检查</h1><div class="row"><div><div class="portrait large"><img class="background" src="' + images + 'background.png"><img class="body" src="' + images + 'body.png"></div><p>高/中档 · 背景 + 人物</p></div><div><img class="static" src="' + images + 'portrait.png"><p>低档 · 静态回退</p></div><div><div class="portrait small"><img class="background" src="' + images + 'background.png"><img class="body" src="' + images + 'body.png"></div><p>牌桌头像尺寸</p></div></div>'
const file = path.join(out, 'god_lvbu_dynamic_preview.html')
fs.writeFileSync(file, html)
;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1050, height: 770 } })
  await page.goto('file:///' + file.replace(/\\/g, '/'))
  await Promise.all((await page.locator('img').all()).map(img => img.evaluate(node => node.decode())))
  await page.screenshot({ path: path.join(out, 'god_lvbu_dynamic_preview.png') })
  await browser.close()
  console.log('Lu Bu dynamic preview ready')
})().catch(error => { console.error(error); process.exit(1) })

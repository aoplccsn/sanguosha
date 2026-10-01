const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const root = 'C:\\Sanguosha\\docs\\t11\\god_art';
const review = path.join(root, 'review');
const gods = [
  ['guanyu', '神关羽', '青绿 · 忠义 · 武魂'],
  ['lvmeng', '神吕蒙', '幽蓝 · 洞察 · 水墨'],
  ['zhouyu', '神周瑜', '赤金 · 琴火 · 风雅'],
  ['zhugeliang', '神诸葛亮', '星蓝 · 天象 · 雾'],
  ['caocao', '神曹操', '黑金 · 帝王 · 战魂'],
  ['lvbu', '神吕布', '赤黑 · 战神 · 戟'],
  ['zhaoyun', '神赵云', '银青 · 龙魂 · 速度'],
  ['simayi', '神司马懿', '紫黑 · 权谋 · 时间'],
];
function html(body, styles = '') {
  return '<!doctype html><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#131015;color:#f1e7d8;font-family:Segoe UI,Microsoft YaHei,sans-serif}' + styles + '</style>' + body;
}
(async () => {
  fs.mkdirSync(review, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  for (const [id, name, theme] of gods) {
    const image = '../candidates/god_' + id + '_v1.png';
    const body = '<div class="sheet"><div class="hero"><img src="' + image + '"></div><div class="info"><p class="eyebrow">T11 · ORIGINAL GOD PORTRAIT · CANDIDATE V1</p><h1>' + name + '</h1><p>' + theme + '</p><div class="details"><div><span>头像裁切预览</span><img src="' + image + '"></div><div><span>全身构图检查</span><img src="' + image + '"></div></div><p class="note">主立绘候选 · 动画分层与特效素材待制作</p></div></div>';
    const styles = '.sheet{height:900px;display:grid;grid-template-columns:570px 630px}.hero{height:900px;overflow:hidden}.hero img{width:100%;height:100%;object-fit:cover;object-position:center 30%}.info{padding:70px 42px;background:linear-gradient(130deg,#251d21,#100e14)}.eyebrow{font-size:13px;letter-spacing:.15em;color:#c39c65}h1{font-size:55px;margin:24px 0}p{font-size:23px;color:#d8c6b4}.details{display:flex;gap:24px;margin-top:62px}.details div{width:240px}.details span{display:block;margin-bottom:12px;color:#c39c65}.details img{width:240px;height:320px;object-fit:cover;object-position:50% 16%;border:1px solid #a28257}.details div+div img{object-position:50% 50%}.note{margin-top:48px;font-size:16px;color:#a99b91}';
    const file = path.join(review, 'god_' + id + '_sheet.html');
    fs.writeFileSync(file, html(body, styles));
    const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 1 });
    await page.goto('file:///' + file.replace(/\\/g, '/'));
    await page.locator('img').first().evaluate(img => img.decode());
    await page.screenshot({ path: path.join(review, 'god_' + id + '_sheet.png') });
    await page.close();
  }
  const cards = gods.map(([id, name, theme]) => '<article><img src="../candidates/god_' + id + '_v1.png"><div><b>' + name + '</b><small>' + theme + '</small></div></article>').join('');
  const file = path.join(review, 'all_8_gods_overview.html');
  fs.writeFileSync(file, html('<header><span>T11 · ORIGINAL GOD ART REVIEW</span><h1>八神将立绘总览</h1></header><main>' + cards + '</main>', 'header{height:150px;padding:28px 60px}header span{color:#c39c65;letter-spacing:.2em;font-size:15px}header h1{margin:12px 0;font-size:44px}main{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;padding:0 38px 38px}article{height:660px;background:#251e22;border:1px solid #74563b;overflow:hidden}article img{width:100%;height:580px;object-fit:cover;object-position:center 22%}article div{padding:9px 14px}b{display:block;font-size:22px}small{display:block;color:#baaa9c;font-size:13px}'));
  const page = await browser.newPage({ viewport: { width: 2000, height: 1510 }, deviceScaleFactor: 1 });
  await page.goto('file:///' + file.replace(/\\/g, '/'));
  await Promise.all((await page.locator('img').all()).map(img => img.evaluate(node => node.decode())));
  await page.screenshot({ path: path.join(review, 'all_8_gods_overview.png') });
  await browser.close();
  console.log('Created 8 individual review sheets and overview.');
})().catch(error => { console.error(error); process.exit(1); });

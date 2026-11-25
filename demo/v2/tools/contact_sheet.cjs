#!/usr/bin/env node
// Builds cards/contact_sheet.png from cards/png/*.png (cards in cards.json order, then example_*.png layouts).
const fs = require('fs'); const L = require('./lib.cjs'); const C = L.V2 + '/cards';
const cards = JSON.parse(fs.readFileSync(C + '/cards.json', 'utf8')).cards;
const tiles = cards.map(c => [c.id + '  ·  ' + c.dur + ' s', `${C}/png/${c.id}.png`]);
for (const [n, f] of [['layout: phone left, caption right', 'example_phone'], ['layout: split screen', 'example_split']]) if (fs.existsSync(`${C}/png/${f}.png`)) tiles.push([n, `${C}/png/${f}.png`]);
const html = `<div style="position:absolute;inset:0;background:#EDEBE5;padding:28px 28px"><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:22px 20px;font-size:17px;color:#4E4E60">
${tiles.map(([t, f]) => `<div><img src="file://${f}" style="width:100%;display:block;border:1px solid #D2CEC4;border-radius:6px"><div style="margin-top:7px;font-weight:600">${t}</div></div>`).join('')}</div></div>`;
(async () => {
  const ctx = await L.launch(); const h = await L.openHtml(ctx, html.replace('position:absolute;inset:0;', 'position:absolute;left:0;top:0;width:1920px;'), 'html,body{height:auto!important;overflow:visible!important;background:#EDEBE5!important}');
  await h.page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
  await h.page.setViewportSize({ width: 1920, height: 1080 });
  const hh = await h.page.evaluate(() => document.body.firstElementChild.getBoundingClientRect().height);
  await h.page.screenshot({ path: C + '/contact_sheet.png', fullPage: true });
  await ctx.close(); console.log('contact sheet', C + '/contact_sheet.png', tiles.length + ' tiles');
})();

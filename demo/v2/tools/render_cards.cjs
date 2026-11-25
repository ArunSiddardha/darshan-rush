#!/usr/bin/env node
// usage: node render_cards.cjs [card_id ...]   (no ids = all cards)
// Reads cards/cards.json, numbers.json, team.json. Writes cards/clips/<id>.mp4 and cards/png/<id>.png (final frame, with background).
const fs = require('fs');
const L = require('./lib.cjs');
const C = L.V2 + '/cards';
const cfg = JSON.parse(fs.readFileSync(C + '/cards.json', 'utf8'));
const data = { numbers: JSON.parse(fs.readFileSync(C + '/numbers.json', 'utf8')), team: JSON.parse(fs.readFileSync(C + '/team.json', 'utf8')) };
const sub = (t) => t.replace(/\{\{([\w.]+)\}\}/g, (_, k) => { const v = k.split('.').reduce((o, p) => o && o[p], data); if (v === undefined) throw new Error('missing ' + k); return v; });

const THEMES = { black: ['#000000', '#FFFFFF', '#B9B9C6'], light: ['#FBFAF7', '#1B1B26', '#4E4E60'], indigo: ['#2B2E8C', '#FFFFFF', '#C9CBF2'] };
const CSS = `
.stage{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center}
.center .stage{align-items:center;text-align:center;padding:0 220px}
.left .stage{align-items:flex-start;padding:0 0 0 300px}
.it{display:block}
.hook{font-size:68px;font-weight:400;line-height:1.28;max-width:1400px;text-wrap:balance;letter-spacing:-.003em}
.rule{width:132px;height:8px;border-radius:4px;background:var(--saffron);margin-bottom:52px}
.rule.c{margin-bottom:56px}
.name{font-size:104px;font-weight:700;line-height:1.1;letter-spacing:-.012em;margin-bottom:44px}
.fact{font-size:56px;font-weight:400;line-height:1.3;margin-bottom:14px}
.foot{position:absolute;bottom:92px;left:300px;font-size:32px;font-weight:400;color:var(--grey)}
.foot.center{left:0;right:0;text-align:center}
.light .fact{color:var(--ink2)}
.big{font-size:88px;font-weight:600;line-height:1.15;letter-spacing:-.01em;margin-bottom:34px}
.small{font-size:34px;font-weight:400;opacity:.85}
.money{font-size:76px;font-weight:600;line-height:1.2;margin:22px 0;letter-spacing:-.008em;text-wrap:balance}
.honest{font-size:64px;font-weight:500;line-height:1.2;margin:20px 0;color:var(--ink2)}
.honest.strong{font-weight:700;color:var(--ink)}
.endtitle{font-size:140px;font-weight:700;line-height:1.05;letter-spacing:-.015em;margin-bottom:40px}
.endsp{font-size:52px;font-weight:500;color:var(--ink2);margin-bottom:34px}
.endteam{font-size:36px;font-weight:400;color:var(--grey)}
.numbers .stage{display:block}
.numbers .divider{position:absolute;left:960px;top:210px;width:2px;height:600px;background:var(--line)}
.col{position:absolute;width:760px}
.col.l{left:140px} .col.r{left:1020px}
.col.head{top:190px;font-size:44px;font-weight:700;letter-spacing:.14em;text-transform:uppercase}
.col.l.head{color:var(--saffron)} .col.r.head{color:var(--indigo)}
.col.bignum{top:262px;font-size:210px;font-weight:700;line-height:1;letter-spacing:-.03em}
.col.l.bignum{color:var(--saffron)} .col.r.bignum{color:var(--indigo)}
.col.biglabel{top:500px;font-size:46px;font-weight:500;color:var(--ink2)}
.col.line{font-size:52px;font-weight:600;line-height:1.25;color:var(--ink)}
.col.line:nth-of-type(n){top:0}
`;
function build(card) {
  const [bg, fg, fg2] = THEMES[card.theme];
  let li = 0, lineIdx = { l: 0, r: 0 };
  const items = card.items.map((it, i) => {
    const text = it.text !== undefined ? sub(it.text) : '';
    let style = '';
    if (card.layout === 'numbers' && /\bline\b/.test(it.cls)) {
      const side = /\bl\b/.test(it.cls) ? 'l' : 'r';
      style = `top:${590 + lineIdx[side] * 72}px;`; lineIdx[side]++;
    }
    if (text === '' && it.cls.indexOf('rule') < 0) return `<div class="it ${it.cls}" data-i="${i}" style="${style}"></div>`;
    return `<div class="it ${it.cls}" data-i="${i}" style="${style}">${L.rich(text)}</div>`;
  }).join('');
  const body = `<div class="${card.layout} ${card.theme === 'light' ? 'light' : 'on-dark'}" style="position:absolute;inset:0;color:${fg}">
    ${card.layout === 'numbers' ? '<div class="divider"></div>' : ''}<div class="stage">${items}</div></div>`;
  return { body, bg };
}

(async () => {
  const want = process.argv.slice(2);
  const cards = cfg.cards.filter(c => !want.length || want.includes(c.id));
  if (!cards.length) throw new Error('no such card: ' + want.join(','));
  fs.mkdirSync(C + '/clips', { recursive: true }); fs.mkdirSync(C + '/png', { recursive: true });
  const ctx = await L.launch();
  for (const card of cards) {
    const t0 = Date.now();
    const { body, bg } = build(card);
    const h = await L.openHtml(ctx, body, CSS, '');
    const page = h.page;
    const dir = `${L.BUILD}/${card.id}`; fs.mkdirSync(dir, { recursive: true });
    // final composite with background, for the contact sheet
    await page.evaluate((bg) => { document.body.style.background = bg; }, bg);
    await L.shot(page, `${C}/png/${card.id}.png`, false);
    // one transparent layer per item
    await page.evaluate(() => { document.body.style.background = 'transparent'; });
    const n = card.items.length, files = [];
    for (let i = 0; i < n; i++) {
      await page.evaluate((i) => document.querySelectorAll('.it').forEach(e => { e.style.visibility = (+e.dataset.i === i) ? 'visible' : 'hidden'; }), i);
      const f = `${dir}/layer${i}.png`; await L.shot(page, f, true); files.push(f);
    }
    await page.close(); L.cleanup(h);
    // ffmpeg: bg colour, layers fade in with a small upward drift, global fade
    const dur = card.dur, [fi, fo] = card.fade || [0.4, 0.5];
    const args = ['-f', 'lavfi', '-i', `color=c=${bg.replace('#', '0x')}:s=1920x1080:r=30:d=${dur}`];
    files.forEach(f => args.push('-loop', '1', '-framerate', '30', '-t', String(dur), '-i', f));
    let fc = [], last = '0:v';
    card.items.forEach((it, i) => {
      const at = it.at, d = it.d || 0.8;
      let chain = `[${i + 1}:v]format=rgba,fade=t=in:st=${at}:d=${d}:alpha=1`;
      if (it.out !== undefined) chain += `,fade=t=out:st=${it.out}:d=${it.outd || 0.7}:alpha=1`;
      fc.push(`${chain}[l${i}]`);
      fc.push(`[${last}][l${i}]overlay=x=0:y='16*pow(1-min(1\\,max(0\\,(t-${at})/${d}))\\,3)':eval=frame:shortest=0[o${i}]`);
      last = `o${i}`;
    });
    let post = `[${last}]format=yuv420p`;
    if (fi > 0) post += `,fade=t=in:st=0:d=${fi}`;
    if (fo > 0) post += `,fade=t=out:st=${dur - fo}:d=${fo}`;
    fc.push(post + '[v]');
    args.push('-filter_complex', fc.join(';'), '-map', '[v]', '-t', String(dur), '-r', '30', '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
      '-pix_fmt', 'yuv420p', '-movflags', '+faststart', `${C}/clips/${card.id}.mp4`);
    L.ffmpeg(args);
    console.log(`${card.id}  ${dur}s  ${((Date.now() - t0) / 1000).toFixed(1)}s render`);
  }
  await ctx.close();
})().catch(e => { console.error(e); process.exit(1); });

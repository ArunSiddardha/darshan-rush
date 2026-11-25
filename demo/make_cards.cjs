// Renders caption, title and end-card PNGs (1920x1080) from EDIT.txt using the app's Anek fonts.
// ffmpeg here has no drawtext, so all text is drawn by headless Chrome. usage: node make_cards.cjs <EDIT.txt> <outdir>
const fs = require('fs'), path = require('path');
const { chromium } = require('/Users/arun/automation/vt/node_modules/playwright-core');
const CHROME = '/Users/arun/automation/browsers/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const PROFILE = '/Users/arun/hackathon/festive/_tools/tmp-profile-demo-cards';
const FONTS = ['/Users/arun/hackathon/festive/repo/app/static_v2/fonts', '/Users/arun/hackathon/festive/repo/app/static/fonts']
  .find(d => fs.existsSync(d + '/AnekLatin-latin.woff2'));
const [edit, outdir] = process.argv.slice(2);
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const faces = fs.readdirSync(FONTS).filter(f => f.endsWith('.woff2') && f.startsWith('Anek')).map(f =>
  `@font-face{font-family:Anek;font-weight:400 700;font-stretch:75% 125%;src:url(file://${FONTS}/${f}) format('woff2');}`).join('');
const css = `${faces}
*{box-sizing:border-box;margin:0}
body{width:1920px;height:1080px;font-family:Anek,sans-serif;color:#1A1917;overflow:hidden}
.bg{background:#F3F1EC} .clear{background:transparent}
.lower{position:absolute;left:96px;bottom:84px;max-width:1500px;background:#0D5C63;color:#fff;padding:22px 36px;border-radius:14px;font-size:44px;font-weight:600;line-height:1.25;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.side{position:absolute;left:760px;right:110px;top:0;bottom:0;display:flex;align-items:center}
.side p{font-size:64px;font-weight:600;line-height:1.2;color:#1A1917;border-left:10px solid #0D5C63;padding-left:36px}
.big{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 160px;background:#0D5C63;color:#fff}
.big h1{font-size:112px;font-weight:700;line-height:1.05;letter-spacing:-1px}
.big h2{font-size:48px;font-weight:400;margin-top:36px;opacity:.92;line-height:1.3;max-width:1500px}
.big small{position:absolute;left:160px;bottom:70px;font-size:28px;opacity:.8}
.sim{position:absolute;right:60px;top:44px;font-size:24px;font-weight:600;letter-spacing:2px;background:#fff;color:#0D5C63;padding:8px 16px;border-radius:8px}`;
(async () => {
  fs.mkdirSync(outdir, { recursive: true }); fs.mkdirSync(PROFILE, { recursive: true });
  const ctx = await chromium.launchPersistentContext(PROFILE, { headless: true, executablePath: CHROME, viewport: { width: 1920, height: 1080 } });
  const pg = await ctx.newPage();
  const lines = fs.readFileSync(edit, 'utf8').split('\n');
  let n = 0;
  for (const raw of lines) {
    const l = raw.trim(); if (!l || l.startsWith('#')) continue;
    n++;
    const [file, , , layout, cap = ''] = l.split('|').map(s => s.trim());
    const [main, sub = ''] = cap.split(' // ');
    let body, cls = 'clear';
    if (layout === 'title') body = `<div class="big"><h1>${esc(main)}</h1><h2>${esc(sub)}</h2><small>Festive Hacks 2026 · Simulated crowd. Not affiliated with any temple. Not for operational use.</small></div>`;
    else if (layout === 'end') body = `<div class="big"><h1>${esc(main)}</h1><h2>${esc(sub)}</h2><small>Simulated crowd. Not affiliated with any temple. Not for operational use.</small></div>`;
    else if (layout === 'phone-left-with-caption') { cls = 'bg'; body = `<div class="side"><p>${esc(main)}</p></div>`; }
    else if (layout === 'side-by-side') { cls = 'bg'; body = main ? `<div class="lower">${esc(main)}</div>` : ''; }
    else body = main ? `<div class="lower">${esc(main)}</div>` : '';
    const html = `<!doctype html><meta charset=utf-8><style>${css}</style><body class="${cls}">${body}`;
    const f = path.join(outdir, '_card.html'); fs.writeFileSync(f, html);
    await pg.goto('file://' + f); await pg.evaluate(() => document.fonts.ready); await pg.waitForTimeout(150);
    const png = path.join(outdir, String(n).padStart(2, '0') + '.png');
    await pg.screenshot({ path: png, omitBackground: cls === 'clear' });
    console.log('card', png, layout);
  }
  await ctx.close();
})();

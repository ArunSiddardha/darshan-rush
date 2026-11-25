// Shared helpers for the card and overlay tools. No Sarvam calls, no network.
const fs = require('fs'), path = require('path');
const { chromium } = require('/Users/arun/automation/vt/node_modules/playwright-core');
const V2 = '/Users/arun/hackathon/festive/repo/demo/v2';
const FONTS = '/Users/arun/hackathon/festive/repo/app/static/fonts';
const BUILD = V2 + '/cards/_work';
const FF = '/opt/homebrew/bin/ffmpeg', FP = '/opt/homebrew/bin/ffprobe';
const LAYOUT = JSON.parse(fs.readFileSync(V2 + '/tools/layout.json', 'utf8'));

const fontsCss = fs.readFileSync('/Users/arun/hackathon/festive/repo/app/static/fonts.css', 'utf8')
  .replace(/url\(fonts\//g, 'url(file://' + FONTS + '/');

const BASE_CSS = `${fontsCss}
:root{--bg:#FBFAF7;--ink:#1B1B26;--ink2:#4E4E60;--grey:#7A7A8C;--saffron:#F26B1D;--saffron-lt:#FFA766;--indigo:#2B2E8C;--line:#E4E1DA}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;overflow:hidden;background:transparent;font-family:'Anek','Helvetica Neue',sans-serif;
  -webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;font-variation-settings:'wdth' 100}
em{font-style:normal;color:var(--saffron)} .on-dark em{color:var(--saffron-lt)}
`;

// "*word*" becomes saffron emphasis, "\n" becomes a line break
function rich(t) {
  return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>').replace(/\\n|\n/g, '<br>');
}

async function launch() {
  const ctx = await chromium.launchPersistentContext('/Users/arun/hackathon/festive/_tools/tmp-profile-cards', {
    executablePath: '/Users/arun/automation/browsers/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    headless: true, viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1,
  });
  return ctx;
}

let counter = 0;
async function openHtml(ctx, body, extraCss = '', bodyClass = '') {
  fs.mkdirSync(BUILD, { recursive: true });
  const f = `${BUILD}/page_${process.pid}_${counter++}.html`;
  fs.writeFileSync(f, `<!doctype html><meta charset=utf-8><style>${BASE_CSS}${extraCss}</style><body class="${bodyClass}">${body}</body>`);
  const page = await ctx.newPage();
  await page.goto('file://' + f);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.fonts].map(f => f.load().catch(() => 0))));
  await page.waitForTimeout(60);
  return { page, file: f };
}
async function shot(page, out, transparent = true) {
  await page.screenshot({ path: out, omitBackground: transparent, clip: { x: 0, y: 0, width: 1920, height: 1080 } });
}
function cleanup(h) { try { fs.unlinkSync(h.file); } catch (e) {} }

// ---- overlay html ----
const SPONSORS = { sarvam: 'Sarvam AI', nudgebee: 'NudgeBee', flagsmith: 'Flagsmith' };
function sponsorHtml(key) {
  const names = key === 'all' ? ['Sarvam AI', 'NudgeBee', 'Flagsmith'] : [SPONSORS[key] || key];
  const txt = names.join('<i>·</i>');
  return `<div class="sp">${txt}</div>`;
}
const SPONSOR_CSS = `.sp{position:absolute;right:${LAYOUT.sponsor.right}px;top:${LAYOUT.sponsor.top}px;height:56px;padding:0 28px;border-radius:28px;
  background:rgba(43,46,140,.88);color:#fff;font-size:28px;font-weight:600;letter-spacing:.01em;display:flex;align-items:center;white-space:pre;
  box-shadow:0 6px 22px -8px rgba(27,27,38,.45)} .sp i{font-style:normal;margin:0 14px;color:#FFA766;font-weight:700}`;

function captionHtml(text) {
  const c = LAYOUT.caption;
  return `<div class="cap"><div class="rule"></div><div class="t">${rich(text)}</div></div>`;
}
function captionCss() {
  const c = LAYOUT.caption;
  return `.cap{position:absolute;left:${c.x}px;width:${c.w}px;top:${c.cy}px;transform:translateY(-50%)}
  .cap .rule{width:96px;height:7px;border-radius:4px;background:var(--saffron);margin-bottom:34px}
  .cap .t{font-size:${c.size}px;font-weight:600;line-height:1.18;color:var(--ink);letter-spacing:-.005em;text-wrap:balance}`;
}
function subtitleHtml(text) { return `<div class="sub"><span>${rich(text)}</span></div>`; }
function subtitleCss(pos) {
  const s = LAYOUT.subtitle, p = s[pos] || s.center;
  return `.sub{position:absolute;left:${p.x}px;width:${p.w}px;bottom:${p.bottom}px;display:flex;justify-content:${p.align || 'center'}}
  .sub span{display:inline-block;max-width:100%;padding:16px 34px 18px;border-radius:20px;background:rgba(17,17,30,.88);color:#fff;
   font-size:${s.size}px;font-weight:500;line-height:1.28;text-align:center;text-wrap:balance;box-shadow:0 10px 30px -12px rgba(0,0,0,.5)}`;
}
function phoneBackHtml() {
  const p = LAYOUT.phone;
  return `<div style="position:absolute;inset:0;background:var(--bg)"></div>
  <div style="position:absolute;left:${p.ox}px;top:${p.oy}px;width:${p.ow}px;height:${p.oh}px;border-radius:${p.r}px;background:#1B1B26;
   box-shadow:0 50px 90px -30px rgba(27,27,38,.45),0 18px 36px -18px rgba(27,27,38,.35)"></div>`;
}
function phoneRingHtml() {
  const p = LAYOUT.phone;
  return `<div style="position:absolute;left:${p.ox}px;top:${p.oy}px;width:${p.ow}px;height:${p.oh}px;border-radius:${p.r}px;border:${p.bezel}px solid #1B1B26;
   box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.10)"></div>`;
}
// split screen: panels with rounded holes (bg colour outside), thin border, optional labels
function splitMaskHtml(opts) {
  const s = LAYOUT.split;
  const panel = (x) => `<div style="position:absolute;left:${x}px;top:${s.y}px;width:${s.w}px;height:${s.h}px;border-radius:${s.r}px;box-shadow:0 0 0 60px var(--bg)"></div>`;
  const border = (x) => `<div style="position:absolute;left:${x}px;top:${s.y}px;width:${s.w}px;height:${s.h}px;border-radius:${s.r}px;border:2px solid #D9D5CC"></div>`;
  const label = (x, t) => t ? `<div class="pl" style="left:${x}px">${rich(t)}</div>` : '';
  return `<div style="position:absolute;inset:0;overflow:hidden">${panel(s.x1)}${panel(s.x2)}</div>${border(s.x1)}${border(s.x2)}${label(s.x1, opts.left)}${label(s.x2, opts.right)}`;
}
const SPLIT_CSS = `.pl{position:absolute;top:${LAYOUT.split.y - 68}px;height:52px;padding:0 26px;border-radius:26px;background:var(--indigo);color:#fff;font-size:28px;font-weight:600;display:flex;align-items:center}`;

// ---- cues ----
function toSec(s) {
  s = String(s).trim(); if (s.includes(':')) { const [m, r] = s.split(':'); return +m * 60 + parseFloat(r); } return parseFloat(s);
}
function parseCues(file) {
  const out = [];
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const l = line.trim(); if (!l || l.startsWith('#')) continue;
    const parts = l.includes('\t') ? l.split('\t') : l.split('|');
    if (parts.length < 3) throw new Error('bad cue line: ' + line);
    out.push({ start: toSec(parts[0]), end: toSec(parts[1]), text: parts.slice(2).join('|').trim() });
  }
  return out;
}
function probeDur(f) {
  const { spawnSync } = require('child_process');
  const r = spawnSync(FP, ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], { encoding: 'utf8' });
  const d = parseFloat(r.stdout); return isFinite(d) ? d : null;
}
function ffmpeg(args) {
  const { spawnSync } = require('child_process');
  const r = spawnSync(FF, ['-y', '-v', 'error', ...args], { encoding: 'utf8' });
  if (r.status !== 0) { console.error(r.stderr); throw new Error('ffmpeg failed'); }
}
module.exports = { V2, BUILD, FF, FP, LAYOUT, BASE_CSS, rich, launch, openHtml, shot, cleanup, sponsorHtml, SPONSOR_CSS, captionHtml, captionCss,
  subtitleHtml, subtitleCss, phoneBackHtml, phoneRingHtml, splitMaskHtml, SPLIT_CSS, parseCues, probeDur, ffmpeg, SPONSORS };

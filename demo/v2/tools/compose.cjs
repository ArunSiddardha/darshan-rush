#!/usr/bin/env node
// node compose.cjs phone|split --src A [--src2 B] --caption "text" [--sponsor sarvam|nudgebee|flagsmith|all] [--subs cues.txt]
//   [--dur 6] [--ss 0] [--fade 0.3] [--out file.mp4] [--png still.png] [--left-label T --right-label T] [--sub-pos right|center]
const fs = require('fs'); const L = require('./lib.cjs');
const O = L.V2 + '/cards/overlays';
const mode = process.argv[2];
const a = {}; const argv = process.argv.slice(3);
for (let i = 0; i < argv.length; i++) { if (argv[i].startsWith('--')) { const k = argv[i].slice(2); a[k] = (argv[i + 1] === undefined || argv[i + 1].startsWith('--')) ? true : argv[++i]; } }
if (!['phone', 'split'].includes(mode) || !a.src || !a.out) { console.error('usage: compose.cjs phone|split --src f [--src2 f] --out f.mp4 [--caption t] [--sponsor k] [--subs f] [--dur s]'); process.exit(2); }
const isImg = (f) => /\.(png|jpe?g|webp)$/i.test(f);
const srcs = [a.src].concat(mode === 'split' ? [a.src2 || a.src] : []);
srcs.forEach(f => { if (!fs.existsSync(f)) { console.error('missing source ' + f); process.exit(2); } });
const ss = parseFloat(a.ss || 0), fade = parseFloat(a.fade === undefined ? 0.3 : a.fade);
let dur = a.dur ? parseFloat(a.dur) : (srcs.every(isImg) ? 6 : Math.max(0.5, Math.min(...srcs.filter(f => !isImg(f)).map(f => L.probeDur(f))) - ss));
const cues = a.subs ? L.parseCues(a.subs) : [];
const subPos = a['sub-pos'] || (mode === 'phone' ? 'right' : 'split');

(async () => {
  const ctx = await L.launch(); const tmp = `${L.BUILD}/compose_${process.pid}`; fs.mkdirSync(tmp, { recursive: true });
  const png = async (name, html, css) => { const h = await L.openHtml(ctx, html, css); const f = `${tmp}/${name}.png`; await L.shot(h.page, f, true); await h.page.close(); L.cleanup(h); return f; };
  const capCss = mode === 'split'
    ? `.cap{position:absolute;left:0;right:0;top:${L.LAYOUT.split.y + L.LAYOUT.split.h + 40}px;text-align:center}.cap .rule{display:none}.cap .t{font-size:58px;font-weight:600;color:var(--ink);line-height:1.15}`
    : L.captionCss();
  const cap = a.caption ? await png('cap', L.captionHtml(a.caption), capCss) : null;
  let splitMask = null;
  if (mode === 'split') splitMask = await png('mask', L.splitMaskHtml({ left: a['left-label'], right: a['right-label'] }), L.SPLIT_CSS);
  const subFiles = [];
  for (let i = 0; i < cues.length; i++) subFiles.push(await png('sub' + i, L.subtitleHtml(cues[i].text), L.subtitleCss(subPos)));
  await ctx.close();

  const P = L.LAYOUT.phone, S = L.LAYOUT.split;
  const inp = []; const fc = []; let n = 0;
  const addLoop = (f) => { inp.push('-loop', '1', '-framerate', '30', '-t', String(dur), '-i', f); return n++; };
  const addSrc = (f) => { if (isImg(f)) inp.push('-loop', '1', '-framerate', '30', '-t', String(dur), '-i', f); else inp.push('-ss', String(ss), '-t', String(dur), '-i', f); return n++; };
  let last;
  const fitPad = (idx, w, h, bg, tag) => fc.push(`[${idx}:v]fps=30,scale=${w}:${h}:force_original_aspect_ratio=decrease:flags=lanczos,pad=${w}:${h}:(ow-iw)/2:(oh-ih)/2:color=${bg},setsar=1[${tag}]`);
  if (mode === 'phone') {
    const back = addLoop(O + '/phone_back.png'), src = addSrc(srcs[0]), ring = addLoop(O + '/phone_ring.png');
    fitPad(src, P.sw, P.sh, '0xFFFFFF', 's');
    fc.push(`[${back}:v][s]overlay=${P.sx}:${P.sy}:shortest=1[b1]`, `[b1][${ring}:v]overlay=0:0[b2]`); last = 'b2';
  } else {
    const bg = addLoop(O + '/phone_back.png'); // bg only used for its colour; replaced below
    fc.push(`[${bg}:v]drawbox=x=0:y=0:w=1920:h=1080:color=0xFBFAF7:t=fill[bgc]`);
    const sa = addSrc(srcs[0]), sb = addSrc(srcs[1]);
    const mk = (idx, x, tag) => { fitPad(idx, S.w, S.h, '0xF1EFEA', tag + 'f'); };
    mk(sa, S.x1, 'sa'); mk(sb, S.x2, 'sb');
    fc.push(`[bgc][saf]overlay=${S.x1}:${S.y}:shortest=1[x1]`, `[x1][sbf]overlay=${S.x2}:${S.y}:shortest=1[x2]`);
    const m = addLoop(splitMask); fc.push(`[x2][${m}:v]overlay=0:0[x3]`); last = 'x3';
  }
  const rise = (t0, d) => `y='14*pow(1-min(1\\,max(0\\,(t-${t0})/${d}))\\,3)'`;
  if (cap) { const c = addLoop(cap); fc.push(`[${c}:v]format=rgba,fade=t=in:st=0.35:d=0.7:alpha=1[cp]`, `[${last}][cp]overlay=x=0:${rise(0.35, 0.7)}:eval=frame[c1]`); last = 'c1'; }
  if (a.sponsor && a.sponsor !== 'none') { const s = addLoop(`${O}/sponsor_${a.sponsor}.png`); fc.push(`[${s}:v]format=rgba,fade=t=in:st=0.5:d=0.5:alpha=1[sp]`, `[${last}][sp]overlay=0:0[c2]`); last = 'c2'; }
  subFiles.forEach((f, i) => { const s = addLoop(f); const c = cues[i]; fc.push(`[${last}][${s}:v]overlay=0:0:enable='between(t\\,${c.start}\\,${c.end})'[u${i}]`); last = `u${i}`; });
  let post = `[${last}]format=yuv420p`;
  if (fade > 0) post += `,fade=t=in:st=0:d=${fade},fade=t=out:st=${Math.max(0, dur - fade)}:d=${fade}`;
  fc.push(post + '[v]');
  L.ffmpeg([...inp, '-filter_complex', fc.join(';'), '-map', '[v]', '-t', String(dur), '-r', '30', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', a.out]);
  if (a.png) L.ffmpeg(['-ss', String(Math.min(dur - 0.1, a['png-at'] ? parseFloat(a['png-at']) : 2.5)), '-i', a.out, '-frames:v', '1', a.png]);
  console.log(`${a.out}  ${dur}s`);
})().catch(e => { console.error(e); process.exit(1); });

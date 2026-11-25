// Real browser mic test. Usage: node browser_mic.cjs <base url> <pilgrim wav> <volunteer wav>
// Headless Chrome for Testing with a fake microphone that plays a wav file. Needs INCIDENT_TOKEN in env.
const { chromium } = require('/Users/arun/automation/vt/node_modules/playwright-core');
const [base, pwav, vwav] = process.argv.slice(2);
const TOK = process.env.INCIDENT_TOKEN;
const fs = require('fs');
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function run(wav, fn) {
  const ctx = await chromium.launchPersistentContext('/Users/arun/hackathon/festive/_tools/tmp-profile2', {
    executablePath: '/Users/arun/automation/browsers/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
    headless: true, viewport: { width: 390, height: 844 }, permissions: ['microphone'],
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', `--use-file-for-fake-audio-capture=${wav}`, '--autoplay-policy=user-gesture-required']
  });
  // Chrome's fake microphone hangs getUserMedia in this session (likely the macOS microphone permission prompt that
  // nobody can click), so the page's getUserMedia is replaced by a WebAudio stream that plays the wav. The real
  // MediaRecorder, upload, server and playback code paths still run.
  const b64 = fs.readFileSync(wav).toString('base64');
  await ctx.addInitScript(() => {
    const of = window.fetch; window.__uploads = [];
    window.fetch = (u, o) => { try { const a = o && o.body && o.body.get && o.body.get('audio'); if (a) window.__uploads.push({ url: String(u), bytes: a.size, type: a.type, name: a.name }); } catch (e) {} return of(u, o); };
  });
  await ctx.addInitScript(b => {
    navigator.mediaDevices.getUserMedia = async () => {
      const ac = new AudioContext(); await ac.resume();
      const buf = await ac.decodeAudioData(Uint8Array.from(atob(b), c => c.charCodeAt(0)).buffer);
      const dest = ac.createMediaStreamDestination(); const src = ac.createBufferSource(); src.buffer = buf; src.connect(dest); src.start();
      return dest.stream;
    };
  }, b64);
  try { return await fn(ctx); } finally { await ctx.close(); }
}
(async () => {
  const out = {};
  out.pilgrim = await run(pwav, async ctx => {
    const p = await ctx.newPage(); const logs = []; const posts = [];
    p.on('console', m => logs.push(m.type() + ': ' + m.text().slice(0, 150)));
    p.on('request', r => { if (r.url().includes('/api/directions') && r.method() === 'POST') posts.push({ ct: r.headers()['content-type']?.slice(0, 40), size: (r.postDataBuffer() || []).length }); });
    const respP = p.waitForResponse(r => r.url().includes('/api/directions') && r.request().method() === 'POST', { timeout: 40000 }); respP.catch(() => {});
    await p.goto(base + '/', { waitUntil: 'domcontentloaded' }); await sleep(1500);
    await p.click('#mic', { force: true }); await sleep(3500); await p.click('#mic', { force: true });
    const resp = await respP; const j = await resp.json();
    await sleep(2500);
    // Credits may be out: also check that the reply player really plays a real Sarvam wav after a mic tap (autoplay policy).
    const SAMPLE = process.env.SAMPLE_WAV ? fs.readFileSync(process.env.SAMPLE_WAV).toString('base64') : null;
    if (!j.audio_base64 && SAMPLE) { await p.evaluate(b => play(b), SAMPLE); await sleep(1500); }
    const st = await p.evaluate(() => { const a = document.querySelector('#player'); return { srcLen: (a.src || '').length, paused: a.paused, ended: a.ended, t: a.currentTime, dur: a.duration, secure: window.isSecureContext, hasMR: typeof MediaRecorder !== 'undefined' }; });
    await p.screenshot({ path: '/Users/arun/hackathon/festive/repo/voice_tests/out/browser_pilgrim.png' });
    return { status: resp.status(), transcript: j.transcript, intent: j.intent, lang: j.lang, reply: j.reply_text, hasAudio: !!j.audio_base64, notice: j.notice, lat: j.latency, posts, audio: st, errors: logs.filter(l => l.startsWith('error')), uploads: await p.evaluate(() => window.__uploads) };
  });
  const H = { 'X-Incident-Token': TOK, 'Content-Type': 'application/json' };
  await fetch(base + '/api/volunteer/reset', { method: 'POST', headers: H });
  await fetch(base + '/api/incident?force=1', { method: 'POST', headers: H, body: JSON.stringify({ summary: 'Booking pod ran out of memory', root_cause: 'Map images held in memory', proposed_fix: 'Switch to lite map and staggered slots', event_id: 'bm-' + Date.now() }) });
  out.volunteer = await run(vwav, async ctx => {
    const p = await ctx.newPage(); const logs = [];
    p.on('console', m => logs.push(m.type() + ': ' + m.text().slice(0, 150)));
    await p.goto(base + '/volunteer', { waitUntil: 'domcontentloaded' }); await sleep(3500);
    const q = await p.evaluate(() => { const a = document.querySelector('#player'); return { src: a.src.slice(0, 80), paused: a.paused, t: a.currentTime }; });
    const respP = p.waitForResponse(r => r.url().includes('/api/volunteer/reply'), { timeout: 40000 }); respP.catch(() => {});
    await p.click('#mic', { force: true }); await sleep(3000); await p.click('#mic', { force: true });
    const j = await (await respP).json(); await sleep(1500);
    const hear = await p.evaluate(() => document.querySelector('#hear').textContent);
    await p.screenshot({ path: '/Users/arun/hackathon/festive/repo/voice_tests/out/browser_volunteer.png' });
    return { questionAudio: q, reply: j, hear, uploads: await p.evaluate(() => window.__uploads), errors: logs.filter(l => l.startsWith('error')) };
  });
  console.log(JSON.stringify(out, null, 1));
})().catch(e => { console.error('ERR', e); process.exit(1); });

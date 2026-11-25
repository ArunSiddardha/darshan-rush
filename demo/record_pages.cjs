// Record our own pages with a headless Chrome for Testing (own temp profile, never your daily browser).
// usage: node record_pages.cjs <seconds> [page ...]      pages: judge graph pilgrim volunteer kube   (default: the first four)
// env:   BASE (default http://127.0.0.1:8088)   RUSH_TOKEN (for the judge page; read from repo/.env if unset, never printed)
//        page 'kube' renders `kubectl get pods` (context kind-nb, namespace darshan) once a second as a terminal look-alike, labelled as such.
//        PRESS=1  on the judge page also clicks "Cause the rush" after 3 s (only use when you want a real rush)
// Output: /Users/arun/hackathon/festive/repo/demo/raw/<page>-<WxH>.webm   (video is written when the context closes)
const fs = require('fs'), path = require('path');
const { chromium } = require('/Users/arun/automation/vt/node_modules/playwright-core');
const CHROME = '/Users/arun/automation/browsers/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const PROFILE = '/Users/arun/hackathon/festive/_tools/tmp-profile-demo';
const OUT = '/Users/arun/hackathon/festive/repo/demo/raw';
const BASE = process.env.BASE || 'http://127.0.0.1:8088';
const secs = Number(process.argv[2] || 20);
const want = process.argv.slice(3);
function token() {
  if (process.env.RUSH_TOKEN) return process.env.RUSH_TOKEN;
  try { const m = fs.readFileSync('/Users/arun/hackathon/festive/repo/.env', 'utf8').match(/^INCIDENT_TOKEN=(.*)$/m); return m ? m[1].trim() : ''; } catch (e) { return ''; }
}
const KUBECTL = '/opt/homebrew/bin/kubectl';
const kubeText = () => { try { return require('child_process').execFileSync(KUBECTL, ['--context', 'kind-nb', '-n', 'darshan', 'get', 'pods'], { timeout: 4000 }).toString(); } catch (e) { return 'kubectl not reachable: ' + String(e.message).split('\n')[0]; } };
const KUBE_HTML = '<body style="margin:0;background:#101418;color:#d7e0e8;font:22px/1.5 Menlo,monospace;padding:28px"><div style="color:#7fd1b9">$ kubectl --context kind-nb -n darshan get pods   <span style="color:#8a97a3">(live, refreshed every second)</span></div><pre id=o style="margin-top:18px;font:inherit"></pre>';
const PAGES = {
  kube:      { path: () => null, size: { width: 1280, height: 720 } },
  judge:     { path: () => '/judge?t=' + encodeURIComponent(token()), size: { width: 1280, height: 720 } },
  graph:     { path: () => '/graph', size: { width: 1280, height: 720 } },
  pilgrim:   { path: () => '/', size: { width: 390, height: 844 }, phone: true },
  volunteer: { path: () => '/volunteer', size: { width: 390, height: 844 }, phone: true },
};
(async () => {
  const names = want.length ? want : ['judge', 'graph', 'pilgrim', 'volunteer'];
  fs.mkdirSync(OUT, { recursive: true }); fs.mkdirSync(PROFILE, { recursive: true });
  for (const n of names) {
    const p = PAGES[n]; if (!p) { console.log('unknown page', n); continue; }
    const tmp = path.join(OUT, '_tmp_' + n); fs.mkdirSync(tmp, { recursive: true });
    const ctx = await chromium.launchPersistentContext(PROFILE, {
      headless: true, executablePath: CHROME,
      viewport: p.size, recordVideo: { dir: tmp, size: p.size },
      deviceScaleFactor: 1, isMobile: !!p.phone, hasTouch: !!p.phone, permissions: ['microphone'],
    });
    const pg = await ctx.newPage();
    pg.on('pageerror', e => console.log('PAGEERR', n, e.message));
    if (n === 'kube') { await pg.setContent(KUBE_HTML); for (let i = 0; i < secs; i++) { const t = kubeText(); await pg.evaluate(x => { document.getElementById('o').textContent = x; }, t); await pg.waitForTimeout(1000); } }
    else await pg.goto(BASE + p.path(), { waitUntil: 'domcontentloaded' }).catch(e => console.log('goto failed', n, e.message));
    await pg.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
    if (n === 'kube') {}
    else if (n === 'judge' && process.env.PRESS === '1') { await pg.waitForTimeout(3000); await pg.click('#rush').catch(() => {}); await pg.waitForTimeout(Math.max(0, secs * 1000 - 3000)); }
    else await pg.waitForTimeout(secs * 1000);
    const vid = pg.video();
    await ctx.close();
    const dest = path.join(OUT, `${n}-${p.size.width}x${p.size.height}.webm`);
    await vid.saveAs(dest).catch(async () => { fs.copyFileSync(await vid.path(), dest); });
    try { fs.unlinkSync(await vid.path()); fs.rmdirSync(tmp); } catch (e) {}
    console.log('recorded', dest, secs + 's');
  }
})();

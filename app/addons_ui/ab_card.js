/* A/B result card: reads GET /api/experiment (flag voice_directions, metric reached_gate).
   Shows exposed, reached and rate per variant. Labelled test traffic. Only global: DarshanAddons.abCard. */
(function () {
  var NS = (window.DarshanAddons = window.DarshanAddons || {});
  var LABEL = { voice: 'Voice', map: 'Map' };
  function text(tag, cls, s) { var n = document.createElement(tag); if (cls) n.className = cls; n.textContent = s; return n; }
  function mount(el) {
    var rows = el.querySelector('[data-ab-rows]'), sub = el.querySelector('[data-ab-sub]'), foot = el.querySelector('[data-ab-foot]');
    function render(d) {
      var v = d.variants || {}, names = Object.keys(v), best = -1, lead = null;
      names.forEach(function (n) { var r = v[n].rate; if (r !== null && r !== undefined && r > best) { best = r; lead = n; } });
      rows.textContent = '';
      names.forEach(function (n) {
        var x = v[n], row = document.createElement('div');
        row.className = 'ab-row'; if (n === lead && names.length > 1) row.setAttribute('data-lead', '1');
        row.appendChild(text('div', 'ab-name', LABEL[n] || n));
        var bar = document.createElement('div'), fill = document.createElement('div');
        bar.className = 'ab-bar'; fill.className = 'ab-fill';
        fill.style.width = (x.rate ? Math.round(x.rate * 100) : 0) + '%'; bar.appendChild(fill); row.appendChild(bar);
        var pct = x.rate === null || x.rate === undefined ? 'no data yet' : Math.round(x.rate * 100) + '%';
        row.appendChild(text('div', 'ab-num', (x.reached_gate || 0) + ' of ' + (x.exposed || 0) + ' reached - ' + pct));
        rows.appendChild(row);
      });
      sub.textContent = 'Hypothesis: voice directions get more pilgrims to the gate. Metric: ' + (d.metric || 'reached_gate') + '.';
      foot.textContent = 'Test traffic, small sample. Counts from ' + (d.source === 'flagsmith' ? 'the app, with Flagsmith assigning variants.' : 'the app (local counters).');
    }
    function load() {
      fetch('/api/experiment').then(function (r) { return r.json(); }).then(render).catch(function () {
        sub.textContent = 'Experiment results unavailable.'; });
    }
    load();
    var s = parseInt(el.dataset.refresh || '5', 10);
    if (s > 0) setInterval(function () { if (!document.hidden && el.isConnected) load(); }, s * 1000);
  }
  NS.abCard = { mount: mount };
  function boot() { document.querySelectorAll('[data-ab-card]').forEach(function (el) { if (!el.__ab) { el.__ab = 1; mount(el); } }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();

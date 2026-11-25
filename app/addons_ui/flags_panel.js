/* "Flagsmith decides" panel: reads GET /api/flags/decisions. No globals except DarshanAddons.flagsPanel.
   Include once after the HTML fragment. Auto-mounts every [data-flags-panel]. */
(function () {
  var NS = (window.DarshanAddons = window.DarshanAddons || {});
  function uidOf(el) {
    if (el.dataset.uid) return el.dataset.uid;
    try {
      var k = 'darshan_uid', v = localStorage.getItem(k) || localStorage.getItem('uid');
      if (!v) { v = 'v' + Math.random().toString(36).slice(2, 10); localStorage.setItem(k, v); }
      return v;
    } catch (e) { return 'anon'; }
  }
  function text(tag, cls, s) { var n = document.createElement(tag); if (cls) n.className = cls; n.textContent = s; return n; }
  function mount(el) {
    var rows = el.querySelector('[data-fp-rows]'), sub = el.querySelector('[data-fp-sub]'), msg = el.querySelector('[data-fp-msg]');
    var state = { lang: el.dataset.lang || document.documentElement.lang || 'en', age65: el.dataset.age65 === 'true', timer: null };
    function render(d) {
      rows.textContent = '';
      (d.flags || []).forEach(function (f) {
        var tr = document.createElement('tr');
        tr.appendChild(text('td', 'fp-flag', f.flag));
        var v = f.value === null || f.value === '' || f.value === undefined ? (f.enabled ? 'on' : 'off') : (f.enabled ? '' : 'off: ') + f.value;
        tr.appendChild(text('td', 'fp-val' + (f.enabled ? '' : ' fp-off'), String(v)));
        var why = document.createElement('td');
        why.appendChild(text('span', 'fp-tag ' + (f.kind || ''), f.kind || ''));
        why.appendChild(document.createTextNode(f.why || ''));
        tr.appendChild(why);
        rows.appendChild(tr);
      });
      var t = d.traits || {};
      sub.textContent = 'Visitor ' + d.uid + ' - language ' + t.language + ', age 65+ ' + (t.age_65_plus ? 'yes' : 'no');
      msg.hidden = !d.message; msg.textContent = d.message || '';
    }
    function load() {
      var q = 'uid=' + encodeURIComponent(uidOf(el)) + '&lang=' + encodeURIComponent(state.lang) + '&age65=' + state.age65;
      fetch('/api/flags/decisions?' + q).then(function (r) { return r.json(); }).then(render).catch(function () {
        sub.textContent = 'Flag decisions unavailable.'; msg.hidden = false; msg.textContent = 'Could not reach the server.';
      });
    }
    el.addEventListener('flags:refresh', function (e) {
      var d = e.detail || {};
      if (d.lang) state.lang = d.lang;
      if (typeof d.age65 === 'boolean') state.age65 = d.age65;
      load();
    });
    load();
    var s = parseInt(el.dataset.refresh || '5', 10);
    if (s > 0) state.timer = setInterval(function () { if (!document.hidden && el.isConnected) load(); }, s * 1000);
  }
  NS.flagsPanel = { mount: mount };
  function boot() { document.querySelectorAll('[data-flags-panel]').forEach(function (el) { if (!el.__fp) { el.__fp = 1; mount(el); } }); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();

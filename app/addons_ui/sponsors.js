/* Sponsors page. Reads GET /api/sponsors/status every 3 s and fills the three cards and the chain. No globals. */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var NA = '<span class="sp-na">not available</span>';
  var LANGN = { ml: 'Malayalam', ta: 'Tamil', te: 'Telugu', kn: 'Kannada', hi: 'Hindi', en: 'English' };
  var TYPEN = { stt: 'speech to text', translate: 'translation', tts: 'text to speech', chat: 'chat' };

  function clock(t) { if (!t) return ''; var d = new Date(t * 1000); return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
  function ago(t, now) { if (!t) return ''; var s = Math.max(0, Math.round((now || Date.now() / 1000) - t)); if (s < 90) return s + ' s ago'; if (s < 5400) return Math.round(s / 60) + ' min ago'; return Math.round(s / 3600) + ' h ago'; }
  function when(t, now) { return t ? clock(t) + ' (' + ago(t, now) + ')' : ''; }
  function lang(c) { return c ? (LANGN[c] || c) : ''; }
  function row(k, v, sub) { return '<div><dt>' + esc(k) + '</dt><dd>' + (v == null || v === '' ? NA : v) + (sub ? '<span class="sub">' + sub + '</span>' : '') + '</dd></div>'; }
  function dot(state) {
    var m = { working: 'Working', waiting: 'Waiting', problem: 'Problem' };
    var s = m[state] ? state : 'waiting';
    return '<span class="sp-dot ' + s + '" role="status"><i></i>' + m[s] + '</span>';
  }
  function head(id, name, state) { return '<div class="sp-head"><h2 id="h-' + id + '">' + name + '</h2>' + dot(state) + '</div>'; }
  function list(a) { return '<ul>' + a.map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ul>'; }
  function links(a) { return '<div class="sp-links">' + a.map(function (l) { return '<a href="' + l[1] + '">' + esc(l[0]) + '</a>'; }).join('') + '</div>'; }
  function code(a) { return '<p class="sp-code">' + a.map(esc).join('<br>') + '</p>'; }
  function keep(el, html) {
    /* do not collapse an open expander when the data refreshes */
    var open = Array.prototype.map.call(el.querySelectorAll('details'), function (d) { return d.open; });
    el.innerHTML = html;
    Array.prototype.forEach.call(el.querySelectorAll('details'), function (d, i) { if (open[i]) d.open = true; });
  }

  function chain(c) {
    if (!c || !c.length) { $('#sp-chain').innerHTML = ''; return; }
    $('#sp-chain').innerHTML = c.map(function (n) {
      return '<li class="' + (n.on ? 'on' : n.next ? 'next' : '') + '"' + (n.on ? ' aria-current="step"' : '') + '>' + esc(n.label) + '<small>' + esc(n.owner) + '</small></li>';
    }).join('');
  }

  function sarvam(s, now) {
    var el = $('#sp-sarvam');
    if (!s || s.available === false) { keep(el, head('sarvam', 'Sarvam AI', 'waiting') + '<p class="sp-does">' + NA + '</p>'); return; }
    var calls = Object.keys(s.calls || {}).map(function (k) { return (TYPEN[k] || k) + ' ' + s.calls[k]; }).join(', ');
    var med = Object.keys(s.median_ms || {}).map(function (k) { return (TYPEN[k] || k) + ' ' + s.median_ms[k] + ' ms'; }).join(', ');
    var heard = s.last_heard, said = s.last_said, ks = s.key_slot;
    keep(el,
      head('sarvam', 'Sarvam AI', s.state) +
      '<p class="sp-does">What it does here: it listens to the pilgrim and the volunteer in their own language, translates, and speaks the answer back.</p>' +
      '<h3>Live</h3><dl class="sp-facts">' +
      row('Calls this session', calls ? esc(calls) : (s.calls_total === 0 ? 'none yet' : null), s.calls_total ? esc(s.calls_total) + ' in total' : '') +
      row('Languages heard', (s.languages_heard || []).length ? esc(s.languages_heard.map(lang).join(', ')) : 'none yet') +
      row('Last heard', heard ? '&ldquo;' + esc(heard.text) + '&rdquo;' : 'nothing yet', heard ? esc([lang(heard.lang), when(heard.t, now), heard.from].filter(Boolean).join(' · ')) : '') +
      row('Last said', said ? '&ldquo;' + esc(said.text) + '&rdquo;' : 'nothing yet', said ? esc([lang(said.lang), when(said.t, now), said.from].filter(Boolean).join(' · ')) : '') +
      row('Median time', med ? esc(med) : 'no answered calls yet') +
      row('Key in use', ks ? 'slot ' + esc(ks.in_use) + ' of ' + esc(ks.of) : null, ks && ks.cooling && ks.cooling.length ? 'slot ' + esc(ks.cooling.join(', ')) + ' is resting' : '') +
      row('Credits', esc(s.credits)) +
      '</dl>' +
      '<h3>Where it is used</h3>' + list([
        'The pilgrim speaks to book, and hears the slot read back',
        'The volunteer is asked in Malayalam and answers yes by voice',
        'Walk-in booking: the volunteer speaks for a pilgrim without a phone',
        'A photo is read aloud, and a booking site is checked, in the pilgrim&rsquo;s language',
        'Live conversation: hands-free questions about gates and waits']) +
      '<h3>Where in the code</h3>' + code(['app/sarvam.py', 'app/sarvam_keys.py', 'app/volunteer.py', 'app/directions.py', 'app/addons_read.py', 'app/addons_live.py']) +
      links([['See it: pilgrim page', '/'], ['See it: volunteer asked by voice', '/volunteer']]));
  }

  function flagsmith(f, now) {
    var el = $('#sp-flagsmith');
    if (!f || f.available === false) { keep(el, head('flagsmith', 'Flagsmith', 'waiting') + '<p class="sp-does">' + NA + '</p>'); return; }
    var flags = (f.flags || []).map(function (x) {
      var ch = x.changed_at ? 'Last changed ' + when(x.changed_at, now) + ' by ' + esc(x.changed_by) : (x.available === false ? '' : 'Last change: not available');
      return '<div class="sp-flag"><div class="r1"><b>' + esc(x.flag) + '</b><span class="val">' + esc(x.value) + '</span></div>' +
        '<div class="why">Why: ' + esc(x.reason) + '</div>' + (ch ? '<div class="when">' + ch + '</div>' : '') +
        (x.proof ? '<div class="proof">' + esc(x.proof) + '</div>' : '') + '</div>';
    }).join('');
    var ex = f.experiment && f.experiment.variants, abRow;
    if (ex) {
      var v = ex.voice || {}, m = ex.map || {};
      abRow = row('A/B test', 'voice ' + (v.reached_gate || 0) + ' of ' + (v.exposed || 0) + ' reached the gate &middot; map ' + (m.reached_gate || 0) + ' of ' + (m.exposed || 0), esc('metric reached_gate' + (f.experiment.source === 'local' ? ', counted in this app' : '')));
    } else abRow = row('A/B test', null);
    var pct = f.rollout && f.rollout.percent != null ? esc(f.rollout.percent) + '% of pilgrims on voice_agent_v2' : null;
    var aud = '';
    if (f.audit && f.audit.rows) {
      aud = f.audit.rows.length ? list(f.audit.rows.slice(0, 3).map(function (r) { return esc(r.log) + ' &middot; ' + esc(r.by) + ' &middot; ' + clock(r.t); })) : '<p class="small muted">Audit log has no entries yet. The change history above comes from each flag&rsquo;s version list.</p>';
    }
    keep(el,
      head('flagsmith', 'Flagsmith', f.state) +
      '<p class="sp-does">What it does here: it holds the switches that change the app while it runs, with no redeploy: the rush fix, voice-first for elders, wording, the A/B test and the staged rollout.</p>' +
      (f.note ? '<p class="small" style="margin-top:12px;color:var(--bad)">' + esc(f.note) + '</p>' : '') +
      '<h3>Live flags</h3>' + flags +
      '<h3>Live numbers</h3><dl class="sp-facts">' + abRow + row('Rollout', pct) + '</dl>' +
      (aud ? '<h3>Audit log</h3>' + aud : '') +
      (f.admin_note ? '<p class="small muted" style="margin-top:8px">' + esc(f.admin_note) + '</p>' : '') +
      '<h3>Where it is used</h3>' + list([
        'The rush switch: map_mode and slot_mode, flipped after the volunteer&rsquo;s yes',
        'Elders get the voice-first screen (segment: age 65+)',
        'Wording changes without a redeploy (ui_copy)',
        'The A/B test: voice directions or map directions',
        'The staged rollout of voice_agent_v2: 10, 50, 100 percent']) +
      '<h3>Where in the code</h3>' + code(['app/flags.py', 'app/addons_flags.py', 'scripts/flagsmith_setup.py', 'scripts/rollout.sh', 'nudgebee/ (the two HTTP tasks)']) +
      links([['See it: judge page', '/judge'], ['See it: decisions JSON', '/api/flags/decisions?uid=sponsors&age65=true']]));
  }

  function nudgebee(n, now) {
    var el = $('#sp-nudgebee');
    if (!n || n.available === false) { keep(el, head('nudgebee', 'NudgeBee', 'waiting') + '<p class="sp-does">' + NA + '</p>'); return; }
    var lc = n.last_crash;
    var steps = (n.approval || []).map(function (a) {
      return '<li class="' + (a.done ? 'done' : '') + '">' + esc(a.step) + '<span class="t">' + (a.t ? clock(a.t) : '') + '</span>' + (a.inferred && a.done ? '<span class="inf" style="flex-basis:100%;padding-left:20px">seen when the flags flipped</span>' : '') + '</li>';
    }).join('');
    var rc = n.root_cause ? '<details><summary>Read what NudgeBee wrote</summary><pre>' + esc(n.root_cause) + '</pre></details>' : '';
    keep(el,
      head('nudgebee', 'NudgeBee', n.state) +
      '<p class="sp-does">What it does here: it watches the cluster, finds why the booking pod crashed, and runs the approved fix that flips the flags.</p>' +
      '<h3>Live</h3><dl class="sp-facts">' +
      row('Agent', esc(n.agent), 'The agent pods run in the cluster and are not visible from inside our pod, so this shows what our app has received.') +
      row('Last crash reported', lc ? when(lc.t, now) : 'none yet', lc ? 'pod ' + esc(lc.pod) + (lc.sent === false ? ' (not delivered)' : '') : '') +
      row('Root cause', n.root_cause_short ? esc(n.root_cause_short) : 'not received yet', rc) +
      row('In plain words', n.summary ? esc(n.summary) : 'not received yet') +
      row('Crash to cause', n.crash_to_cause_s != null ? esc(n.crash_to_cause_s) + ' s' : 'not measured yet') +
      row('Yes to recovery', n.yes_to_recovery_s != null ? esc(n.yes_to_recovery_s) + ' s' : 'not measured yet') +
      '</dl>' +
      '<h3>Approval</h3><ul class="sp-steps">' + steps + '</ul>' +
      (n.webhook_error ? '<p class="small" style="color:var(--bad);margin-top:8px">Approval webhook problem: ' + esc(n.webhook_error) + '</p>' : '') +
      '<h3>Automations</h3><p class="sp-code">' + (n.automations || []).map(esc).join('<br>') + '</p>' +
      (n.assistant_guard ? '<h3>Assistant health guard</h3><p>' + esc(n.assistant_guard.guard.threshold) + ' sends one alert to darshan-assistant-degraded (10 minute cool-down). Last run: ' +
        esc(n.assistant_guard.guard.last_post ? new Date(n.assistant_guard.guard.last_post * 1000).toLocaleTimeString() + ', ' + (n.assistant_guard.guard.last_result || '') : 'not triggered yet') + '.' +
        (n.assistant_guard.fallback_line ? ' <b>' + esc(n.assistant_guard.fallback_line) + '</b>' : '') + '</p>' : '') +
      '<h3>Where it is used</h3>' + list([
        'Finding the cause when the booking pod runs out of memory',
        'The approval-gated fix: after the volunteer&rsquo;s yes, a duty officer approves and NudgeBee flips the Flagsmith flags',
        'Verifying recovery: the app watches the flags and the booking come back']) +
      '<h3>Where in the code</h3>' + code(['app/crash.py', 'app/volunteer.py', 'nudgebee/README.md', 'nudgebee/ (workflow YAML)']) +
      links([['See it: volunteer page', '/volunteer'], ['See it: recovery graph', '/static/graph.html']]));
  }

  var fails = 0;
  function tick() {
    fetch('/api/sponsors/status', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
      fails = 0;
      var now = d.now || Date.now() / 1000;
      chain(d.chain);
      sarvam(d.sarvam, now); flagsmith(d.flagsmith, now); nudgebee(d.nudgebee, now);
      if (d.simulated_note) $('#sp-sim').textContent = 'What is simulated: ' + d.simulated_note.replace(/^Simulated: /, '');
      $('#sp-updated').textContent = 'Updated ' + clock(now);
    }).catch(function () {
      fails++;
      $('#sp-updated').textContent = fails > 1 ? 'Cannot reach the app. Retrying.' : 'Updating';
    });
  }
  tick(); setInterval(tick, 3000);
})();

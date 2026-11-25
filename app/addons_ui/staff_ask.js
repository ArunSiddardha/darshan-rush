/* Staff "Ask anything": tap, speak, tap again; hear and read the answer. No global side effects except window.StaffAsk.
   StaffAsk.init(root, {endpoint:'/api/staff/ask', lang:'ml' | () => 'ml', staffId:'v1', maxMs:12000}) */
(function () {
  'use strict';
  function q(root, k) { return root.querySelector('[data-sa="' + k + '"]'); }
  function init(root, opts) {
    opts = opts || {};
    var ep = opts.endpoint || '/api/staff/ask', maxMs = opts.maxMs || 12000, staffId = opts.staffId || 'staff';
    var lang = function () { return typeof opts.lang === 'function' ? opts.lang() : (opts.lang || 'en'); };
    var talk = q(root, 'talk'), label = q(root, 'talklabel'), you = q(root, 'you'), reply = q(root, 'reply'), note = q(root, 'note'),
        conf = q(root, 'confirm'), audio = q(root, 'audio'), eg = q(root, 'eg'), form = q(root, 'form'), txt = q(root, 'text');
    var rec = null, chunks = [], stream = null, timer = null, egList = [], egI = 0;

    function state(s) { root.dataset.state = s; label.textContent = s === 'recording' ? 'Tap to send' : s === 'thinking' ? 'Thinking...' : 'Ask anything'; }
    function showErr(m) { note.textContent = m || ''; }
    function cycle() { if (egList.length) { eg.textContent = 'Try: ' + egList[egI++ % egList.length]; } }
    fetch('/api/staff/examples?lang=' + encodeURIComponent(lang())).then(function (r) { return r.json(); })
      .then(function (j) { egList = j.examples || []; cycle(); setInterval(cycle, 4000); }).catch(function () {});

    function render(j) {
      you.textContent = j.transcript || '';
      reply.textContent = j.reply_text || '';
      showErr(j.notice || '');
      conf.hidden = !j.needs_confirmation;
      if (j.audio_base64) { audio.src = 'data:audio/wav;base64,' + j.audio_base64; audio.play().catch(function () {}); }
      state('idle');
    }
    function send(body) {
      state('thinking'); showErr('');
      return fetch(ep, { method: 'POST', body: body.json ? JSON.stringify(body.json) : body.form, headers: body.json ? { 'Content-Type': 'application/json' } : {} })
        .then(function (r) { return r.json(); }).then(render)
        .catch(function () { state('idle'); showErr('Could not reach the server. Type your question instead.'); });
    }
    function sendJson(extra) { return send({ json: Object.assign({ lang: lang(), staff_id: staffId }, extra) }); }

    function stop() { clearTimeout(timer); if (rec && rec.state !== 'inactive') rec.stop(); }
    function start() {
      if (!navigator.mediaDevices || !window.MediaRecorder) { showErr('This browser cannot record. Type your question instead.'); return; }
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
        stream = s; chunks = []; rec = new MediaRecorder(s);
        rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
        rec.onstop = function () {
          stream.getTracks().forEach(function (t) { t.stop(); });
          var type = (rec.mimeType || 'audio/webm').split(';')[0], blob = new Blob(chunks, { type: type });
          if (blob.size < 1500) { state('idle'); showErr('I did not hear anything. Tap and try again.'); return; }
          var fd = new FormData(); fd.append('audio', blob, 'ask.' + (type.indexOf('mp4') >= 0 ? 'm4a' : 'webm'));
          fd.append('lang', lang()); fd.append('staff_id', staffId); send({ form: fd });
        };
        rec.start(); state('recording'); showErr(''); timer = setTimeout(stop, maxMs);
      }).catch(function () { showErr('Microphone not allowed. Type your question instead.'); });
    }
    talk.addEventListener('click', function () { if (root.dataset.state === 'recording') stop(); else if (root.dataset.state !== 'thinking') start(); });
    q(root, 'yes').addEventListener('click', function () { conf.hidden = true; sendJson({ text: 'yes', confirm: 'yes' }); });
    q(root, 'no').addEventListener('click', function () { conf.hidden = true; sendJson({ text: 'no', confirm: 'no' }); });
    form.addEventListener('submit', function (e) { e.preventDefault(); var v = txt.value.trim(); if (v) { txt.value = ''; sendJson({ text: v }); } });
    return { stop: stop };
  }
  window.StaffAsk = { init: init };
})();

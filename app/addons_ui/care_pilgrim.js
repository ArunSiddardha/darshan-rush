/* Care requests, pilgrim side. No global side effects except window.CarePilgrim.
   CarePilgrim.init(root, {endpoint:'/api/care', uid:'u1' | () => 'u1', lang:'te' | () => 'te', stop: () => 'g3'|null, maxMs:15000, pollMs:5000}) -> {refresh, submitText} */
(function () {
  'use strict';
  var UI = {
    en: {open: 'I need help', speak: 'Speak', stop: 'Tap to send', send: 'Sending...', medical: 'Medical', lost_person: 'Lost person', tout_payment: 'Someone asks for money', other: 'Other', type: 'or type here', meta: 'Request number'},
    hi: {open: 'मुझे मदद चाहिए', speak: 'बोलिए', stop: 'भेजने के लिए दबाएँ', send: 'भेज रहे हैं...', medical: 'स्वास्थ्य', lost_person: 'खोया हुआ व्यक्ति', tout_payment: 'कोई पैसे मांग रहा है', other: 'कुछ और', type: 'या यहाँ लिखिए', meta: 'अनुरोध नंबर'},
    te: {open: 'నాకు సహాయం కావాలి', speak: 'మాట్లాడండి', stop: 'పంపడానికి నొక్కండి', send: 'పంపుతున్నాం...', medical: 'ఆరోగ్యం', lost_person: 'తప్పిపోయిన వ్యక్తి', tout_payment: 'ఎవరో డబ్బు అడుగుతున్నారు', other: 'ఇతరం', type: 'లేదా ఇక్కడ రాయండి', meta: 'అభ్యర్థన నంబర్'},
    ta: {open: 'எனக்கு உதவி வேண்டும்', speak: 'பேசுங்கள்', stop: 'அனுப்பத் தொடுங்கள்', send: 'அனுப்புகிறது...', medical: 'உடல்நலம்', lost_person: 'காணாமல் போனவர்', tout_payment: 'யாரோ பணம் கேட்கிறார்', other: 'மற்றவை', type: 'அல்லது இங்கே தட்டச்சு செய்யுங்கள்', meta: 'கோரிக்கை எண்'},
    ml: {open: 'എനിക്ക് സഹായം വേണം', speak: 'സംസാരിക്കൂ', stop: 'അയയ്ക്കാൻ തൊടൂ', send: 'അയയ്ക്കുന്നു...', medical: 'ആരോഗ്യം', lost_person: 'കാണാതായ ആൾ', tout_payment: 'ആരോ പണം ചോദിക്കുന്നു', other: 'മറ്റുള്ളവ', type: 'അല്ലെങ്കിൽ ഇവിടെ എഴുതൂ', meta: 'അപേക്ഷാ നമ്പർ'},
    kn: {open: 'ನನಗೆ ಸಹಾಯ ಬೇಕು', speak: 'ಮಾತನಾಡಿ', stop: 'ಕಳುಹಿಸಲು ಒತ್ತಿ', send: 'ಕಳುಹಿಸುತ್ತಿದೆ...', medical: 'ಆರೋಗ್ಯ', lost_person: 'ಕಳೆದುಹೋದ ವ್ಯಕ್ತಿ', tout_payment: 'ಯಾರೋ ಹಣ ಕೇಳುತ್ತಿದ್ದಾರೆ', other: 'ಇತರೆ', type: 'ಅಥವಾ ಇಲ್ಲಿ ಬರೆಯಿರಿ', meta: 'ವಿನಂತಿ ಸಂಖ್ಯೆ'}
  };
  var STOPS = [['g1', 'Base Camp'], ['g2', 'River Crossing'], ['g3', 'Forest Path'], ['g4', 'Queue Complex'], ['g5', 'Main Steps']];
  function q(root, k) { return root.querySelector('[data-cp="' + k + '"]'); }
  function val(v, d) { return typeof v === 'function' ? v() : (v == null ? d : v); }

  function init(root, opts) {
    opts = opts || {};
    var ep = opts.endpoint || '/api/care', maxMs = opts.maxMs || 15000, pollMs = opts.pollMs || 5000;
    var uid = function () { return val(opts.uid, 'anon'); }, lang = function () { return val(opts.lang, 'en'); }, stop = function () { return val(opts.stop, null); };
    var T = function () { return UI[lang()] || UI.en; };
    var openB = q(root, 'open'), panel = q(root, 'panel'), talk = q(root, 'talk'), note = q(root, 'note'), form = q(root, 'form'), txt = q(root, 'text'),
        card = q(root, 'card'), audio = q(root, 'audio'), stopsBox = q(root, 'stops');
    var rec = null, chunks = [], stream = null, timer = null, poll = null, lastId = null;

    function labels() {
      var t = T();
      q(root, 'openlabel').textContent = t.open; txt.placeholder = t.type;
      ['medical', 'lost_person', 'tout_payment', 'other'].forEach(function (k) { q(root, 'c-' + k).textContent = t[k]; });
      q(root, 'talklabel').textContent = root.dataset.state === 'recording' ? t.stop : root.dataset.state === 'sending' ? t.send : t.speak;
    }
    function state(s) { root.dataset.state = s; labels(); }
    function err(m) { note.textContent = m || ''; }
    function toggle(open) { panel.hidden = !open; openB.setAttribute('aria-expanded', open ? 'true' : 'false'); if (open) { state('idle'); } else { state('closed'); } }
    openB.addEventListener('click', function () { toggle(panel.hidden); });

    function show(r) {
      card.hidden = false; card.dataset.urg = r.urgency || '';
      q(root, 'num').textContent = r.id;
      q(root, 'status').textContent = r.status_text || r.reply_text || '';
      q(root, 'meta').textContent = T().meta + (r.stop_name ? ' · ' + r.stop_name : '');
    }
    function askStop(id) {
      stopsBox.hidden = false; stopsBox.textContent = '';
      STOPS.forEach(function (s) {
        var b = document.createElement('button'); b.type = 'button'; b.textContent = s[1];
        b.addEventListener('click', function () {
          fetch(ep + '/' + encodeURIComponent(id) + '/stop', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({stop: s[0]})})
            .then(function (r) { return r.json(); }).then(function () { stopsBox.hidden = true; refresh(); }).catch(function () {});
        });
        stopsBox.appendChild(b);
      });
    }
    function handle(j) {
      state('idle');
      if (!j.id) { err(j.reply_text || j.notice || ''); return; }
      err(j.notice && j.notice !== 'duplicate' ? j.notice : '');
      lastId = j.id; show({id: j.id, urgency: j.urgency, status_text: j.reply_text, stop_name: j.stop && j.stop.name});
      if (j.audio_base64) { audio.src = 'data:audio/wav;base64,' + j.audio_base64; audio.play().catch(function () {}); }
      else if ('speechSynthesis' in window && j.reply_text) { try { var u = new SpeechSynthesisUtterance(j.reply_text); u.lang = lang() + '-IN'; speechSynthesis.speak(u); } catch (e) {} }
      if (j.needs_stop) askStop(j.id); else stopsBox.hidden = true;
      toggle(false); startPoll();
    }
    function post(fd, json) {
      state('sending'); err('');
      var o = json ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(json)} : {method: 'POST', body: fd};
      return fetch(ep, o).then(function (r) { return r.json(); }).then(handle).catch(function () { state('idle'); err('No connection. Please try again or go to the help counter.'); });
    }
    function base() { var b = {uid: uid(), lang: lang()}; var s = stop(); if (s) b.stop = s; return b; }
    function submitText(text, choice) { var b = base(); if (text) b.text = text; if (choice) b.choice = choice; return post(null, b); }

    Array.prototype.forEach.call(root.querySelectorAll('[data-choice]'), function (b) {
      b.addEventListener('click', function () { var c = b.getAttribute('data-choice'); if (c === 'other') { txt.focus(); } submitText('', c); });
    });
    form.addEventListener('submit', function (e) { e.preventDefault(); var t = txt.value.trim(); if (t) { txt.value = ''; submitText(t); } });

    function finish() {
      clearTimeout(timer);
      if (rec && rec.state !== 'inactive') rec.stop();
      if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    }
    talk.addEventListener('click', function () {
      if (root.dataset.state === 'recording') { finish(); return; }
      if (!navigator.mediaDevices || !window.MediaRecorder) { err('Voice is not available on this phone. Please type or use a button.'); return; }
      navigator.mediaDevices.getUserMedia({audio: true}).then(function (s) {
        stream = s; chunks = []; rec = new MediaRecorder(s);
        rec.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
        rec.onstop = function () {
          var blob = new Blob(chunks, {type: rec.mimeType || 'audio/webm'}), fd = new FormData(), b = base();
          Object.keys(b).forEach(function (k) { fd.append(k, b[k]); });
          fd.append('audio', blob, 'help.' + ((rec.mimeType || '').indexOf('mp4') >= 0 ? 'm4a' : 'webm'));
          post(fd);
        };
        rec.start(); state('recording'); timer = setTimeout(finish, maxMs);
      }).catch(function () { err('Microphone is blocked. Please type or use a button.'); });
    });

    function refresh() {
      return fetch(ep + '/mine?uid=' + encodeURIComponent(uid())).then(function (r) { return r.json(); }).then(function (j) {
        var rs = (j.requests || []), act = rs.filter(function (r) { return r.status !== 'resolved' && r.status !== 'could_not_resolve'; });
        var r = act[0] || (lastId && rs.filter(function (x) { return x.id === lastId; })[0]) || rs[0];
        if (!r) { card.hidden = true; return; }
        show(r);
        if (!act.length) stopPoll();
      }).catch(function () {});
    }
    function startPoll() { stopPoll(); poll = setInterval(refresh, pollMs); }
    function stopPoll() { if (poll) { clearInterval(poll); poll = null; } }
    state('closed'); refresh().then(function () { if (!card.hidden && card.dataset.urg !== undefined) startPoll(); });
    return {refresh: refresh, submitText: submitText, open: function () { toggle(true); }};
  }
  window.CarePilgrim = {init: init, UI: UI};
})();

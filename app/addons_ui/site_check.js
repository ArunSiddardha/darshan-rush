/* Site-check fragment. No globals except AddonsSiteCheck. */
(function () {
  var BADGE = { high_risk: 'High risk', caution: 'Be careful', unknown: 'Cannot check' };
  function init(root, opts) {
    opts = opts || {};
    var q = function (n) { return root.querySelector('[data-ad="' + n + '"]'); };
    var audio = null;
    q('go').addEventListener('click', async function () {
      var text = q('text').value.trim(); if (!text) { q('status').textContent = 'Paste an address or type the offer first.'; return; }
      q('status').textContent = 'Checking...'; q('out').hidden = true;
      try {
        var r = await fetch(opts.endpoint || '/api/site-check', { method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ text: text, lang: window.DARSHAN_LANG || q('lang').value || 'en', uid: opts.uid || '' }) });
        var j = await r.json();
        q('status').textContent = j.notice || '';
        if (j.reply_text) {
          q('badge').textContent = (window.DARSHAN_BADGE || BADGE)[j.verdict] || ''; q('reply').textContent = j.reply_text;
          var ul = q('reasons'); ul.textContent = '';
          (j.reasons || []).forEach(function (x) { var li = document.createElement('li'); li.textContent = x; ul.appendChild(li); });
          q('play').hidden = !j.audio_base64; q('out').hidden = false;
          audio = j.audio_base64 ? new Audio('data:audio/wav;base64,' + j.audio_base64) : null;
          if (audio) audio.play().catch(function () {});
        }
      } catch (e) { q('status').textContent = 'Could not reach the server. Try again.'; }
    });
    q('play').addEventListener('click', function () { if (audio) { audio.currentTime = 0; audio.play().catch(function () {}); } });
  }
  window.AddonsSiteCheck = { init: init };
})();

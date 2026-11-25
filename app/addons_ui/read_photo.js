/* Read-a-photo fragment. No globals. Usage: AddonsReadPhoto.init(document.getElementById('ad-read'), {endpoint:'/api/read-photo', uid:'...'})
   Call init() yourself after the fragment is in the page. */
(function () {
  function init(root, opts) {
    opts = opts || {};
    var q = function (n) { return root.querySelector('[data-ad="' + n + '"]'); };
    var audio = null;
    q('file').addEventListener('change', async function (e) {
      var f = e.target.files && e.target.files[0]; if (!f) return;
      var lang = (window.DARSHAN_LANG || q('lang').value || 'en');
      var fd = new FormData(); fd.append('image', f, f.name || 'photo.jpg'); fd.append('lang', lang); fd.append('uid', opts.uid || '');
      q('status').textContent = 'Reading the photo...'; q('out').hidden = true;
      try {
        var r = await fetch(opts.endpoint || '/api/read-photo', { method: 'POST', body: fd });
        var j = await r.json();
        q('status').textContent = j.notice || '';
        if (j.translated_text || j.text) {
          q('translated').textContent = j.translated_text || j.text; q('text').textContent = j.text || '';
          q('lat').textContent = j.latency && j.latency.total_ms ? 'Took ' + (j.latency.total_ms / 1000).toFixed(1) + ' s' : '';
          q('out').hidden = false;
          q('play').hidden = !j.audio_base64;
          audio = j.audio_base64 ? new Audio('data:audio/wav;base64,' + j.audio_base64) : null;
          if (audio) audio.play().catch(function () {});
        }
      } catch (err) { q('status').textContent = 'Could not reach the server. Try again.'; }
      e.target.value = '';
    });
    q('play').addEventListener('click', function () { if (audio) { audio.currentTime = 0; audio.play().catch(function () {}); } });
  }
  window.AddonsReadPhoto = { init: init };
})();

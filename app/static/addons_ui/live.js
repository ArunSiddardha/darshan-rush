/* Live conversation: one tap, then hands-free talking. No dependencies, no global side effects except two names:
   window.LiveSession (the engine) and window.AddonsLive.init(root, opts) (binds the live.html fragment).

   const s = new LiveSession({ endpoint:'/api/live/turn', promptEndpoint:'/api/live/prompt', uid:'u1', lang:'te' });
   s.on('state', st => ...)   // idle | listening | hearing | thinking | speaking | error
   s.on('level', v => ...)    // 0..1, mic level while listening, voice envelope while speaking
   s.on('caption', c => ...)  // {who:'you'|'app', text}
   s.on('turn', t => ...)     // {transcript, reply_text, latency:{stt_ms,llm_ms,tts_ms,total_ms}, client:{...}}
   s.on('end', e => ...)      // {reason:'goodbye'|'silence'|'stopped'|'denied'|'lost'}
   s.on('error', e => ...)    // {code, message}
   await s.start()            // MUST be called from a tap handler
   s.stop()

   RECORDING CHOICE: we keep raw PCM in a ring buffer (AudioWorklet, ScriptProcessor fallback) and encode a 16 kHz mono
   16-bit WAV ourselves. MediaRecorder gives audio/webm on Chrome but audio/mp4 on iPhone Safari (fragmented mp4, odd
   headers, and a recorder that must be restarted per utterance, which loses the first syllable). WAV from PCM is the
   same bytes on every browser, needs no container support, allows an exact pre-roll, and Sarvam reads it directly.
   Cost: about 32 KB per second of speech (a 12 s utterance is about 380 KB). */
(function () {
  'use strict';
  var SILENT_WAV = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
  var WORKLET = 'class P extends AudioWorkletProcessor{constructor(){super();this.b=new Float32Array(1024);this.n=0;}' +
    'process(i){var x=i[0]&&i[0][0];if(x){for(var k=0;k<x.length;k++){this.b[this.n++]=x[k];if(this.n===1024){this.port.postMessage(this.b.slice(0));this.n=0;}}}return true;}}' +
    'registerProcessor("live-cap",P);';
  var FRAME = 1024;

  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function rms(f) { var s = 0; for (var i = 0; i < f.length; i++) s += f[i] * f[i]; return Math.sqrt(s / f.length); }

  // ---- 16 kHz mono WAV from float PCM (box-filter downsample)
  function toWav16k(chunks, sr) {
    var n = 0, i, j; for (i = 0; i < chunks.length; i++) n += chunks[i].length;
    var all = new Float32Array(n), o = 0; for (i = 0; i < chunks.length; i++) { all.set(chunks[i], o); o += chunks[i].length; }
    var ratio = sr / 16000, m = Math.floor(n / ratio), pcm = new Int16Array(m);
    for (i = 0; i < m; i++) {
      var a = i * ratio, b = a + ratio, s = 0, w = 0, k = Math.floor(a);
      for (j = k; j < b && j < n; j++) { var wt = Math.min(j + 1, b) - Math.max(j, a); s += all[j] * wt; w += wt; }
      var v = w ? s / w : 0; pcm[i] = clamp(v, -1, 1) * 32767;
    }
    var buf = new ArrayBuffer(44 + m * 2), dv = new DataView(buf);
    function str(p, t) { for (var q = 0; q < t.length; q++) dv.setUint8(p + q, t.charCodeAt(q)); }
    str(0, 'RIFF'); dv.setUint32(4, 36 + m * 2, true); str(8, 'WAVE'); str(12, 'fmt '); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, 1, true); dv.setUint32(24, 16000, true); dv.setUint32(28, 32000, true);
    dv.setUint16(32, 2, true); dv.setUint16(34, 16, true); str(36, 'data'); dv.setUint32(40, m * 2, true);
    for (i = 0; i < m; i++) dv.setInt16(44 + i * 2, pcm[i], true);
    return new Blob([buf], { type: 'audio/wav' });
  }

  // ---- voice envelope of a PCM16 wav (50 ms steps) so the UI can breathe with the reply without routing audio through Web Audio
  function envelope(bytes) {
    try {
      var dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), p = 12, rate = 24000, ch = 1, bits = 16, ds = -1, dl = 0;
      while (p + 8 <= bytes.length) {
        var id = String.fromCharCode(bytes[p], bytes[p + 1], bytes[p + 2], bytes[p + 3]), sz = dv.getUint32(p + 4, true);
        if (id === 'fmt ') { ch = dv.getUint16(p + 10, true); rate = dv.getUint32(p + 12, true); bits = dv.getUint16(p + 22, true); }
        if (id === 'data') { ds = p + 8; dl = Math.min(sz, bytes.length - ds); break; }
        p += 8 + sz + (sz & 1);
      }
      if (ds < 0 || bits !== 16) return null;
      var step = Math.floor(rate * 0.05) * ch, out = [], mx = 0.0001;
      for (var s = ds; s + step * 2 <= ds + dl; s += step * 2) {
        var acc = 0; for (var k = 0; k < step; k += ch) { var x = dv.getInt16(s + k * 2, true) / 32768; acc += x * x; }
        var r = Math.sqrt(acc / (step / ch)); out.push(r); if (r > mx) mx = r;
      }
      return out.map(function (r) { return clamp(r / mx, 0, 1); });
    } catch (e) { return null; }
  }

  function LiveSession(opts) {
    opts = opts || {};
    this.o = {
      endpoint: opts.endpoint || '/api/live/turn', promptEndpoint: opts.promptEndpoint || '/api/live/prompt',
      uid: opts.uid || 'live-' + Math.random().toString(36).slice(2, 8), lang: opts.lang || 'en',
      silenceMs: opts.silenceMs || 900, minUtteranceMs: opts.minUtteranceMs || 350, maxUtteranceMs: opts.maxUtteranceMs || 12000,
      startMs: opts.startMs || 150, prerollMs: opts.prerollMs || 400, calibrateMs: opts.calibrateMs || 500,
      onRatio: opts.onRatio || 3, onAbs: opts.onAbs || 0.01, offRatio: opts.offRatio || 1.8, offAbs: opts.offAbs || 0.005,
      bargeMs: opts.bargeMs || 300, bargeRatio: opts.bargeRatio || 2.5, bargeEnabled: opts.bargeEnabled !== false, noLevel: !!opts.noLevel,
      nudgeAfterMs: opts.nudgeAfterMs || 8000, endAfterMs: opts.endAfterMs || 25000, timeoutMs: opts.timeoutMs || 20000,
      audioEl: opts.audioEl || null, testSource: opts.testSource || null, getStream: opts.getStream || null, fetch: opts.fetch || null, greeting: opts.greeting !== false, auto: !!opts.auto
    };
    this.sessionId = opts.sessionId || 's-' + Math.random().toString(36).slice(2, 10);
    this.lang = this.o.lang; this.state = 'idle'; this.level = 0; this.metrics = []; this.log = [];
    this._h = {}; this._q = []; this._playing = false; this._pending = null; this._reset();
  }
  var LP = LiveSession.prototype;

  LP._reset = function () {
    this.phase = 'off'; this.hearing = false; this.t = 0; this.calMs = 0; this.calSum = 0; this.calN = 0; this.floor = 0.004;
    this.lv = 0; this.ring = []; this.buf = null; this.voicedMs = 0; this.silentMs = 0; this.aboveMs = 0; this.bufMs = 0;
    this.idleMs = 0; this.nudged = false; this.nudgePlaying = false; this.echo = 0; this.bargeAbove = 0; this.endAfter = false; this.frames = 0;
  };
  LP.on = function (n, f) { (this._h[n] = this._h[n] || []).push(f); return this; };
  LP._emit = function (n, d) { var a = this._h[n] || []; for (var i = 0; i < a.length; i++) { try { a[i](d); } catch (e) { /* listener errors never break the loop */ } } };
  LP._log = function (what, extra) { var e = { t: Math.round(this.t), at: Date.now(), what: what }; if (extra) for (var k in extra) e[k] = extra[k]; this.log.push(e); };
  LP._set = function (s) { if (s !== this.state) { this.state = s; this._emit('state', s); this._emit(s, s); } };
  LP._caption = function (who, text) { if (text) this._emit('caption', { who: who, text: text }); };
  LP.setLang = function (l) { this.lang = l; };

  // ------------------------------------------------------------------ start / stop
  LP.start = async function () {
    if (this.phase !== 'off') return;
    this._reset(); this.phase = 'starting'; this.metrics = []; this.log = [];
    var AC = window.AudioContext || window.webkitAudioContext;
    // 1) inside the tap: audio context and the single <audio> element, so iPhone allows every later reply
    this.ctx = new AC(); try { this.ctx.resume(); } catch (e) {}
    this.audio = this.o.audioEl || new Audio(); this.audio.setAttribute('playsinline', ''); this.audio.src = SILENT_WAV;
    try { var pp = this.audio.play(); if (pp && pp.catch) pp.catch(function () {}); } catch (e) {}
    // 2) one microphone stream for the whole session
    try {
      if (this.o.testSource) this._testNode = await this.o.testSource(this.ctx); // tests only: audio node in the same context instead of a mic
      else this.stream = this.o.getStream ? await this.o.getStream() : await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
    } catch (e) {
      var denied = e && (e.name === 'NotAllowedError' || e.name === 'SecurityError' || e.name === 'PermissionDeniedError');
      this._fail(denied ? 'denied' : 'nomic', denied ? 'Microphone is blocked. Allow the microphone for this site, then tap again.' :
        'No microphone found. Plug one in, then tap again.');
      return;
    }
    var self = this;
    if (this.stream) this.stream.getAudioTracks().forEach(function (tr) {
      tr.addEventListener('ended', function () { self._finish('lost', 'The microphone stopped. Tap to talk again.'); });
    });
    this._onVis = function () { self._visibility(); }; document.addEventListener('visibilitychange', this._onVis);
    this.ctx.onstatechange = function () { if (self.ctx && self.ctx.state === 'interrupted') self._tryResume(); };
    await this._wake();
    await this._wireCapture();
    this._audioEvents();
    this.phase = 'listen'; this._log('started', { sampleRate: this.ctx.sampleRate });
    this._set('listening');
    if (this.o.greeting) this._prompt('greeting'); // spoken while the noise floor is still being measured
  };

  LP._wireCapture = async function () {
    var self = this, src = this._testNode || this.ctx.createMediaStreamSource(this.stream), sink = this.ctx.createGain();
    sink.gain.value = 0; sink.connect(this.ctx.destination); this.src = src; this.sink = sink;
    function onFrame(f) { self._frame(f); }
    if (this.ctx.audioWorklet && window.Blob && window.URL) {
      try {
        var url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }));
        await this.ctx.audioWorklet.addModule(url); URL.revokeObjectURL(url);
        var node = new AudioWorkletNode(this.ctx, 'live-cap', { numberOfOutputs: 1, outputChannelCount: [1] });
        node.port.onmessage = function (m) { onFrame(m.data); };
        src.connect(node); node.connect(sink); this.node = node; this.capture = 'worklet'; return;
      } catch (e) { /* fall through */ }
    }
    var sp = this.ctx.createScriptProcessor(FRAME, 1, 1);
    sp.onaudioprocess = function (e) { onFrame(new Float32Array(e.inputBuffer.getChannelData(0))); };
    src.connect(sp); sp.connect(sink); this.node = sp; this.capture = 'scriptprocessor';
  };

  LP.stop = function () { this._finish('stopped'); };

  LP._finish = function (reason, message) {
    if (this.phase === 'off') return;
    this.phase = 'off'; this.hearing = false;
    try { this.audio.pause(); } catch (e) {}
    this._q = []; this._playing = false; this._pending = null;
    try { if (this.node) { this.node.disconnect(); if (this.node.port) this.node.port.onmessage = null; } if (this.src) this.src.disconnect(); } catch (e) {}
    try { if (this.stream) this.stream.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
    try { if (this.ctx) { this.ctx.onstatechange = null; this.ctx.close(); } } catch (e) {}
    try { if (this._wl) this._wl.release(); } catch (e) {}
    this._wl = null; this.ctx = null; this.stream = null;
    if (this._onVis) document.removeEventListener('visibilitychange', this._onVis);
    this.level = 0; this._emit('level', 0); this._set('idle');
    this._emit('end', { reason: reason, message: message || (reason === 'silence' ? 'Tap to talk again' : '') });
  };

  LP._fail = function (code, message) {
    this.phase = 'off'; try { if (this.ctx) this.ctx.close(); } catch (e) {} this.ctx = null;
    this._set('error'); this._emit('error', { code: code, message: message }); this._emit('end', { reason: code, message: message });
  };

  LP._wake = async function () {
    try { if (navigator.wakeLock) this._wl = await navigator.wakeLock.request('screen'); } catch (e) { this._wl = null; }
  };

  LP._tryResume = function () {
    var self = this, c = this.ctx; if (!c) return;
    try { c.resume(); } catch (e) {}
    setTimeout(function () { if (self.ctx === c && c.state !== 'running' && !document.hidden) self._finish('lost', 'The phone paused the microphone. Tap to talk again.'); }, 1500);
  };

  LP._visibility = function () {
    if (this.phase === 'off') return;
    if (document.hidden) { this.hearing = false; this.buf = null; this._log('hidden'); return; }
    this._log('visible'); this._wake();
    var live = !this.stream || this.stream.getAudioTracks().some(function (t) { return t.readyState === 'live'; });
    if (!live) return this._finish('lost', 'The microphone stopped. Tap to talk again.');
    this._tryResume();
    if (this.audio && this._playing && this.audio.paused) { var self = this; var p = this.audio.play(); if (p && p.catch) p.catch(function () { self._playEnded(); }); }
    this.idleMs = 0;
  };

  // ------------------------------------------------------------------ voice activity detection
  LP._thr = function () {
    var f = this.floor, o = this.o;
    return { on: Math.max(f * o.onRatio, f + o.onAbs), off: Math.max(f * o.offRatio, f + o.offAbs) };
  };

  LP._frame = function (f) {
    if (this.phase === 'off' || this.phase === 'starting' || document.hidden) return;
    var o = this.o, dt = f.length / this.ctx.sampleRate * 1000, r = rms(f);
    this.t += dt; this.frames++;
    this.lv = r > this.lv ? r : this.lv * 0.85 + r * 0.15;
    var speaking = this.phase === 'speak';
    // 1) noise floor: measured first, then updated while nothing is happening
    if (this.calMs < o.calibrateMs) {
      if (!speaking) { this.calMs += dt; this.calSum += r; this.calN++; if (this.calMs >= o.calibrateMs) { this.floor = Math.max(0.002, this.calSum / this.calN); this._log('floor', { floor: +this.floor.toFixed(4) }); } }
      return this._level();
    }
    var th = this._thr();
    if (!speaking && !this.hearing && this.lv < th.on) this.floor = Math.max(0.0015, this.floor * 0.97 + Math.min(this.lv, this.floor * 2) * 0.03);
    // 2) pre-roll ring
    this.ring.push(f); var maxRing = Math.ceil(o.prerollMs / (FRAME / this.ctx.sampleRate * 1000)); if (this.ring.length > maxRing) this.ring.shift();
    // 3) per phase
    if (speaking) {
      this.echo = this.echo * 0.98 + Math.min(this.lv, th.on * 3) * 0.02;
      if (this.nudgePlaying) this._idle(dt);
      var bt = Math.max(th.on * 1.5, this.echo * o.bargeRatio);
      this.bargeAbove = o.bargeEnabled && this.lv > bt ? this.bargeAbove + dt : Math.max(0, this.bargeAbove - dt);
      if (this.bargeAbove >= o.bargeMs) this._barge();
    } else if (this.hearing) {
      this.buf.push(f); this.bufMs += dt;
      if (this.lv > th.off) { this.silentMs = 0; this.voicedMs += dt; } else this.silentMs += dt;
      if (this.silentMs >= o.silenceMs || this.bufMs >= o.maxUtteranceMs) this._endUtterance(this.silentMs < o.silenceMs ? 'max' : 'silence');
    } else {
      this.aboveMs = r > th.on ? this.aboveMs + dt : Math.max(0, this.aboveMs - dt); // raw frame level, not the smoothed one: a click must not look like speech
      if (this.aboveMs >= o.startMs) this._beginUtterance(); else if (this.phase === 'listen') this._idle(dt);
    }
    this._level();
  };

  LP._idle = function (dt) {
    this.idleMs += dt;
    if (!this.nudged && this.idleMs >= this.o.nudgeAfterMs && this.phase === 'listen') { this.nudged = true; this.nudgePlaying = true; this._log('nudge'); this._prompt('nudge'); }
    if (this.idleMs >= this.o.endAfterMs) { this._log('silence_end'); this._finish('silence', 'Tap to talk again'); }
  };

  LP._beginUtterance = function () {
    this.hearing = true; this.buf = this.ring.slice(); this.bufMs = this.buf.length * FRAME / this.ctx.sampleRate * 1000;
    this.voicedMs = this.aboveMs; this.silentMs = 0; this.aboveMs = 0; this.idleMs = 0; this.nudged = false; this.nudgePlaying = false;
    this._log('speech_start'); if (this.phase === 'listen') this._set('hearing');
  };

  LP._barge = function () {
    this._log('barge_in'); this._q = []; this._playing = false; this.nudgePlaying = false;
    try { this.audio.pause(); } catch (e) {}
    this.phase = 'listen'; this.bargeAbove = 0; this._beginUtterance(); this.voicedMs = this.o.startMs;
  };

  LP._endUtterance = function (why) {
    var o = this.o, ms = this.voicedMs, chunks = this.buf, silent = this.silentMs;
    this.hearing = false; this.buf = null; this.silentMs = 0; this.aboveMs = 0; this.ring = []; this.idleMs = 0;
    var fm = FRAME / this.ctx.sampleRate * 1000, keepTail = Math.max(0, Math.ceil(250 / fm));
    if (why === 'silence') chunks = chunks.slice(0, Math.max(1, chunks.length - Math.max(0, Math.floor(silent / fm) - keepTail)));
    if (ms < o.minUtteranceMs) { this._log('discarded_short', { voiced: Math.round(ms) }); if (this.phase === 'listen') this._set('listening'); return; }
    this._log('speech_end', { voiced: Math.round(ms), why: why });
    var wav = toWav16k(chunks, this.ctx.sampleRate), job = { wav: wav, voiced: ms, endAt: performance.now() };
    if (this.phase === 'think') { this._pending = job; this._log('queued'); return; } // spoke while we were still answering
    this._send(job);
  };

  LP._level = function () {
    if (this.frames % 2 || this.o.noLevel) return;
    var v;
    if (this.phase === 'speak' && this._env) {
      var i = Math.floor((this.audio.currentTime || 0) * 20); v = this._env[i] == null ? 0 : this._env[i] * 0.9;
    } else if (this.phase === 'speak') v = 0.35 + 0.25 * Math.sin(this.t / 140);
    else v = clamp(Math.sqrt(Math.max(0, this.lv - this.floor)) * 2.6, 0, 1);
    this.level = this.level * 0.5 + v * 0.5; this._emit('level', this.level);
  };

  // ------------------------------------------------------------------ talking to the server
  LP._fetch = function (url, init) {
    var f = this.o.fetch || window.fetch.bind(window), ac = new AbortController(), tm = setTimeout(function () { ac.abort(); }, this.o.timeoutMs);
    init.signal = ac.signal; return f(url, init).finally(function () { clearTimeout(tm); });
  };

  LP._post = async function (job) {
    for (var attempt = 0; attempt < 2; attempt++) {
      try {
        var fd = new FormData(); fd.append('audio', job.wav, 'utterance.wav'); fd.append('uid', this.o.uid);
        fd.append('lang', this.lang); fd.append('session_id', this.sessionId); if (this.o.auto) fd.append('auto', '1');
        var r = await this._fetch(this.o.endpoint, { method: 'POST', body: fd });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return await r.json();
      } catch (e) { if (this.phase === 'off') return null; this._log('net_retry', { n: attempt + 1 }); await new Promise(function (ok) { setTimeout(ok, 500); }); }
    }
    return undefined;
  };

  LP._send = async function (job) {
    this.phase = 'think'; this._set('thinking'); var t0 = performance.now();
    var j = await this._post(job);
    if (this.phase === 'off') return;
    if (j === undefined) { // retried once, still failing: say so
      this._caption('app', 'I could not reach the server. Please say it again in a moment.'); this._emit('error', { code: 'network', message: 'Network problem' });
      try { if (window.speechSynthesis) window.speechSynthesis.speak(new SpeechSynthesisUtterance('I could not reach the server. Please try again.')); } catch (e) {}
      return this._backToListening();
    }
    var client = { send_ms: Math.round(performance.now() - t0), since_speech_end_ms: Math.round(performance.now() - job.endAt), utterance_voiced_ms: Math.round(job.voiced) };
    if (j.ignored) { this._log('ignored_by_server'); this.metrics.push({ ignored: true, client: client, latency: j.latency }); return this._backToListening(); }
    if (j.lang) this.lang = j.lang;
    this._caption('you', j.transcript);
    this._caption('app', j.reply_text);
    var m = { transcript: j.transcript, reply_text: j.reply_text, intent: j.intent, state: j.state, latency: j.latency, client: client, spoke_at: null, raw: j };
    this.metrics.push(m); this._lastMetric = m; this._emit('turn', m);
    if (j.error) { this._emit('error', { code: 'server', message: j.notice || j.reply_text }); }
    this.endAfter = !!j.end_session;
    if (j.audio_base64) { this.phase = 'speak'; this.echo = 0; this.bargeAbove = 0; this._enqueue(j.audio_base64); }
    else this._backToListening();
  };

  LP._prompt = async function (kind) {
    try {
      var fd = new FormData(); fd.append('kind', kind); fd.append('lang', this.lang); fd.append('session_id', this.sessionId);
      var r = await this._fetch(this.o.promptEndpoint, { method: 'POST', body: fd }), j = await r.json();
      for (var w = 0; kind === 'greeting' && this.calMs < this.o.calibrateMs && w < 40 && this.phase !== 'off'; w++) await new Promise(function (ok) { setTimeout(ok, 50); }); // measure the noise floor in quiet first
      if (this.phase === 'off' || this.hearing) { this.nudgePlaying = false; return; }
      this._caption('app', j.reply_text);
      if (j.audio_base64 && this.phase === 'listen') { this.phase = 'speak'; this.echo = 0; this.bargeAbove = 0; this._enqueue(j.audio_base64); }
      else { this.nudgePlaying = false; }
    } catch (e) { this.nudgePlaying = false; }
  };

  LP._backToListening = function () {
    if (this.phase === 'off') return;
    if (this.endAfter) return this._finish('goodbye', 'Take care. Tap to talk again.');
    this.phase = 'listen'; this.idleMs = 0; this.nudged = false; this.nudgePlaying = false; this.aboveMs = 0; this.ring = []; this._env = null;
    if (this._pending) { var j = this._pending; this._pending = null; this.hearing = false; return this._send(j); }
    this._set(this.hearing ? 'hearing' : 'listening');
  };

  // ------------------------------------------------------------------ audio out: one element, a queue
  LP._audioEvents = function () {
    var self = this;
    this.audio.onended = function () { self._playEnded(); };
    this.audio.onerror = function () { self._playEnded(); };
    this.audio.onplaying = function () {
      if (self._lastMetric && self._lastMetric.spoke_at == null) { self._lastMetric.spoke_at = performance.now(); self._lastMetric.client.first_audio_ms = Math.round(performance.now() - self._turnEnd(self._lastMetric)); }
    };
  };
  LP._turnEnd = function (m) { return performance.now() - m.client.since_speech_end_ms; };

  LP._enqueue = function (b64) { this._q.push(b64); this._set('speaking'); if (!this._playing) this._pump(); };

  LP._pump = function () {
    var self = this, b64 = this._q.shift();
    if (!b64) { this._playing = false; return this._backToListening(); }
    this._playing = true;
    try {
      var bin = atob(b64), bytes = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      this._env = envelope(bytes);
      if (this._url) URL.revokeObjectURL(this._url);
      this._url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' })); this.audio.src = this._url;
      var p = this.audio.play();
      if (p && p.catch) p.catch(function (e) { self._log('play_blocked', { err: String(e && e.name) }); self._emit('error', { code: 'audio_blocked', message: 'Tap the screen to hear the reply.' }); self._playEnded(); });
    } catch (e) { this._playEnded(); }
  };

  LP._playEnded = function () { if (!this._playing) return; this._playing = false; this._pump(); };

  // ------------------------------------------------------------------ fragment binding (live.html)
  function init(root, opts) {
    opts = opts || {};
    var q = function (n) { return root.querySelector('[data-live="' + n + '"]'); };
    var LABEL = { idle: 'Tap once to start talking', listening: 'Listening. Just talk.', hearing: 'I hear you', thinking: 'One moment', speaking: 'Speaking. You can talk over me.', error: 'Something went wrong' };
    var s = null, start = q('start'), end = q('end'), circle = q('circle'), label = q('label'), you = q('you'), app = q('app'), note = q('note');
    function paint(st) { root.setAttribute('data-state', st); label.textContent = LABEL[st] || st; start.hidden = st !== 'idle' && st !== 'error'; end.hidden = st === 'idle' || st === 'error'; }
    function make() {
      var o = {}; for (var k in opts) o[k] = opts[k];
      o.lang = typeof opts.lang === 'function' ? opts.lang() : (opts.lang || window.DARSHAN_LANG || 'en');
      s = new LiveSession(o);
      s.on('state', paint);
      s.on('level', function (v) { circle.style.setProperty('--lv', v.toFixed(3)); });
      s.on('caption', function (c) { (c.who === 'you' ? you : app).textContent = c.text; });
      s.on('error', function (e) { note.textContent = e.message || ''; });
      s.on('end', function (e) { paint('idle'); note.textContent = e.message || ''; start.textContent = e.reason === 'silence' || e.reason === 'goodbye' || e.reason === 'lost' ? 'Tap to talk again' : 'Tap once to start talking'; });
      if (opts.onSession) opts.onSession(s);
      return s;
    }
    start.addEventListener('click', function () { note.textContent = ''; you.textContent = ''; app.textContent = ''; make().start(); });
    end.addEventListener('click', function () { if (s) s.stop(); });
    paint('idle');
    return { get session() { return s; } };
  }

  window.LiveSession = LiveSession;
  window.AddonsLive = { init: init, toWav16k: toWav16k };
})();

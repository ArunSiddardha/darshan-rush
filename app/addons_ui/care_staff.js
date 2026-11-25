/* Care requests, staff side. No global side effects except window.CareStaff.
   CareStaff.init(root, {endpoint:'/api/care', volunteer:'Meera' | () => 'Meera', stop:'g3' | () => 'g3', lang:'ml' | () => 'ml', pollMs:4000,
                         onMapItems: function (items) {}})  items: [{id, stop_id, urgency, category}] for pins on the site-overview map.
   Plays an alert tone and vibrates when a NEW emergency appears. */
(function () {
  'use strict';
  var LBL = {
    en: {medical: 'Medical', lost_person: 'Lost person', lost_item: 'Lost item', safety_crowd: 'Crowd safety', harassment_theft: 'Harassment or theft', tout_payment: 'Asking for money', accessibility: 'Wheelchair or elder help', water_toilet_clean: 'Water, toilet, cleanliness', slot_booking: 'Slot or booking', staff_behaviour: 'Staff behaviour', suggestion: 'Suggestion', other: 'Other'},
    hi: {medical: 'स्वास्थ्य', lost_person: 'खोया व्यक्ति', lost_item: 'खोया सामान', safety_crowd: 'भीड़ सुरक्षा', harassment_theft: 'परेशानी या चोरी', tout_payment: 'पैसे मांग रहा', accessibility: 'व्हीलचेयर या बुज़ुर्ग', water_toilet_clean: 'पानी, शौचालय, सफ़ाई', slot_booking: 'स्लॉट या बुकिंग', staff_behaviour: 'स्टाफ़ व्यवहार', suggestion: 'सुझाव', other: 'अन्य'},
    te: {medical: 'ఆరోగ్యం', lost_person: 'తప్పిపోయిన వ్యక్తి', lost_item: 'పోయిన వస్తువు', safety_crowd: 'రద్దీ భద్రత', harassment_theft: 'వేధింపు లేదా దొంగతనం', tout_payment: 'డబ్బు అడుగుతున్నారు', accessibility: 'వీల్‌చైర్ లేదా పెద్దవారు', water_toilet_clean: 'నీరు, టాయిలెట్, శుభ్రత', slot_booking: 'స్లాట్ లేదా బుకింగ్', staff_behaviour: 'సిబ్బంది ప్రవర్తన', suggestion: 'సూచన', other: 'ఇతరం'},
    ta: {medical: 'உடல்நலம்', lost_person: 'காணாமல் போனவர்', lost_item: 'தொலைந்த பொருள்', safety_crowd: 'கூட்டப் பாதுகாப்பு', harassment_theft: 'தொந்தரவு அல்லது திருட்டு', tout_payment: 'பணம் கேட்கிறார்', accessibility: 'சக்கர நாற்காலி அல்லது முதியவர்', water_toilet_clean: 'தண்ணீர், கழிப்பறை, தூய்மை', slot_booking: 'ஸ்லாட் அல்லது முன்பதிவு', staff_behaviour: 'பணியாளர் நடத்தை', suggestion: 'ஆலோசனை', other: 'மற்றவை'},
    ml: {medical: 'ആരോഗ്യം', lost_person: 'കാണാതായ ആൾ', lost_item: 'നഷ്ടപ്പെട്ട സാധനം', safety_crowd: 'തിരക്ക് സുരക്ഷ', harassment_theft: 'ശല്യം അല്ലെങ്കിൽ മോഷണം', tout_payment: 'പണം ചോദിക്കുന്നു', accessibility: 'വീൽചെയർ അല്ലെങ്കിൽ പ്രായമായവർ', water_toilet_clean: 'വെള്ളം, ടോയ്‌ലറ്റ്, ശുചിത്വം', slot_booking: 'സ്ലോട്ട് അല്ലെങ്കിൽ ബുക്കിംഗ്', staff_behaviour: 'ജീവനക്കാരുടെ പെരുമാറ്റം', suggestion: 'നിർദ്ദേശം', other: 'മറ്റുള്ളവ'},
    kn: {medical: 'ಆರೋಗ್ಯ', lost_person: 'ಕಳೆದುಹೋದ ವ್ಯಕ್ತಿ', lost_item: 'ಕಳೆದುಹೋದ ವಸ್ತು', safety_crowd: 'ಜನಸಂದಣಿ ಸುರಕ್ಷತೆ', harassment_theft: 'ಕಿರುಕುಳ ಅಥವಾ ಕಳ್ಳತನ', tout_payment: 'ಹಣ ಕೇಳುತ್ತಿದ್ದಾರೆ', accessibility: 'ವೀಲ್‌ಚೇರ್ ಅಥವಾ ಹಿರಿಯರು', water_toilet_clean: 'ನೀರು, ಶೌಚಾಲಯ, ಸ್ವಚ್ಛತೆ', slot_booking: 'ಸ್ಲಾಟ್ ಅಥವಾ ಬುಕಿಂಗ್', staff_behaviour: 'ಸಿಬ್ಬಂದಿ ವರ್ತನೆ', suggestion: 'ಸಲಹೆ', other: 'ಇತರೆ'}
  };
  var UI = {
    en: {open: 'open', em: 'emergencies', med: 'median response', go: 'I am going', done: 'Resolved', cannot: 'Cannot', play: 'Hear their words', none: 'No requests right now.', ci: 'Check in here', name: 'Your name', emergency: 'EMERGENCY', urgent: 'Urgent', normal: 'Normal', min: 'min', stops: 'stops away', here: 'at your stop', wait: 'waiting', note: 'Note for the pilgrim (optional)', why: 'Why can you not help?', sim: 'Simulated volunteers are shown for the demo.'},
    hi: {open: 'खुले', em: 'आपातकाल', med: 'औसत प्रतिक्रिया', go: 'मैं जा रहा हूँ', done: 'हो गया', cannot: 'नहीं कर सकता', play: 'उनकी आवाज़ सुनें', none: 'अभी कोई अनुरोध नहीं।', ci: 'यहाँ चेक-इन', name: 'आपका नाम', emergency: 'आपातकाल', urgent: 'ज़रूरी', normal: 'सामान्य', min: 'मिनट', stops: 'पड़ाव दूर', here: 'आपके पड़ाव पर', wait: 'इंतज़ार', note: 'यात्री के लिए संदेश (वैकल्पिक)', why: 'आप मदद क्यों नहीं कर सकते?', sim: 'डेमो के लिए नकली स्वयंसेवक दिखाए गए हैं।'},
    te: {open: 'ఓపెన్', em: 'అత్యవసరాలు', med: 'సగటు స్పందన', go: 'నేను వెళ్తున్నాను', done: 'పూర్తయింది', cannot: 'చేయలేను', play: 'వారి మాటలు వినండి', none: 'ప్రస్తుతం అభ్యర్థనలు లేవు.', ci: 'ఇక్కడ చెక్-ఇన్', name: 'మీ పేరు', emergency: 'అత్యవసరం', urgent: 'అత్యవసరమే', normal: 'సాధారణం', min: 'ని.', stops: 'స్టాప్‌ల దూరం', here: 'మీ స్టాప్‌లోనే', wait: 'వేచి ఉన్నారు', note: 'యాత్రికునికి గమనిక (ఐచ్ఛికం)', why: 'మీరు ఎందుకు సహాయం చేయలేరు?', sim: 'డెమో కోసం నకిలీ వాలంటీర్లు చూపబడ్డారు.'},
    ta: {open: 'திறந்தவை', em: 'அவசரம்', med: 'சராசரி பதில்', go: 'நான் போகிறேன்', done: 'முடிந்தது', cannot: 'முடியாது', play: 'அவர்கள் பேசியதைக் கேளுங்கள்', none: 'இப்போது கோரிக்கைகள் இல்லை.', ci: 'இங்கே செக்-இன்', name: 'உங்கள் பெயர்', emergency: 'அவசரம்', urgent: 'அவசரமானது', normal: 'சாதாரணம்', min: 'நிமிடம்', stops: 'நிறுத்தங்கள் தூரம்', here: 'உங்கள் நிறுத்தத்தில்', wait: 'காத்திருப்பு', note: 'யாத்ரீகருக்கான குறிப்பு (விருப்பம்)', why: 'ஏன் உதவ முடியாது?', sim: 'டெமோவுக்காக போலி தன்னார்வலர்கள் காட்டப்படுகின்றனர்.'},
    ml: {open: 'തുറന്നവ', em: 'അടിയന്തരം', med: 'ശരാശരി പ്രതികരണം', go: 'ഞാൻ പോകുന്നു', done: 'തീർന്നു', cannot: 'പറ്റില്ല', play: 'അവരുടെ വാക്കുകൾ കേൾക്കൂ', none: 'ഇപ്പോൾ അപേക്ഷകളില്ല.', ci: 'ഇവിടെ ചെക്ക്-ഇൻ', name: 'നിങ്ങളുടെ പേര്', emergency: 'അടിയന്തരം', urgent: 'അത്യാവശ്യം', normal: 'സാധാരണം', min: 'മിനിറ്റ്', stops: 'സ്റ്റോപ്പ് അകലെ', here: 'നിങ്ങളുടെ സ്റ്റോപ്പിൽ', wait: 'കാത്തിരിപ്പ്', note: 'തീർത്ഥാടകനുള്ള കുറിപ്പ് (ഓപ്ഷണൽ)', why: 'എന്തുകൊണ്ട് സഹായിക്കാൻ കഴിയില്ല?', sim: 'ഡെമോയ്ക്കായി സിമുലേറ്റഡ് വോളന്റിയർമാരെ കാണിക്കുന്നു.'},
    kn: {open: 'ತೆರೆದಿವೆ', em: 'ತುರ್ತು', med: 'ಸರಾಸರಿ ಪ್ರತಿಕ್ರಿಯೆ', go: 'ನಾನು ಹೋಗುತ್ತಿದ್ದೇನೆ', done: 'ಮುಗಿದಿದೆ', cannot: 'ಸಾಧ್ಯವಿಲ್ಲ', play: 'ಅವರ ಮಾತು ಕೇಳಿ', none: 'ಈಗ ವಿನಂತಿಗಳಿಲ್ಲ.', ci: 'ಇಲ್ಲಿ ಚೆಕ್-ಇನ್', name: 'ನಿಮ್ಮ ಹೆಸರು', emergency: 'ತುರ್ತು', urgent: 'ಅಗತ್ಯ', normal: 'ಸಾಮಾನ್ಯ', min: 'ನಿಮಿಷ', stops: 'ನಿಲ್ದಾಣ ದೂರ', here: 'ನಿಮ್ಮ ನಿಲ್ದಾಣದಲ್ಲಿ', wait: 'ಕಾಯುತ್ತಿದ್ದಾರೆ', note: 'ಯಾತ್ರಿಗೆ ಟಿಪ್ಪಣಿ (ಐಚ್ಛಿಕ)', why: 'ನೀವು ಏಕೆ ಸಹಾಯ ಮಾಡಲಾಗದು?', sim: 'ಡೆಮೊಗಾಗಿ ಅನುಕರಣೆ ಸ್ವಯಂಸೇವಕರನ್ನು ತೋರಿಸಲಾಗಿದೆ.'}
  };
  var STOPS = [['g1', 'Base Camp'], ['g2', 'River Crossing'], ['g3', 'Forest Path'], ['g4', 'Queue Complex'], ['g5', 'Main Steps']];
  function q(root, k) { return root.querySelector('[data-cs="' + k + '"]'); }
  function val(v, d) { return typeof v === 'function' ? v() : (v == null ? d : v); }
  function mins(s) { return s == null ? '-' : (s < 90 ? Math.round(s) + 's' : Math.round(s / 60) + 'm'); }

  function init(root, opts) {
    opts = opts || {};
    var ep = opts.endpoint || '/api/care', pollMs = opts.pollMs || 4000;
    var lang = function () { return val(opts.lang, 'en'); };
    var T = function () { return UI[lang()] || UI.en; }, L = function () { return LBL[lang()] || LBL.en; };
    var me = {volunteer: val(opts.volunteer, ''), stop: val(opts.stop, 'g1')};
    var list = q(root, 'list'), note = q(root, 'note'), audio = q(root, 'audio'), sel = q(root, 'stopsel'), nameIn = q(root, 'name');
    var seen = {}, first = true, actx = null, timer = null;
    STOPS.forEach(function (s) { var o = document.createElement('option'); o.value = s[0]; o.textContent = s[1]; sel.appendChild(o); });
    sel.value = me.stop; nameIn.value = me.volunteer || '';

    function labels() {
      var t = T();
      q(root, 'l-open').textContent = t.open; q(root, 'l-em').textContent = t.em; q(root, 'l-med').textContent = t.med;
      nameIn.placeholder = t.name; q(root, 'cibtn').textContent = t.ci;
    }
    function beep() {
      try {
        actx = actx || new (window.AudioContext || window.webkitAudioContext)();
        [0, 0.28, 0.56].forEach(function (d) {
          var o = actx.createOscillator(), g = actx.createGain(); o.type = 'square'; o.frequency.value = 880;
          g.gain.value = 0.15; o.connect(g); g.connect(actx.destination); o.start(actx.currentTime + d); o.stop(actx.currentTime + d + 0.18);
        });
      } catch (e) {}
      if (navigator.vibrate) { try { navigator.vibrate([300, 120, 300, 120, 600]); } catch (e) {} }
    }
    function api(path, body) {
      return fetch(ep + path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body || {})}).then(function (r) { return r.json(); });
    }
    function item(r) {
      var t = T(), li = document.createElement('li'); li.className = 'cs-item'; li.dataset.urg = r.urgency; li.dataset.id = r.id;
      var dist = r.distance_stops == null ? '' : (r.distance_stops === 0 ? t.here : r.distance_stops + ' ' + t.stops);
      var mine = r.assigned_to && r.assigned_to.name === me.volunteer;
      li.innerHTML = '<div class="cs-top"><span class="cs-id"></span><span class="cs-tag"></span></div><p class="cs-sum"></p><p class="cs-en"></p><p class="cs-words"></p><p class="cs-meta"></p>';
      li.querySelector('.cs-id').textContent = r.id;
      li.querySelector('.cs-tag').textContent = r.urgency === 'emergency' ? t.emergency : r.urgency === 'urgent' ? t.urgent : t.normal;
      li.querySelector('.cs-sum').textContent = L()[r.category] + (r.stop_name ? ' · ' + r.stop_name : '');
      li.querySelector('.cs-en').textContent = lang() === 'en' ? '' : r.summary_en;
      li.querySelector('.cs-words').textContent = r.transcript ? '“' + r.transcript + '”' : '';
      li.querySelector('.cs-meta').textContent = [dist, mins(r.waiting_s) + ' ' + t.wait, r.assigned_to ? r.assigned_to.name + (r.assigned_to.simulated ? ' (sim)' : '') : '', r.escalated ? 'escalated' : ''].filter(Boolean).join(' · ');
      if (r.audio_url) {
        var p = document.createElement('button'); p.type = 'button'; p.className = 'cs-play'; p.textContent = '▶ ' + t.play;
        p.addEventListener('click', function () { audio.src = r.audio_url; audio.play().catch(function () {}); }); li.appendChild(p);
      }
      var b = document.createElement('div'); b.className = 'cs-btns';
      var go = document.createElement('button'); go.type = 'button'; go.className = 'cs-go'; go.textContent = t.go + (r.status === 'on_the_way' && mine ? ' ✓' : '');
      var ok = document.createElement('button'); ok.type = 'button'; ok.textContent = t.done;
      var no = document.createElement('button'); no.type = 'button'; no.textContent = t.cannot;
      go.addEventListener('click', function () { api('/' + r.id + '/onway', {volunteer: me.volunteer}).then(refresh); });
      ok.addEventListener('click', function () { var n = window.prompt ? window.prompt(t.note, '') : ''; if (n === null) return; api('/' + r.id + '/resolve', {volunteer: me.volunteer, note: n || ''}).then(refresh); });
      no.addEventListener('click', function () { var n = window.prompt ? window.prompt(t.why, '') : ''; if (n === null) return; api('/' + r.id + '/cannot', {volunteer: me.volunteer, reason: n || ''}).then(refresh); });
      b.appendChild(go); b.appendChild(ok); b.appendChild(no); li.appendChild(b);
      return li;
    }
    function refresh() {
      labels();
      var url = ep + '/open?stop=' + encodeURIComponent(me.stop) + (me.volunteer ? '&volunteer=' + encodeURIComponent(me.volunteer) : '');
      return fetch(url).then(function (r) { return r.json(); }).then(function (j) {
        var rs = j.requests || [], s = j.stats || {};
        q(root, 's-open').textContent = s.open || 0; q(root, 's-em').textContent = s.open_emergencies || 0; q(root, 's-med').textContent = mins(s.median_ack_s);
        list.textContent = '';
        if (!rs.length) { var e = document.createElement('li'); e.className = 'cs-empty'; e.textContent = T().none; list.appendChild(e); }
        var fresh = false;
        rs.forEach(function (r) { list.appendChild(item(r)); if (!seen[r.id]) { seen[r.id] = 1; if (r.urgency === 'emergency') fresh = true; } });
        if (fresh && !first) beep();
        first = false;
        note.textContent = (s.simulated_roster ? T().sim : '');
        if (opts.onMapItems) { try { opts.onMapItems(rs.map(function (r) { return {id: r.id, stop_id: r.stop_id, urgency: r.urgency, category: r.category, status: r.status}; })); } catch (e) {} }
      }).catch(function () { note.textContent = 'No connection to the help service.'; });
    }
    q(root, 'checkin').addEventListener('submit', function (e) {
      e.preventDefault();
      me.volunteer = nameIn.value.trim() || me.volunteer; me.stop = sel.value;
      if (!me.volunteer) { nameIn.focus(); return; }
      api('/checkin', {volunteer: me.volunteer, stop: me.stop, languages: [lang(), 'en']}).then(refresh);
    });
    sel.addEventListener('change', function () { me.stop = sel.value; refresh(); });
    refresh(); timer = setInterval(refresh, pollMs);
    return {refresh: refresh, stop: function () { clearInterval(timer); }, setVolunteer: function (n, s) { me.volunteer = n; if (s) { me.stop = s; sel.value = s; } refresh(); }};
  }
  window.CareStaff = {init: init, LABELS: LBL, UI: UI};
})();

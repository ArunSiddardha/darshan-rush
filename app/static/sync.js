/* Pilgrim page: shared-state sync (GET /api/state every 1.5 s), the quiet "you can ask about" line and "I need help".
   Uses window.DR exposed by app.js (uid, lang, SM, loadFlags, restore, pollQueue). */
(function(){
const ASK={en:['You can ask about',['slots','waiting times','the way','water and toilets','medical help','help for elders','what to carry','buses']],
 hi:['आप पूछ सकते हैं',['स्लॉट','इंतज़ार का समय','रास्ता','पानी और शौचालय','चिकित्सा सहायता','बुज़ुर्गों के लिए मदद','क्या साथ लाएँ','बसें']],
 te:['మీరు అడగవచ్చు',['స్లాట్లు','వేచి ఉండే సమయం','దారి','నీళ్ళు, మరుగుదొడ్లు','వైద్య సహాయం','పెద్దవారికి సహాయం','ఏమి తీసుకురావాలి','బస్సులు']],
 ta:['நீங்கள் கேட்கலாம்',['ஸ்லாட்','காத்திருப்பு நேரம்','வழி','தண்ணீர், கழிப்பறை','மருத்துவ உதவி','முதியோருக்கு உதவி','என்ன கொண்டு வர வேண்டும்','பேருந்துகள்']],
 ml:['നിങ്ങൾക്ക് ചോദിക്കാം',['സ്ലോട്ടുകൾ','കാത്തിരിപ്പ് സമയം','വഴി','വെള്ളം, ശൗചാലയം','വൈദ്യസഹായം','പ്രായമായവർക്കുള്ള സഹായം','എന്ത് കൊണ്ടുവരണം','ബസുകൾ']],
 kn:['ನೀವು ಕೇಳಬಹುದು',['ಸ್ಲಾಟ್‌ಗಳು','ಕಾಯುವ ಸಮಯ','ದಾರಿ','ನೀರು, ಶೌಚಾಲಯ','ವೈದ್ಯಕೀಯ ಸಹಾಯ','ಹಿರಿಯರಿಗೆ ಸಹಾಯ','ಏನು ತರಬೇಕು','ಬಸ್ಸುಗಳು']]};
const HELP={en:['I need help','A volunteer has been told. Please stay where you are.'],hi:['मुझे मदद चाहिए','स्वयंसेवक को बता दिया गया है। कृपया वहीं रुकिए।'],
 te:['నాకు సహాయం కావాలి','వాలంటీర్ కి తెలియజేశాం. దయచేసి అక్కడే ఉండండి.'],ta:['எனக்கு உதவி வேண்டும்','தன்னார்வலருக்கு தெரிவிக்கப்பட்டது. தயவுசெய்து அங்கேயே இருங்கள்.'],
 ml:['എനിക്ക് സഹായം വേണം','വോളന്റിയറെ അറിയിച്ചു. ദയവായി അവിടെത്തന്നെ നിൽക്കൂ.'],kn:['ನನಗೆ ಸಹಾಯ ಬೇಕು','ಸ್ವಯಂಸೇವಕರಿಗೆ ತಿಳಿಸಲಾಗಿದೆ. ದಯವಿಟ್ಟು ಅಲ್ಲೇ ಇರಿ.']};
const FAIL={en:'Could not reach the volunteers. Please go to the nearest information counter.',hi:'स्वयंसेवकों तक नहीं पहुँच सके। कृपया पास के सूचना काउंटर पर जाइए।',te:'వాలంటీర్లను చేరలేకపోయాం. దయచేసి దగ్గరలోని సమాచార కౌంటర్ కి వెళ్ళండి.',ta:'தன்னார்வலர்களை அடைய முடியவில்லை. அருகிலுள்ள தகவல் கவுண்டருக்கு செல்லுங்கள்.',ml:'വോളന്റിയർമാരെ അറിയിക്കാനായില്ല. അടുത്തുള്ള ഇൻഫർമേഷൻ കൗണ്ടറിലേക്ക് പോകൂ.',kn:'ಸ್ವಯಂಸೇವಕರನ್ನು ತಲುಪಲಾಗಲಿಲ್ಲ. ಹತ್ತಿರದ ಮಾಹಿತಿ ಕೌಂಟರ್‌ಗೆ ಹೋಗಿ.'};
const RUSH={en:'Rush mode: staggered slots',hi:'भीड़ मोड: स्लॉट बारी-बारी से',te:'రద్దీ సమయం: స్లాట్లు విడతలుగా',ta:'நெரிசல் நேரம்: ஸ்லாட்கள் இடைவெளியில்',ml:'തിരക്ക് സമയം: സ്ലോട്ടുകൾ ഇടവിട്ട്',kn:'ಜನದಟ್ಟಣೆ: ಸ್ಲಾಟ್‌ಗಳು ಹಂತ ಹಂತವಾಗಿ'};
const D=()=>window.DR||{};const L=()=>ASK[D().lang]?D().lang:'en';
const ex=document.getElementById('examples');let i=0;
const can=document.createElement('p');can.className='canask';can.id='canask';if(ex)ex.after(can);
function showAsk(){const k=L(),a=ASK[k],n=a[1].length,pick=[0,1,2].map(j=>a[1][(i+j)%n]);i=(i+3)%n;can.lang=k;can.classList.remove('in');
 setTimeout(()=>{can.textContent=a[0]+': '+pick.join(', ');can.classList.add('in')},150)}
showAsk();if(!matchMedia('(prefers-reduced-motion:reduce)').matches)setInterval(showAsk,3600);
/* rush line */
const rush=document.createElement('p');rush.className='rushline';rush.hidden=true;if(can)can.after(rush);
/* I need help */
const alt=document.getElementById('alt');const hb=document.createElement('button');hb.type='button';hb.className='btn btn-quiet needhelp';hb.id='needHelp';
const hd=document.createElement('p');hd.className='small helpdone';hd.hidden=true;
const ml=document.getElementById('mapLink');if(ml){ml.after(hb);hb.after(hd)}else if(alt){alt.appendChild(hb);alt.after(hd)}
function helpText(){hb.textContent=HELP[L()][0];hb.lang=L()}
helpText();
hb.onclick=async()=>{hb.disabled=true;let ok=false;
 const pos=(LAST&&LAST.position)||null;
 let line='';try{const r=await fetch('/api/care',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({uid:D().uid,lang:L(),stop:pos,position:pos,text:'I need help',choice:'other'})});const j=await r.json().catch(()=>({}));if(r.ok&&j.id){ok=true;line=j.reply_text||''}}catch(e){}
 if(!ok){try{const r=await fetch('/api/staff/help',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid:D().uid,stop:pos,text:'Pilgrim tapped I need help'})});ok=r.ok}catch(e){}}
 hd.hidden=false;hd.lang=L();hd.textContent=ok?(line||HELP[L()][1]):FAIL[L()];
 setTimeout(()=>{hb.disabled=false},8000)};
/* shared state */
let LAST=null,lastFlags='',lastSlot='',lastPos='';
async function tick(){try{const r=await fetch('/api/state?role=pilgrim&uid='+encodeURIComponent(D().uid||'anon')+'&lang='+L());if(!r.ok)return;const G=await r.json();LAST=G;
 const fk=JSON.stringify(G.flags||{});if(lastFlags&&fk!==lastFlags){try{D().loadFlags();D().pollQueue()}catch(e){}}lastFlags=fk;
 const sk=JSON.stringify(G.slot&&G.slot.label||'');if(lastSlot&&sk!==lastSlot){try{D().restore(true)}catch(e){}}lastSlot=sk;
 const pk=G.position||'';const SM=D().SM;if(pk&&pk!==lastPos&&SM){try{SM.setPos(pk,true);SM.render()}catch(e){}}lastPos=pk;
 rush.hidden=!G.rush_line;rush.textContent=RUSH[L()];rush.lang=L()}catch(e){}}
tick();setInterval(tick,1500);
let lk=L();setInterval(()=>{if(L()!==lk){lk=L();helpText();showAsk()}},800);
})();

const $=s=>document.querySelector(s);
const uid=localStorage.uid||(localStorage.uid=(crypto.randomUUID?crypto.randomUUID():String(Math.random()).slice(2)));
let exposed=false,lang=localStorage.lang||'en',F={},Q={gates:[]},mine=null,mySlot=null,rec=null,chunks=[],spokenLite=false;
const LN={ml:'മലയാളം',ta:'தமிழ்',te:'తెలుగు',kn:'ಕನ್ನಡ',hi:'हिन्दी',en:'English'};
const T={
 en:{tag:'Book a darshan slot by speaking in your language.',hint:'Tap and speak',rec:'Listening... tap again',book:'Book my darshan slot',reached:'I reached the gate',play:'Play slot',gates:'Gates and waiting time',min:'min',send:'Send',
  lite:'Heavy crowd. Showing a simple list. Booking continues.',stag:'Slots are staggered so everyone gets a fair time.',slot:'Your slot',gate:'Gate',thanks:'Noted. Thank you.',empty:'Live crowd data is starting. Please wait a moment.',nov:'Voice unavailable (Sarvam credits). Type instead.',nomic:'Microphone not available. Type instead.',busy:'Booking is busy. Please try again.'},
 ml:{tag:'നിങ്ങളുടെ ഭാഷയിൽ സംസാരിച്ച് ദർശന സ്ലോട്ട് ബുക്ക് ചെയ്യൂ.',hint:'സംസാരിക്കാൻ അമർത്തുക',rec:'കേൾക്കുന്നു... വീണ്ടും അമർത്തുക',book:'എന്റെ ദർശന സ്ലോട്ട് ബുക്ക് ചെയ്യുക',reached:'ഞാൻ ഗേറ്റിൽ എത്തി',play:'സ്ലോട്ട് കേൾക്കുക',gates:'ഗേറ്റുകളും കാത്തിരിപ്പ് സമയവും',min:'മിനിറ്റ്',send:'അയയ്ക്കുക',
  lite:'തിരക്ക് കൂടുതലാണ്. ലളിതമായ പട്ടിക കാണിക്കുന്നു. ബുക്കിംഗ് തുടരാം.',stag:'എല്ലാവർക്കും ന്യായമായ സമയം ലഭിക്കാൻ സ്ലോട്ടുകൾ ഇടവിട്ടാണ്.',slot:'നിങ്ങളുടെ സ്ലോട്ട്',gate:'ഗേറ്റ്',thanks:'രേഖപ്പെടുത്തി. നന്ദി.',empty:'തത്സമയ വിവരം ഉടൻ വരും. ഒരു നിമിഷം കാത്തിരിക്കൂ.',nov:'Voice unavailable (Sarvam credits). Type instead.',nomic:'മൈക്ക് ലഭ്യമല്ല. ടൈപ്പ് ചെയ്യൂ.',busy:'ബുക്കിംഗ് തിരക്കിലാണ്. വീണ്ടും ശ്രമിക്കൂ.'},
 ta:{tag:'உங்கள் மொழியில் பேசி தரிசன நேரத்தை பதிவு செய்யுங்கள்.',hint:'பேச அழுத்தவும்',rec:'கேட்கிறேன்... மீண்டும் அழுத்தவும்',book:'என் தரிசன நேரத்தை பதிவு செய்',reached:'நான் வாயிலை அடைந்தேன்',play:'நேரத்தை கேள்',gates:'வாயில்களும் காத்திருப்பு நேரமும்',min:'நிமிடம்',send:'அனுப்பு',
  lite:'கூட்டம் அதிகம். எளிய பட்டியல் காட்டப்படுகிறது. முன்பதிவு தொடரலாம்.',stag:'அனைவருக்கும் நியாயமான நேரம் கிடைக்க நேரங்கள் இடைவெளியுடன் வழங்கப்படுகின்றன.',slot:'உங்கள் நேரம்',gate:'வாயில்',thanks:'பதிவு செய்யப்பட்டது. நன்றி.',empty:'நேரடி தகவல் விரைவில் வரும். சற்று காத்திருங்கள்.',nov:'Voice unavailable (Sarvam credits). Type instead.',nomic:'மைக் கிடைக்கவில்லை. தட்டச்சு செய்யுங்கள்.',busy:'முன்பதிவு பரபரப்பாக உள்ளது. மீண்டும் முயலுங்கள்.'},
 te:{tag:'మీ భాషలో మాట్లాడి దర్శన స్లాట్ బుక్ చేసుకోండి.',hint:'మాట్లాడటానికి నొక్కండి',rec:'వింటున్నాను... మళ్లీ నొక్కండి',book:'నా దర్శన స్లాట్ బుక్ చేయండి',reached:'నేను గేటుకు చేరుకున్నాను',play:'స్లాట్ వినండి',gates:'గేట్లు, వేచి ఉండే సమయం',min:'నిమిషాలు',send:'పంపండి',
  lite:'రద్దీ ఎక్కువగా ఉంది. సరళమైన జాబితా చూపిస్తున్నాం. బుకింగ్ కొనసాగుతుంది.',stag:'అందరికీ న్యాయంగా సమయం దొరకడానికి స్లాట్లు విడతలుగా ఇస్తున్నాం.',slot:'మీ స్లాట్',gate:'గేటు',thanks:'నమోదైంది. ధన్యవాదాలు.',empty:'ప్రత్యక్ష సమాచారం త్వరలో వస్తుంది. కొంచెం ఆగండి.',nov:'Voice unavailable (Sarvam credits). Type instead.',nomic:'మైక్ అందుబాటులో లేదు. టైప్ చేయండి.',busy:'బుకింగ్ రద్దీగా ఉంది. మళ్లీ ప్రయత్నించండి.'},
 kn:{tag:'ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಮಾತನಾಡಿ ದರ್ಶನ ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ.',hint:'ಮಾತನಾಡಲು ಒತ್ತಿ',rec:'ಕೇಳುತ್ತಿದ್ದೇನೆ... ಮತ್ತೆ ಒತ್ತಿ',book:'ನನ್ನ ದರ್ಶನ ಸ್ಲಾಟ್ ಬುಕ್ ಮಾಡಿ',reached:'ನಾನು ಗೇಟ್ ತಲುಪಿದೆ',play:'ಸ್ಲಾಟ್ ಕೇಳಿ',gates:'ಗೇಟ್‌ಗಳು ಮತ್ತು ಕಾಯುವ ಸಮಯ',min:'ನಿಮಿಷ',send:'ಕಳುಹಿಸಿ',
  lite:'ಜನದಟ್ಟಣೆ ಹೆಚ್ಚಿದೆ. ಸರಳ ಪಟ್ಟಿ ತೋರಿಸಲಾಗುತ್ತಿದೆ. ಬುಕಿಂಗ್ ಮುಂದುವರಿಯುತ್ತದೆ.',stag:'ಎಲ್ಲರಿಗೂ ನ್ಯಾಯಯುತ ಸಮಯ ಸಿಗಲು ಸ್ಲಾಟ್‌ಗಳನ್ನು ಅಂತರದಲ್ಲಿ ನೀಡಲಾಗುತ್ತಿದೆ.',slot:'ನಿಮ್ಮ ಸ್ಲಾಟ್',gate:'ಗೇಟ್',thanks:'ದಾಖಲಾಯಿತು. ಧನ್ಯವಾದ.',empty:'ಲೈವ್ ಮಾಹಿತಿ ಶೀಘ್ರ ಬರುತ್ತದೆ. ಸ್ವಲ್ಪ ಕಾಯಿರಿ.',nov:'Voice unavailable (Sarvam credits). Type instead.',nomic:'ಮೈಕ್ ಲಭ್ಯವಿಲ್ಲ. ಟೈಪ್ ಮಾಡಿ.',busy:'ಬುಕಿಂಗ್ ಬ್ಯುಸಿಯಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.'},
 hi:{tag:'अपनी भाषा में बोलकर दर्शन स्लॉट बुक करें।',hint:'बोलने के लिए दबाइए',rec:'सुन रहा हूँ... फिर दबाइए',book:'मेरा दर्शन स्लॉट बुक करें',reached:'मैं गेट पर पहुँच गया',play:'स्लॉट सुनें',gates:'गेट और प्रतीक्षा समय',min:'मिनट',send:'भेजें',
  lite:'भीड़ ज़्यादा है। सरल सूची दिखाई जा रही है। बुकिंग जारी है।',stag:'सबको उचित समय मिले, इसलिए स्लॉट अलग-अलग समय पर दिए जा रहे हैं।',slot:'आपका स्लॉट',gate:'गेट',thanks:'दर्ज हो गया। धन्यवाद।',empty:'लाइव जानकारी जल्द आएगी। कृपया प्रतीक्षा करें।',nov:'Voice unavailable (Sarvam credits). Type instead.',nomic:'माइक उपलब्ध नहीं है। टाइप करें।',busy:'बुकिंग में भीड़ है। फिर कोशिश करें।'}
};
const t=k=>(T[lang]&&T[lang][k])||T.en[k];
const val=x=>x&&typeof x==='object'?(x.value!==undefined?x.value:x.enabled):x;
const flag=n=>val(F[n]!==undefined?F[n]:(F.flags&&F.flags[n]));
const isLite=()=>(Q.map_mode||flag('map_mode'))==='lite';
const isStag=()=>flag('slot_mode')==='staggered'||(mySlot&&mySlot.mode==='staggered');
const gname=id=>{const g=(Q.gates||[]).find(x=>x.id===id);return g?(g.name||g.id):String(id)};

function langs(){$('#langs').innerHTML=Object.keys(LN).map(k=>`<button class="${k==lang?'on':''}" data-k="${k}" lang="${k}">${LN[k]}</button>`).join('');
 document.querySelectorAll('#langs button').forEach(b=>b.onclick=()=>{lang=b.dataset.k;localStorage.lang=lang;spokenLite=false;langs();text();poll();});}
function text(){document.documentElement.lang=lang;$('#tag').textContent=t('tag');$('#hint').textContent=rec?t('rec'):t('hint');$('#book').textContent=t('book');$('#reached').textContent=t('reached');$('#play').textContent=t('play');$('#gatesh').textContent=t('gates');$('#go').textContent=t('send');banner();renderQ();renderSlot();}
function play(b64){if(!b64)return false;const p=$('#player');p.src='data:audio/wav;base64,'+b64;p.play().catch(()=>{});return true}
function banner(){const b=$('#banner');if(isLite()){b.innerHTML=t('lite');b.classList.add('show')}else b.classList.remove('show');
 $('#staggernote').textContent=isStag()?t('stag'):'';}
function renderQ(){
 const gs=Q.gates||[];const lite=isLite();document.body.classList.toggle('lite',lite);
 if(!gs.length){$('#strip').innerHTML=`<div class="empty" style="grid-column:1/-1">${t('empty')}</div>`;DarshanMap.update([],{mode:'lite'});$('#litelist').innerHTML='';return}
 const bestId=gs.reduce((a,g)=>a==null||g.wait_min<a.wait_min?g:a,null).id;
 $('#strip').innerHTML=gs.slice(0,5).map(g=>{const l=DarshanMap.norm(g.load);const c=l>.66?'high':l>.33?'mid':'';
  return `<div class="gate ${c} ${g.id===bestId?'best':''}"><div class="gn">${esc(g.name||g.id)}</div><div class="w">${g.wait_min}</div><div class="u">${t('min')}</div><div class="bar"><i style="width:${Math.max(6,l*100)}%"></i></div></div>`}).join('');
 $('#litelist').innerHTML=gs.map(g=>`<div><span>${esc(g.name||g.id)}</span><b>${g.wait_min} ${t('min')}</b></div>`).join('');
 DarshanMap.update(gs,{mode:lite?'lite':'full',best:bestId,mine:mySlot&&mySlot.gate});
}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function renderSlot(){const c=$('#slot');if(!mySlot){c.classList.remove('show');return}
 c.classList.add('show');$('#slotwhen').textContent=mySlot.time||'';$('#slotwhere').textContent=t('slot')+': '+gname(mySlot.gate);}
async function loadFlags(){try{const r=await fetch('/api/flags?uid='+uid+'&lang='+lang+(exposed?'&expose=0':''));if(r.ok){F=await r.json();exposed=true;
  const v=flag('voice_directions');document.body.dataset.variant=(v==='map')?'map':'voice';banner()}}catch(e){}}
async function pollQueue(){try{const r=await fetch(`/api/queue?uid=${uid}&lang=${lang}`);if(!r.ok)throw 0;Q=await r.json();}catch(e){Q={gates:[]}}
 banner();renderQ();
 if(isLite()&&!spokenLite){spokenLite=true;}}
function poll(){loadFlags();pollQueue()}

function slotFrom(j,gate){let s=j.slot;if(!s)return null;if(typeof s!=='object')s={time:String(s)};
 return {gate:s.gate||gate,time:s.label||s.time||s.start||s.slot||'',id:s.id,mode:j.mode||s.mode}}
$('#book').onclick=async()=>{
 const gs=Q.gates||[];if(!gs.length){$('#hint').textContent=t('empty');return}
 const g=gs.reduce((a,x)=>x.wait_min<a.wait_min?x:a);const b=$('#book');b.disabled=true;
 try{const r=await fetch('/api/slots/book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid,gate:g.id,lang})});
  if(!r.ok)throw 0;const j=await r.json();mySlot=slotFrom(j,g.id);mySlot.mode=j.mode;
  $('#slotnote').textContent=j.mode==='staggered'?t('stag'):'';banner();renderSlot();renderQ();readback();
 }catch(e){$('#hint').textContent=t('busy')}
 b.disabled=false;};
async function directions(fd){
 fd.append('uid',uid);fd.append('lang',lang);const t0=performance.now();
 let r,j={};try{r=await fetch('/api/directions',{method:'POST',body:fd});j=await r.json().catch(()=>({}))}catch(e){$('#lat').innerHTML='<span class="err">'+t('busy')+'</span>';return null}
 const ms=Math.round(performance.now()-t0);
 if(r.status===402||/credit/i.test(j.error||j.detail||'')){$('#lat').innerHTML='<span class="err">'+T.en.nov+'</span>';return null}
 if(j.notice&&!j.audio_base64)$('#lat').innerHTML='<span class="err">'+T.en.nov+'</span>';
 if(!r.ok){$('#lat').innerHTML='<span class="err">'+esc(j.error||'error')+'</span>';return null}
 if(!j.notice)$('#lat').textContent='Voice round trip '+(ms/1000).toFixed(1)+' s';return j}
async function readback(){
 if(!mySlot)return;const fd=new FormData();
 fd.append('text',`${t('slot')}: ${gname(mySlot.gate)}, ${mySlot.time}`);fd.append('readback','1');
 const j=await directions(fd);
 if(j&&j.audio_base64){play(j.audio_base64);return}
 if(window.speechSynthesis){const u=new SpeechSynthesisUtterance(`${t('slot')}. ${gname(mySlot.gate)}. ${mySlot.time}`);u.lang={ml:'ml-IN',ta:'ta-IN',te:'te-IN',kn:'kn-IN',hi:'hi-IN',en:'en-IN'}[lang];speechSynthesis.speak(u);$('#slotnote').textContent='Read aloud by your device voice, not Sarvam.'}}
$('#play').onclick=readback;
$('#reached').onclick=async()=>{
 if(!mySlot)return;
 try{await fetch('/api/event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid,event:'reached_gate',gate:mySlot.gate})})}catch(e){}
 $('#slotnote').textContent=t('thanks');$('#reached').disabled=true};
async function sendVoice(fd){
 $('#hint').textContent='...';const j=await directions(fd);$('#hint').textContent=t('hint');if(!j)return;
 const h=$('#heard');h.style.display='block';h.innerHTML=`<b>${esc(j.transcript||'')}</b>${esc(j.reply_text||'')}`;
 play(j.audio_base64);
 if(j.slot){mySlot=slotFrom(j,j.slot.gate);renderSlot();renderQ()}}
$('#say').onsubmit=e=>{e.preventDefault();const v=$('#typed').value.trim();if(!v)return;const fd=new FormData();fd.append('text',v);sendVoice(fd)};
$('#mic').onclick=async()=>{
 if(rec){rec.stop();return}
 try{const s=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];rec=new MediaRecorder(s);
  rec.ondataavailable=e=>chunks.push(e.data);
  rec.onstop=()=>{s.getTracks().forEach(x=>x.stop());const blob=new Blob(chunks,{type:rec.mimeType||'audio/webm'});rec=null;$('#mic').classList.remove('rec');$('#hint').textContent=t('hint');
   const fd=new FormData();fd.append('audio',blob,'speech.webm');sendVoice(fd)};
  rec.start();$('#mic').classList.add('rec');$('#hint').textContent=t('rec');
 }catch(e){$('#lat').innerHTML='<span class="err">'+t('nomic')+'</span>'}};
DarshanMap.init($('#map'));langs();text();poll();
setInterval(pollQueue,3000);setInterval(loadFlags,5000);

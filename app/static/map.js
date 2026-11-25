/* Simulated site map (pilgrim page and staff overview). One module, no tile service, no real place.
   API: GET /api/map?uid=&lang= (falls back to /api/queue). Position is set by sending a sentence to /api/directions.
   Use: const m = SiteMap.create(el, {uid, lang:()=>'en', mode:()=>'full'|'lite', compact:false, staff:false, onTake(stop), onHere(stop), onReport(stop)}); m.refresh(); m.apply(reply). */
(function(){
'use strict';
var ID=['g1','g2','g3','g4','g5'];
var NAMES={
 en:['Base Camp','River Crossing','Forest Path','Queue Complex','Main Steps','Shrine'],
 ml:['ബേസ് ക്യാമ്പ്','നദി കടക്കൽ','വനപാത','ക്യൂ സമുച്ചയം','പ്രധാന പടികൾ','ദർശന സ്ഥലം'],
 ta:['அடிவார முகாம்','ஆற்றைக் கடக்கும் இடம்','வனப்பாதை','வரிசை வளாகம்','முக்கியப் படிகள்','தரிசன இடம்'],
 te:['బేస్ క్యాంప్','నది దాటే చోటు','అడవి దారి','క్యూ కాంప్లెక్స్','ప్రధాన మెట్లు','దర్శన స్థలం'],
 kn:['ಬೇಸ್ ಕ್ಯಾಂಪ್','ನದಿ ದಾಟುವ ಸ್ಥಳ','ಅರಣ್ಯ ಮಾರ್ಗ','ಸರತಿ ಸಂಕೀರ್ಣ','ಮುಖ್ಯ ಮೆಟ್ಟಿಲುಗಳು','ದರ್ಶನ ಸ್ಥಳ'],
 hi:['बेस कैंप','नदी पार','वन पथ','कतार परिसर','मुख्य सीढ़ियाँ','दर्शन स्थल']};
var S={
 en:{title:'Site map',sim:'SIMULATED',you:'You are here',gate:'Your gate',calm:'Calm',busy:'Busy',vbusy:'Very busy',min:'min',next:'Next: {n}, {w} min walk, {q} min wait',end:'You have reached the end of the route.',nopos:'Tap a stop and choose "I am here".',take:'Take me here',here:'I am here',wait:'Wait now',fac:'Facilities here',nofac:'No facilities listed',walk:'walk to next',close:'Close',report:'Report crowd here',sent:'Report sent',hereSay:'I reached {n}',lite:'Light list, to keep the page fast.',legend:'Facilities',staffH:'Site overview',help:'needs help',load:'load',stop:'Stop',shrine:'End of route',takeSay:'How do I get to {n}?',
  f:{water:'Drinking water',toilet:'Toilets',medical:'Medical post',rest:'Rest area',wheelchair:'Wheelchair help',cloak:'Cloak room',lost_found:'Lost and found',info:'Information counter'}},
 ml:{title:'സ്ഥല ഭൂപടം',sim:'SIMULATED',you:'നിങ്ങൾ ഇവിടെ',gate:'നിങ്ങളുടെ ഗേറ്റ്',calm:'ശാന്തം',busy:'തിരക്ക്',vbusy:'വലിയ തിരക്ക്',min:'മിനിറ്റ്',next:'അടുത്തത്: {n}, {w} മിനിറ്റ് നടത്തം, {q} മിനിറ്റ് കാത്തിരിപ്പ്',end:'വഴിയുടെ അവസാനത്തിലെത്തി.',nopos:'ഒരു സ്ഥലം തൊട്ട് "ഞാൻ ഇവിടെ" തിരഞ്ഞെടുക്കൂ.',take:'ഇവിടെ എത്തിക്കൂ',here:'ഞാൻ ഇവിടെ',wait:'ഇപ്പോഴത്തെ കാത്തിരിപ്പ്',fac:'ഇവിടത്തെ സൗകര്യങ്ങൾ',nofac:'സൗകര്യങ്ങൾ ഇല്ല',walk:'അടുത്തതിലേക്ക് നടത്തം',close:'അടയ്ക്കുക',report:'ഇവിടത്തെ തിരക്ക് അറിയിക്കുക',sent:'അറിയിച്ചു',hereSay:'ഞാൻ {n} എത്തി',lite:'വേഗത്തിനായി ലളിതമായ പട്ടിക.',legend:'സൗകര്യങ്ങൾ',staffH:'സ്ഥലത്തിന്റെ അവലോകനം',help:'സഹായം വേണം',load:'തിരക്ക്',stop:'സ്ഥലം',shrine:'വഴിയുടെ അവസാനം',takeSay:'{n} എങ്ങനെ എത്തും?',
  f:{water:'കുടിവെള്ളം',toilet:'ശൗചാലയം',medical:'വൈദ്യസഹായം',rest:'വിശ്രമ സ്ഥലം',wheelchair:'വീൽചെയർ സഹായം',cloak:'ക്ലോക്ക് റൂം',lost_found:'കളഞ്ഞുപോയത്',info:'വിവര കൗണ്ടർ'}},
 ta:{title:'இடத்தின் வரைபடம்',sim:'SIMULATED',you:'நீங்கள் இங்கே',gate:'உங்கள் வாயில்',calm:'அமைதி',busy:'கூட்டம்',vbusy:'மிகுந்த கூட்டம்',min:'நிமி',next:'அடுத்து: {n}, {w} நிமிட நடை, {q} நிமிட காத்திருப்பு',end:'வழியின் முடிவை அடைந்தீர்கள்.',nopos:'ஓர் இடத்தைத் தொட்டு "நான் இங்கே" என்பதைத் தேர்ந்தெடுங்கள்.',take:'இங்கே அழைத்துச் செல்',here:'நான் இங்கே',wait:'இப்போதைய காத்திருப்பு',fac:'இங்குள்ள வசதிகள்',nofac:'வசதிகள் இல்லை',walk:'அடுத்ததற்கு நடை',close:'மூடு',report:'இங்கே கூட்டத்தைத் தெரிவி',sent:'தெரிவிக்கப்பட்டது',hereSay:'நான் {n} வந்துவிட்டேன்',lite:'வேகத்திற்காக எளிய பட்டியல்.',legend:'வசதிகள்',staffH:'இடத்தின் மேலோட்டம்',help:'உதவி தேவை',load:'கூட்டம்',stop:'இடம்',shrine:'வழியின் முடிவு',takeSay:'{n} எப்படிப் போவது?',
  f:{water:'குடிநீர்',toilet:'கழிப்பறை',medical:'மருத்துவ மையம்',rest:'ஓய்விடம்',wheelchair:'சக்கர நாற்காலி உதவி',cloak:'பொருள் காப்பறை',lost_found:'தொலைந்தவை',info:'தகவல் மையம்'}},
 te:{title:'ప్రదేశ పటం',sim:'SIMULATED',you:'మీరు ఇక్కడ',gate:'మీ గేటు',calm:'ప్రశాంతం',busy:'రద్దీ',vbusy:'చాలా రద్దీ',min:'నిమి',next:'తర్వాత: {n}, {w} నిమిషాల నడక, {q} నిమిషాల నిరీక్షణ',end:'మార్గం చివరికి చేరుకున్నారు.',nopos:'ఒక చోటును నొక్కి "నేను ఇక్కడ" ఎంచుకోండి.',take:'ఇక్కడికి తీసుకెళ్లు',here:'నేను ఇక్కడ',wait:'ఇప్పటి నిరీక్షణ',fac:'ఇక్కడి సౌకర్యాలు',nofac:'సౌకర్యాలు లేవు',walk:'తర్వాతి చోటుకు నడక',close:'మూసివేయి',report:'ఇక్కడి రద్దీ తెలపండి',sent:'తెలిపాము',hereSay:'నేను {n} చేరుకున్నాను',lite:'వేగం కోసం సరళమైన జాబితా.',legend:'సౌకర్యాలు',staffH:'ప్రదేశ అవలోకనం',help:'సహాయం కావాలి',load:'రద్దీ',stop:'చోటు',shrine:'మార్గం చివర',takeSay:'{n} కి ఎలా వెళ్ళాలి?',
  f:{water:'తాగునీరు',toilet:'మరుగుదొడ్లు',medical:'వైద్య కేంద్రం',rest:'విశ్రాంతి చోటు',wheelchair:'వీల్‌చైర్ సహాయం',cloak:'క్లోక్ రూమ్',lost_found:'పోయినవి దొరికినవి',info:'సమాచార కేంద్రం'}},
 kn:{title:'ಸ್ಥಳದ ನಕ್ಷೆ',sim:'SIMULATED',you:'ನೀವು ಇಲ್ಲಿ',gate:'ನಿಮ್ಮ ಗೇಟ್',calm:'ಶಾಂತ',busy:'ಜನದಟ್ಟಣೆ',vbusy:'ಹೆಚ್ಚು ಜನದಟ್ಟಣೆ',min:'ನಿಮಿ',next:'ಮುಂದೆ: {n}, {w} ನಿಮಿಷ ನಡಿಗೆ, {q} ನಿಮಿಷ ಕಾಯುವಿಕೆ',end:'ಮಾರ್ಗದ ಕೊನೆಗೆ ತಲುಪಿದ್ದೀರಿ.',nopos:'ಒಂದು ಸ್ಥಳ ಒತ್ತಿ "ನಾನು ಇಲ್ಲಿ" ಆಯ್ಕೆಮಾಡಿ.',take:'ಇಲ್ಲಿಗೆ ಕರೆದೊಯ್ಯಿ',here:'ನಾನು ಇಲ್ಲಿ',wait:'ಈಗಿನ ಕಾಯುವಿಕೆ',fac:'ಇಲ್ಲಿನ ಸೌಲಭ್ಯಗಳು',nofac:'ಸೌಲಭ್ಯಗಳಿಲ್ಲ',walk:'ಮುಂದಿನ ಸ್ಥಳಕ್ಕೆ ನಡಿಗೆ',close:'ಮುಚ್ಚಿ',report:'ಇಲ್ಲಿನ ಜನದಟ್ಟಣೆ ತಿಳಿಸಿ',sent:'ತಿಳಿಸಲಾಗಿದೆ',hereSay:'ನಾನು {n} ತಲುಪಿದೆ',lite:'ವೇಗಕ್ಕಾಗಿ ಸರಳ ಪಟ್ಟಿ.',legend:'ಸೌಲಭ್ಯಗಳು',staffH:'ಸ್ಥಳದ ಅವಲೋಕನ',help:'ಸಹಾಯ ಬೇಕು',load:'ಜನದಟ್ಟಣೆ',stop:'ಸ್ಥಳ',shrine:'ಮಾರ್ಗದ ಕೊನೆ',takeSay:'{n} ಗೆ ಹೇಗೆ ಹೋಗುವುದು?',
  f:{water:'ಕುಡಿಯುವ ನೀರು',toilet:'ಶೌಚಾಲಯ',medical:'ವೈದ್ಯಕೀಯ ಕೇಂದ್ರ',rest:'ವಿಶ್ರಾಂತಿ ಸ್ಥಳ',wheelchair:'ಗಾಲಿಕುರ್ಚಿ ಸಹಾಯ',cloak:'ಕ್ಲೋಕ್ ರೂಮ್',lost_found:'ಕಳೆದುಹೋದದ್ದು',info:'ಮಾಹಿತಿ ಕೌಂಟರ್'}},
 hi:{title:'स्थल का नक्शा',sim:'SIMULATED',you:'आप यहाँ हैं',gate:'आपका गेट',calm:'शांत',busy:'भीड़',vbusy:'बहुत भीड़',min:'मिनट',next:'अगला: {n}, {w} मिनट पैदल, {q} मिनट प्रतीक्षा',end:'आप रास्ते के अंत तक पहुँच गए हैं।',nopos:'एक जगह छुइए और "मैं यहाँ हूँ" चुनिए।',take:'मुझे यहाँ ले चलिए',here:'मैं यहाँ हूँ',wait:'अभी की प्रतीक्षा',fac:'यहाँ की सुविधाएँ',nofac:'कोई सुविधा नहीं',walk:'अगले तक पैदल',close:'बंद करें',report:'यहाँ की भीड़ बताएँ',sent:'बता दिया',hereSay:'मैं {n} पहुँच गया',lite:'तेज़ पेज के लिए सरल सूची।',legend:'सुविधाएँ',staffH:'स्थल का अवलोकन',help:'मदद चाहिए',load:'भीड़',stop:'जगह',shrine:'रास्ते का अंत',takeSay:'{n} कैसे पहुँचूँ?',
  f:{water:'पीने का पानी',toilet:'शौचालय',medical:'चिकित्सा केंद्र',rest:'विश्राम स्थल',wheelchair:'व्हीलचेयर सहायता',cloak:'क्लोक रूम',lost_found:'खोया-पाया',info:'सूचना काउंटर'}}};
var FAC_DEFAULT={g1:['water','toilet','wheelchair','cloak'],g2:['medical','rest'],g3:['water','rest'],g4:['toilet','medical','info'],g5:['water','wheelchair']};
var FIC={ // 24 box, 1.8 stroke line icons
 water:'<path d="M12 3.5c3 4 5.5 6.6 5.5 9.8a5.5 5.5 0 0 1-11 0C6.5 10.100 9 7.500 12 3.500z"/>',
 toilet:'<circle cx="8" cy="5.500" r="1.700"/><path d="M8 9v9M5 11.500h6M5.500 18h5"/><circle cx="17" cy="5.500" r="1.700"/><path d="M14.500 10h5l-1 4h-3zM16 14v4M18 14v4"/>',
 medical:'<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M12 8v8M8 12h8"/>',
 rest:'<path d="M5 11V8a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v3"/><path d="M3.500 11h17v5h-17zM6 16v3M18 16v3"/>',
 wheelchair:'<circle cx="10" cy="4.500" r="1.600"/><path d="M10 8v5h5l2.500 5M10 10.500h4.500"/><path d="M7.500 12.500a5 5 0 1 0 7 6.500"/>',
 cloak:'<path d="M9.500 6.500a2.500 2.500 0 1 1 3.500 2.300L12 10"/><path d="M12 10 3.500 16.500h17z"/>',
 lost_found:'<circle cx="10.500" cy="10.500" r="5.500"/><path d="M15 15l5 5M10.500 8.500v2.500M10.500 13h.01"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5.500M12 7.800h.01"/>'};
function ico(n,cls){return '<svg class="smi '+(cls||'')+'" viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+(FIC[n]||'')+'</g></svg>'}
var TICKET='<svg class="smi" viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M4 7h16v3a2 2 0 0 0 0 4v3H4v-3a2 2 0 0 0 0-4z"/><path d="M14 7v10" stroke-dasharray="2 2"/></g></svg>';
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
/* layout in a 360 x 560 box; route climbs from the bottom to the top */
var PT=[[74,612],[108,500],[64,388],[108,276],[70,164],[96,60]];
var LEFT=[0,0,0,0,0,0]; // all labels sit to the right of the winding spine
var START=[86,676];
function curve(pts){var p=[START].concat(pts),d='M'+p[0][0]+' '+p[0][1];
 for(var i=0;i<p.length-1;i++){var a=p[i-1]||p[i],b=p[i],c=p[i+1],e=p[i+2]||c;
  d+=' C'+(b[0]+(c[0]-a[0])/6).toFixed(1)+' '+(b[1]+(c[1]-a[1])/6).toFixed(1)+' '+(c[0]-(e[0]-b[0])/6).toFixed(1)+' '+(c[1]-(e[1]-b[1])/6).toFixed(1)+' '+c[0]+' '+c[1]}
 return d}
var D=curve(PT);
function level(l){l=+l||0;if(l>1)l=l/100;return l>.66?2:l>.4?1:0}
var LV=['calm','busy','vbusy'];

function create(root,o){
 o=o||{};var L=function(){return (o.lang&&o.lang())||'en'};var tx=function(){return S[L()]||S.en};
 var st={stops:[],pos:null,slot:null,sim:true,focus:null,shownPos:null,len:null,lens:null,mode:'full',timer:0,anim:0};
 var lite=function(){return (o.mode&&o.mode())==='lite'||st.mode==='lite'};
 var nm=function(i){var l=NAMES[L()]||NAMES.en;return l[i]||NAMES.en[i]};
 var idx=function(id){return ID.indexOf(id)};
 function fmt(s,m){return s.replace(/\{(\w)\}/g,function(_,k){return m[k]==null?'':m[k]})}

 function normalise(j){ /* accept the /api/map contract, or the /api/queue shape as a fallback */
  var list=(j.stops||j.gates||[]);var by={};list.forEach(function(s){by[s.id]=s});
  st.stops=ID.map(function(id,i){var s=by[id]||{};return {id:id,i:i,wait:s.wait_min==null?null:s.wait_min,load:s.load==null?0:s.load,fac:s.facilities||FAC_DEFAULT[id],walk:s.walk_to_next_min==null?(i<4?[8,12,10,9][i]:null):s.walk_to_next_min,gate:!!s.is_slot_gate,help:s.help||s.needs_help||0}});
  st.pos=j.position!==undefined?j.position:(j.you&&j.you.position_id)||st.pos;
  if(j.slot)st.slot=j.slot.gate||st.slot; else if(j.slot===null)st.slot=null;
  st.sim=j.simulated!==false;st.mode=j.map_mode||(j.rush?'lite':'full')}
 async function refresh(){
  try{var r=await fetch('/api/map?uid='+encodeURIComponent(o.uid||'')+'&lang='+L());
   if(r.ok){normalise(await r.json())}else throw 0}
  catch(e){try{var r2=await fetch('/api/queue?uid='+encodeURIComponent(o.uid||'')+'&lang='+L());if(r2.ok)normalise(await r2.json())}catch(e2){}}
  if(!st.stops.length)normalise({gates:[]});
  if(st.pos==null&&localStorage.mapPos&&localStorage.mapUid===(o.uid||''))st.pos=localStorage.mapPos;
  render()}
 function setPos(id,silent){if(!id||idx(id)<0)return;st.pos=id;try{localStorage.mapPos=id;localStorage.mapUid=o.uid||''}catch(e){}if(!silent)render()}

 /* ---- drawing ---- */
 function ring(s){var lv=level(s.load),c=2*Math.PI*19,f=Math.max(.1,Math.min(1,(+s.load>1?s.load/100:+s.load)||0));
  return '<circle class="rt" cx="0" cy="0" r="19"/><circle class="ra l'+lv+'" cx="0" cy="0" r="19" stroke-dasharray="'+(c*f).toFixed(1)+' '+c.toFixed(1)+'" transform="rotate(-90)"/>'}
 function svgHTML(){
  var h='<svg class="sm-svg" viewBox="0 0 360 680" role="img" aria-label="'+esc(tx().title)+'" preserveAspectRatio="xMidYMid meet">';
  h+='<defs><linearGradient id="smHill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFE9D6"/><stop offset="1" stop-color="#FFE9D6" stop-opacity="0"/></linearGradient></defs>';
  h+='<path class="hill" d="M-10 230 C50 150 90 60 180 30 C260 4 330 70 370 170 L370 230 Z" fill="url(#smHill)"/>';
  /* river across the middle, two quiet wave lines */
  h+='<path class="river" d="M-10 560 C60 530 110 590 190 560 C260 532 310 582 372 550"/>';
  h+='<path class="riverl" d="M130 574 q18-10 36 0 t36 0 M260 566 q18-10 36 0 t36 0"/>';
  /* trees: three small clusters */
  [[22,470],[20,330],[22,222],[24,110]].forEach(function(t){h+='<g class="tree" transform="translate('+t[0]+' '+t[1]+')"><path d="M0-16 11 4H-11z"/><path d="M0-4 13 16H-13z"/><rect x="-1.500" y="16" width="3" height="6"/></g>'});
  h+='<path class="route ahead" id="smAhead" d="'+D+'"/>';
  h+='<path class="route walked" id="smWalked" d="'+D+'"/>';
  st.stops.forEach(function(s,i){var p=PT[i];var here=st.pos===s.id;
   h+='<g class="node n'+level(s.load)+(here?' is-you':'')+(st.focus===s.id?' is-focus':'')+(st.slot===s.id?' is-gate':'')+'" data-id="'+s.id+'" transform="translate('+p[0]+' '+p[1]+')">'+ring(s)+'<circle class="disc" r="13"/><text class="num" y="5.500" text-anchor="middle">'+(i+1)+'</text></g>'});
  var q=PT[5];h+='<g class="node end" transform="translate('+q[0]+' '+q[1]+')"><circle class="disc" r="15"/><path class="flag" d="M-4 9V-9M-4-9h11l-3 4 3 4h-11" /></g>';
  h+='<g id="smYou" class="you" style="display:none"><circle class="pulse" r="12"/><circle class="dot" r="9"/></g>';
  return h+'</svg>'}
 function labelHTML(s,i){var p=PT[i],t=tx(),lv=level(s.load),here=st.pos===s.id,L2=LEFT[i];
  var left=L2?'':'left:'+(142/360*100).toFixed(2)+'%;',right=L2?'right:'+((360-p[0]+24)/360*100).toFixed(2)+'%;':'';
  var top=(p[1]/680*100).toFixed(2);
  var facs=(s.fac||[]).map(function(f){return ico(f)}).join('');
  var pills=(here?'<span class="pill-me">'+esc(t.you)+'</span>':'')+(st.slot===s.id?'<span class="pill-gate">'+TICKET+esc(t.gate)+'</span>':'')+(s.help?'<span class="pill-help">'+esc(s.help)+' '+esc(t.help)+'</span>':'');
  return '<button type="button" class="slab '+(L2?'r':'l')+(here?' is-you':'')+(st.focus===s.id?' is-focus':'')+'" data-id="'+s.id+'" style="'+left+right+'top:'+top+'%">'
   +'<span class="sn" lang="'+L()+'">'+esc(nm(i))+'</span>'
   +'<span class="sw"><b class="num">'+(s.wait==null?'-':esc(s.wait))+'</b> '+esc(t.min)+'<span class="lv l'+lv+'"><i></i>'+esc(t[LV[lv]])+'</span></span>'
   +(facs?'<span class="sf">'+facs+'</span>':'')+pills+'</button>'}
 function endLabel(){var p=PT[5],t=tx();return '<div class="slab end l" style="left:'+(142/360*100).toFixed(2)+'%;top:'+(p[1]/680*100).toFixed(2)+'%"><span class="sn" lang="'+L()+'">'+esc(nm(5))+'</span><span class="sw">'+esc(t.shrine)+'</span></div>'}
 function nextLine(){var t=tx();var i=idx(st.pos);if(i<0||!st.stops[i])return esc(t.nopos);if(i>=4)return esc(t.end);var n=st.stops[i+1];return esc(fmt(t.next,{n:nm(i+1),w:st.stops[i].walk,q:n.wait==null?'-':n.wait}))}
 function legend(){var t=tx(),used={};st.stops.forEach(function(s){(s.fac||[]).forEach(function(f){used[f]=1})});
  return Object.keys(used).map(function(f){return '<li>'+ico(f)+'<span>'+esc(t.f[f]||f)+'</span></li>'}).join('')}

 function render(){
  var t=tx();root.classList.add('sitemap');root.classList.toggle('compact',!!o.compact);root.classList.toggle('lite',lite());
  root.setAttribute('lang',L());
  var head='<div class="sm-head"><h2 class="section-h">'+esc(o.staff?t.staffH:t.title)+'</h2><span class="sm-sim">'+esc(t.sim)+'</span></div>';
  var nl='<p class="sm-next" aria-live="polite">'+nextLine()+'</p>';
  if(lite()){
   var rows=st.stops.map(function(s,i){var lv=level(s.load),here=st.pos===s.id;
    return '<li><button type="button" class="srow'+(here?' is-you':'')+(st.focus===s.id?' is-focus':'')+'" data-id="'+s.id+'"><span class="sidx num">'+(i+1)+'</span><span class="sname" lang="'+L()+'">'+esc(nm(i))+'</span><span class="sw"><b class="num">'+(s.wait==null?'-':esc(s.wait))+'</b> '+esc(t.min)+'<span class="lv l'+lv+'"><i></i>'+esc(t[LV[lv]])+'</span></span>'
     +((here||st.slot===s.id)?'<span class="spills">'+(here?'<span class="pill-me">'+esc(t.you)+'</span>':'')+(st.slot===s.id?'<span class="pill-gate">'+TICKET+esc(t.gate)+'</span>':'')+'</span>':'')+'</button></li>'}).join('');
   root.innerHTML=head+'<p class="sm-lite">'+esc(t.lite)+'</p><ol class="slist">'+rows+'</ol>'+nl}
  else{
   root.innerHTML=head+'<div class="sm-box">'+svgHTML()+st.stops.map(labelHTML).join('')+endLabel()+'</div>'+nl+'<ul class="sm-legend" aria-label="'+esc(t.legend)+'">'+legend()+'</ul>';
   measure();placeYou(false)}
  root.querySelectorAll('[data-id]').forEach(function(e){e.addEventListener('click',function(ev){ev.stopPropagation();openSheet(e.getAttribute('data-id'))})})}

 /* ---- path walking ---- */
 function measure(){var a=root.querySelector('#smAhead');if(!a)return;st.len=a.getTotalLength();st.lens=PT.map(function(p){var best=0,bd=1e9;for(var l=0;l<=st.len;l+=3){var q=a.getPointAtLength(l),d=(q.x-p[0])*(q.x-p[0])+(q.y-p[1])*(q.y-p[1]);if(d<bd){bd=d;best=l}}return best})}
 function lenAt(id){var i=idx(id);return i<0?0:st.lens[i]}
 function drawAt(l){var w=root.querySelector('#smWalked'),y=root.querySelector('#smYou'),a=root.querySelector('#smAhead');if(!w||!a)return;
  w.style.strokeDasharray=Math.max(0,l)+' '+st.len;var p=a.getPointAtLength(l);y.setAttribute('transform','translate('+p.x+' '+p.y+')');y.style.display=''}
 function placeYou(animate){var y=root.querySelector('#smYou');if(!y)return;
  if(st.pos==null||idx(st.pos)<0){y.style.display='none';var w=root.querySelector('#smWalked');if(w)w.style.strokeDasharray='0 '+st.len;st.shownPos=null;return}
  var to=lenAt(st.pos),from=st.shownPos!=null?lenAt(st.shownPos):to;st.shownPos=st.pos;
  cancelAnimationFrame(st.anim);
  var reduce=matchMedia('(prefers-reduced-motion:reduce)').matches;
  if(!animate||reduce||from===to){drawAt(to);return}
  var t0=performance.now(),dur=1100;(function step(now){var k=Math.min(1,(now-t0)/dur);k=1-Math.pow(1-k,3);drawAt(from+(to-from)*k);if(k<1)st.anim=requestAnimationFrame(step)})(t0)}
 /* the reply came back: move, highlight, bring the map into view */
 function apply(j,quiet){if(!j)return;var gid=j.gate_id,pid=j.position_gate_id;
  var moved=pid&&pid!==st.pos;if(pid)setPos(pid,true);
  var want=j.show==='map'||pid||gid;if(!want)return;
  st.focus=gid||pid||st.focus;
  if(moved&&!lite()&&root.querySelector('#smYou'))updateMarks(true);else render();
  root.classList.add('slide');setTimeout(function(){root.classList.remove('slide')},700);
  if(!quiet)bring()}
 function updateMarks(animate){ /* re-render labels but keep the marker where it was so it can travel */
  var from=st.shownPos;var keep=from;render();st.shownPos=keep;
  var y=root.querySelector('#smYou');if(y&&keep!=null){var l0=lenAt(keep);drawAt(l0)}placeYou(animate)}
 function bring(){var e=root.querySelector('.slab.is-focus,.srow.is-focus')||root;var r=matchMedia('(prefers-reduced-motion:reduce)').matches;try{e.scrollIntoView({behavior:r?'auto':'smooth',block:'center'})}catch(x){e.scrollIntoView()}}

 /* ---- stop sheet ---- */
 var sheet=null;
 function openSheet(id){var s=st.stops[idx(id)];if(!s)return;var t=tx(),i=s.i;closeSheet();
  var lv=level(s.load);var facs=(s.fac||[]).map(function(f){return '<li>'+ico(f)+'<span>'+esc(t.f[f]||f)+'</span></li>'}).join('')||'<li class="small">'+esc(t.nofac)+'</li>';
  sheet=document.createElement('div');sheet.className='msheet-wrap';sheet.setAttribute('lang',L());
  var acts=o.staff?'<button type="button" class="btn btn-primary btn-block" data-a="report">'+esc(t.report)+'</button>':'<button type="button" class="btn btn-primary btn-block" data-a="take">'+esc(t.take)+'</button><button type="button" class="btn btn-secondary btn-block" data-a="here">'+esc(t.here)+'</button>';
  sheet.innerHTML='<div class="msheet-back"></div><div class="msheet" role="dialog" aria-modal="true" aria-label="'+esc(nm(i))+'"><div class="grab"></div><h3 class="ms-h" lang="'+L()+'">'+esc(nm(i))+'</h3>'
   +'<p class="ms-wait"><span class="k">'+esc(t.wait)+'</span><b class="num">'+(s.wait==null?'-':esc(s.wait))+'</b> '+esc(t.min)+'<span class="lv l'+lv+'"><i></i>'+esc(t[LV[lv]])+'</span></p>'
   +(s.walk!=null&&i<4?'<p class="small">'+esc(t.walk)+': '+esc(s.walk)+' '+esc(t.min)+'</p>':'')
   +'<p class="k2">'+esc(t.fac)+'</p><ul class="ms-fac">'+facs+'</ul><div class="ms-acts">'+acts+'<button type="button" class="btn btn-quiet btn-block" data-a="close">'+esc(t.close)+'</button></div><p class="small ms-note" role="status"></p></div>';
  document.body.appendChild(sheet);requestAnimationFrame(function(){sheet.classList.add('open')});
  sheet.querySelector('.msheet-back').onclick=closeSheet;
  sheet.querySelectorAll('[data-a]').forEach(function(b){b.onclick=function(){var a=b.getAttribute('data-a');
   if(a==='close')closeSheet();
   else if(a==='take'){closeSheet();st.focus=id;render();bring();o.onTake&&o.onTake({id:id,name:nm(i),say:fmt(t.takeSay,{n:nm(i)})})}
   else if(a==='here'){setPos(id,true);st.focus=id;closeSheet();updateMarks(true);bring();o.onHere&&o.onHere({id:id,name:nm(i),say:fmt(t.hereSay,{n:nm(i)})})}
   else if(a==='report'){var n=sheet.querySelector('.ms-note');Promise.resolve(o.onReport&&o.onReport({id:id,name:NAMES.en[i]})).then(function(){n.textContent=t.sent})}}});
  var f=sheet.querySelector('[data-a]');f&&f.focus()}
 function closeSheet(){if(!sheet)return;var s=sheet;sheet=null;s.classList.remove('open');setTimeout(function(){s.remove()},220)}
 document.addEventListener('keydown',function(e){if(e.key==='Escape')closeSheet()});

 function start(ms){refresh();clearInterval(st.timer);st.timer=setInterval(refresh,ms||5000)}
 return {refresh:refresh,render:render,apply:apply,setPos:setPos,start:start,openSheet:openSheet,state:st,bring:bring,setHelp:function(m){st.stops.forEach(function(s){s.help=(m&&m[s.id])||0});render()},names:nm}}
window.SiteMap={create:create,NAMES:NAMES,STR:S};
})();

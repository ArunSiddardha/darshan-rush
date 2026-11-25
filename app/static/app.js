/* Darshan Rush v2, pilgrim page. Same API calls as v1:
   GET /api/flags, GET /api/queue, POST /api/slots/book, POST /api/directions, POST /api/event */
(function(){
const $=s=>document.querySelector(s);
const uid=localStorage.uid||(localStorage.uid=(crypto.randomUUID?crypto.randomUUID():String(Math.random()).slice(2)));
const qs=new URLSearchParams(location.search);
const DEMO=qs.get('demo')||''; // screenshot states only: listening, thinking, reply, lite, elder, error
const ORDER0=['ml','ta','te','kn','hi','en'];
function phoneLang(){for(const l of (navigator.languages||[navigator.language||'en'])){const c=String(l).slice(0,2).toLowerCase();if(ORDER0.includes(c))return c}return 'en'}
let forced=qs.get('lang')||localStorage.langForced||'';   // set only by the quiet Language item in More help
let lang=forced||phoneLang(),F={},Q={gates:[]},mySlot=null,rec=null,chunks=[],busy=false,lastQ=0,msgTimer=0,exposed=false;
const ORDER=['ml','ta','te','kn','hi','en'];
const LN={ml:'മലയാളം',ta:'தமிழ்',te:'తెలుగు',kn:'ಕನ್ನಡ',hi:'हिन्दी',en:'English'};
const LOC={ml:'ml-IN',ta:'ta-IN',te:'te-IN',kn:'kn-IN',hi:'hi-IN',en:'en-IN'};
const T={
en:{prompt:'Tap and say when you want darshan',listen:'Listening. Tap again when you finish.',think:'Finding your slot',type:'Type instead',send:'Send',ph:'For example: book for 2 people tomorrow',book:'Book the shortest queue',crowd:'Crowd right now',min:'min',short:'Shortest',mine:'Your gate',route:'Show route',hide:'Hide route',here:'You are here',slot:'Your darshan slot',gate:'Gate',reached:'I reached the gate',again:'Play again',thanks:'Thank you. Noted that you reached the gate.',lite:'Heavy crowd. The page is lighter now. Booking continues.',stag:'Slots are spaced out so everyone gets a fair time.',empty:'Crowd numbers are loading.',busy:'Booking is busy. Try again in a moment.',credits:'Voice is resting for a moment. Please type your request below.',retry:'Try again',rate:'Voice is busy right now. Try again in a minute, or type.',blocked:'The microphone is blocked. Allow it in your browser, or type.',nomic:'No microphone found. Please type.',net:'No connection to the server. Check your network and try again.',device:'Read aloud by this phone, not by Sarvam.',more:'More help',read:'Read this for me',readsub:'Photo of a ticket or a sign',real:'Is this booking site real?',realsub:'Paste a link to check it',check:'Check',elder:'Larger, voice-first view',eldersub:'Bigger button, spoken help',elderOn:'Use the larger view',elderOff:'Back to the normal view',hear:'Hear how to use this',you:'You said',today:'Today',soon:'Not available yet in this prototype.',updated:'Updated just now'},
ml:{prompt:'അമർത്തി, ദർശനം എപ്പോൾ വേണമെന്ന് പറയൂ',listen:'കേൾക്കുന്നു. കഴിഞ്ഞാൽ വീണ്ടും അമർത്തൂ.',think:'നിങ്ങളുടെ സ്ലോട്ട് കണ്ടെത്തുന്നു',type:'ടൈപ്പ് ചെയ്യാം',send:'അയയ്ക്കുക',ph:'ഉദാ: നാളെ 2 പേർക്ക് ബുക്ക് ചെയ്യൂ',book:'ഏറ്റവും ചെറിയ ക്യൂവിൽ ബുക്ക് ചെയ്യുക',crowd:'ഇപ്പോഴത്തെ തിരക്ക്',min:'മിനിറ്റ്',short:'ഏറ്റവും കുറവ്',mine:'നിങ്ങളുടെ ഗേറ്റ്',route:'വഴി കാണിക്കുക',hide:'വഴി മറയ്ക്കുക',here:'നിങ്ങൾ ഇവിടെ',slot:'നിങ്ങളുടെ ദർശന സ്ലോട്ട്',gate:'ഗേറ്റ്',reached:'ഞാൻ ഗേറ്റിൽ എത്തി',again:'വീണ്ടും കേൾക്കുക',thanks:'നന്ദി. നിങ്ങൾ ഗേറ്റിൽ എത്തിയത് രേഖപ്പെടുത്തി.',lite:'തിരക്ക് കൂടുതലാണ്. പേജ് ലളിതമാക്കി. ബുക്കിംഗ് തുടരാം.',stag:'എല്ലാവർക്കും ന്യായമായ സമയം ലഭിക്കാൻ സ്ലോട്ടുകൾ ഇടവിട്ടാണ്.',empty:'തിരക്കിന്റെ വിവരം വരുന്നു.',busy:'ബുക്കിംഗ് തിരക്കിലാണ്. വീണ്ടും ശ്രമിക്കൂ.',credits:'ശബ്ദം ഇപ്പോൾ ലഭ്യമല്ല. താഴെ ടൈപ്പ് ചെയ്യൂ.',retry:'വീണ്ടും ശ്രമിക്കൂ',rate:'ശബ്ദ സേവനം തിരക്കിലാണ്. ഒരു മിനിറ്റ് കഴിഞ്ഞ് ശ്രമിക്കൂ, അല്ലെങ്കിൽ ടൈപ്പ് ചെയ്യൂ.',blocked:'മൈക്ക് തടഞ്ഞിരിക്കുന്നു. ബ്രൗസറിൽ അനുവദിക്കൂ, അല്ലെങ്കിൽ ടൈപ്പ് ചെയ്യൂ.',nomic:'മൈക്ക് ലഭ്യമല്ല. ടൈപ്പ് ചെയ്യൂ.',net:'സെർവറുമായി ബന്ധമില്ല. നെറ്റ്‌വർക്ക് നോക്കി വീണ്ടും ശ്രമിക്കൂ.',more:'കൂടുതൽ സഹായം',read:'ഇത് വായിച്ചു തരൂ',readsub:'ടിക്കറ്റിന്റെയോ ബോർഡിന്റെയോ ഫോട്ടോ',real:'ഈ ബുക്കിംഗ് സൈറ്റ് യഥാർത്ഥമാണോ?',realsub:'ലിങ്ക് ഒട്ടിച്ച് പരിശോധിക്കൂ',check:'പരിശോധിക്കുക',elder:'വലിയ, ശബ്ദം മുൻനിർത്തിയ കാഴ്ച',eldersub:'വലിയ ബട്ടൺ, പറഞ്ഞുതരുന്ന സഹായം',hear:'ഉപയോഗിക്കുന്ന വിധം കേൾക്കുക',you:'നിങ്ങൾ പറഞ്ഞത്',today:'ഇന്ന്'},
ta:{prompt:'அழுத்தி, எப்போது தரிசனம் வேண்டும் என்று சொல்லுங்கள்',listen:'கேட்கிறேன். முடிந்ததும் மீண்டும் அழுத்தவும்.',think:'உங்கள் நேரத்தைத் தேடுகிறேன்',type:'தட்டச்சு செய்யலாம்',send:'அனுப்பு',ph:'உதா: நாளை 2 பேருக்கு பதிவு செய்',book:'குறைந்த வரிசையில் பதிவு செய்',crowd:'இப்போதைய கூட்டம்',min:'நிமி',short:'குறைவு',mine:'உங்கள் வாயில்',route:'வழியைக் காட்டு',hide:'வழியை மறை',here:'நீங்கள் இங்கே',slot:'உங்கள் தரிசன நேரம்',gate:'வாயில்',reached:'நான் வாயிலை அடைந்தேன்',again:'மீண்டும் கேள்',thanks:'நன்றி. நீங்கள் வாயிலை அடைந்தது பதிவானது.',lite:'கூட்டம் அதிகம். பக்கம் எளிதாக்கப்பட்டது. முன்பதிவு தொடரும்.',stag:'அனைவருக்கும் நியாயமான நேரம் கிடைக்க நேரங்கள் இடைவெளியுடன் வழங்கப்படுகின்றன.',empty:'கூட்ட விவரம் வருகிறது.',busy:'முன்பதிவு பரபரப்பாக உள்ளது. மீண்டும் முயலுங்கள்.',credits:'குரல் இப்போது கிடைக்கவில்லை. கீழே தட்டச்சு செய்யுங்கள்.',retry:'மீண்டும் முயலவும்',rate:'குரல் சேவை பரபரப்பாக உள்ளது. ஒரு நிமிடம் கழித்து முயலுங்கள், அல்லது தட்டச்சு செய்யுங்கள்.',blocked:'மைக் தடுக்கப்பட்டுள்ளது. உலாவியில் அனுமதியுங்கள், அல்லது தட்டச்சு செய்யுங்கள்.',nomic:'மைக் கிடைக்கவில்லை. தட்டச்சு செய்யுங்கள்.',net:'சர்வருடன் இணைப்பு இல்லை. நெட்வொர்க்கைச் சரிபார்த்து மீண்டும் முயலுங்கள்.',more:'மேலும் உதவி',read:'இதைப் படித்துச் சொல்',readsub:'டிக்கெட் அல்லது பலகையின் புகைப்படம்',real:'இந்த முன்பதிவு தளம் உண்மையானதா?',realsub:'இணைப்பை ஒட்டி சரிபார்க்கவும்',check:'சரிபார்',elder:'பெரிய, குரல் முதன்மை காட்சி',eldersub:'பெரிய பொத்தான், குரல் வழிகாட்டல்',hear:'பயன்படுத்தும் முறையைக் கேள்',you:'நீங்கள் சொன்னது',today:'இன்று'},
te:{prompt:'నొక్కి, దర్శనం ఎప్పుడు కావాలో చెప్పండి',listen:'వింటున్నాను. అయ్యాక మళ్లీ నొక్కండి.',think:'మీ స్లాట్ వెతుకుతున్నాను',type:'టైప్ చేయండి',send:'పంపండి',ph:'ఉదా: రేపు 2 మందికి బుక్ చేయండి',book:'తక్కువ క్యూలో బుక్ చేయండి',crowd:'ఇప్పటి రద్దీ',min:'నిమి',short:'తక్కువ',mine:'మీ గేటు',route:'దారి చూపించు',hide:'దారి దాచు',here:'మీరు ఇక్కడ',slot:'మీ దర్శన స్లాట్',gate:'గేటు',reached:'నేను గేటుకు చేరుకున్నాను',again:'మళ్లీ వినండి',thanks:'ధన్యవాదాలు. మీరు గేటుకు చేరినట్లు నమోదైంది.',lite:'రద్దీ ఎక్కువగా ఉంది. పేజీ తేలిక చేశాం. బుకింగ్ కొనసాగుతుంది.',stag:'అందరికీ న్యాయంగా సమయం దొరకడానికి స్లాట్లు విడతలుగా ఇస్తున్నాం.',empty:'రద్దీ వివరాలు వస్తున్నాయి.',busy:'బుకింగ్ రద్దీగా ఉంది. మళ్లీ ప్రయత్నించండి.',credits:'వాయిస్ ఇప్పుడు అందుబాటులో లేదు. కింద టైప్ చేయండి.',retry:'మళ్లీ ప్రయత్నించండి',rate:'వాయిస్ సేవ రద్దీగా ఉంది. ఒక నిమిషం తర్వాత ప్రయత్నించండి, లేదా టైప్ చేయండి.',blocked:'మైక్ బ్లాక్ అయింది. బ్రౌజర్‌లో అనుమతించండి, లేదా టైప్ చేయండి.',nomic:'మైక్ అందుబాటులో లేదు. టైప్ చేయండి.',net:'సర్వర్‌తో కనెక్షన్ లేదు. నెట్‌వర్క్ చూసి మళ్లీ ప్రయత్నించండి.',more:'మరింత సహాయం',read:'ఇది చదివి చెప్పండి',readsub:'టికెట్ లేదా బోర్డు ఫోటో',real:'ఈ బుకింగ్ సైట్ నిజమైనదేనా?',realsub:'లింక్ అతికించి తనిఖీ చేయండి',check:'తనిఖీ',elder:'పెద్ద, వాయిస్ ముందు వీక్షణ',eldersub:'పెద్ద బటన్, మాటల సహాయం',hear:'ఎలా వాడాలో వినండి',you:'మీరు చెప్పింది',today:'ఈ రోజు'},
kn:{prompt:'ಒತ್ತಿ, ದರ್ಶನ ಯಾವಾಗ ಬೇಕು ಎಂದು ಹೇಳಿ',listen:'ಕೇಳುತ್ತಿದ್ದೇನೆ. ಮುಗಿದ ಮೇಲೆ ಮತ್ತೆ ಒತ್ತಿ.',think:'ನಿಮ್ಮ ಸ್ಲಾಟ್ ಹುಡುಕುತ್ತಿದ್ದೇನೆ',type:'ಟೈಪ್ ಮಾಡಿ',send:'ಕಳುಹಿಸಿ',ph:'ಉದಾ: ನಾಳೆ 2 ಜನರಿಗೆ ಬುಕ್ ಮಾಡಿ',book:'ಕಡಿಮೆ ಸಾಲಿನಲ್ಲಿ ಬುಕ್ ಮಾಡಿ',crowd:'ಈಗಿನ ಜನದಟ್ಟಣೆ',min:'ನಿಮಿ',short:'ಕಡಿಮೆ',mine:'ನಿಮ್ಮ ಗೇಟ್',route:'ದಾರಿ ತೋರಿಸಿ',hide:'ದಾರಿ ಮರೆಮಾಡಿ',here:'ನೀವು ಇಲ್ಲಿ',slot:'ನಿಮ್ಮ ದರ್ಶನ ಸ್ಲಾಟ್',gate:'ಗೇಟ್',reached:'ನಾನು ಗೇಟ್ ತಲುಪಿದೆ',again:'ಮತ್ತೆ ಕೇಳಿ',thanks:'ಧನ್ಯವಾದ. ನೀವು ಗೇಟ್ ತಲುಪಿದ್ದು ದಾಖಲಾಯಿತು.',lite:'ಜನದಟ್ಟಣೆ ಹೆಚ್ಚಿದೆ. ಪುಟವನ್ನು ಹಗುರಗೊಳಿಸಲಾಗಿದೆ. ಬುಕಿಂಗ್ ಮುಂದುವರಿಯುತ್ತದೆ.',stag:'ಎಲ್ಲರಿಗೂ ನ್ಯಾಯಯುತ ಸಮಯ ಸಿಗಲು ಸ್ಲಾಟ್‌ಗಳನ್ನು ಅಂತರದಲ್ಲಿ ನೀಡಲಾಗುತ್ತಿದೆ.',empty:'ಜನದಟ್ಟಣೆ ಮಾಹಿತಿ ಬರುತ್ತಿದೆ.',busy:'ಬುಕಿಂಗ್ ಬ್ಯುಸಿಯಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',credits:'ಧ್ವನಿ ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಕೆಳಗೆ ಟೈಪ್ ಮಾಡಿ.',retry:'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ',rate:'ಧ್ವನಿ ಸೇವೆ ಬ್ಯುಸಿಯಾಗಿದೆ. ಒಂದು ನಿಮಿಷದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ, ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.',blocked:'ಮೈಕ್ ತಡೆಯಲಾಗಿದೆ. ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಅನುಮತಿಸಿ, ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.',nomic:'ಮೈಕ್ ಲಭ್ಯವಿಲ್ಲ. ಟೈಪ್ ಮಾಡಿ.',net:'ಸರ್ವರ್ ಸಂಪರ್ಕ ಇಲ್ಲ. ನೆಟ್‌ವರ್ಕ್ ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',more:'ಹೆಚ್ಚಿನ ಸಹಾಯ',read:'ಇದನ್ನು ಓದಿ ಹೇಳಿ',readsub:'ಟಿಕೆಟ್ ಅಥವಾ ಫಲಕದ ಫೋಟೋ',real:'ಈ ಬುಕಿಂಗ್ ಸೈಟ್ ನಿಜವೇ?',realsub:'ಲಿಂಕ್ ಅಂಟಿಸಿ ಪರಿಶೀಲಿಸಿ',check:'ಪರಿಶೀಲಿಸಿ',elder:'ದೊಡ್ಡ, ಧ್ವನಿ ಮೊದಲ ನೋಟ',eldersub:'ದೊಡ್ಡ ಬಟನ್, ಮಾತಿನ ಸಹಾಯ',hear:'ಹೇಗೆ ಬಳಸುವುದು ಎಂದು ಕೇಳಿ',you:'ನೀವು ಹೇಳಿದ್ದು',today:'ಇಂದು'},
hi:{prompt:'दबाइए और बताइए, दर्शन कब चाहिए',listen:'सुन रहा हूँ। बोलने के बाद फिर दबाइए।',think:'आपका स्लॉट ढूँढ रहा हूँ',type:'टाइप करें',send:'भेजें',ph:'जैसे: कल 2 लोगों के लिए बुक करें',book:'सबसे छोटी कतार में बुक करें',crowd:'अभी की भीड़',min:'मिनट',short:'सबसे कम',mine:'आपका गेट',route:'रास्ता दिखाएँ',hide:'रास्ता छिपाएँ',here:'आप यहाँ हैं',slot:'आपका दर्शन स्लॉट',gate:'गेट',reached:'मैं गेट पर पहुँच गया',again:'फिर सुनें',thanks:'धन्यवाद। आपका गेट पर पहुँचना दर्ज हो गया।',lite:'भीड़ ज़्यादा है। पेज हल्का कर दिया गया है। बुकिंग जारी है।',stag:'सबको उचित समय मिले, इसलिए स्लॉट अलग-अलग समय पर दिए जा रहे हैं।',empty:'भीड़ की जानकारी आ रही है।',busy:'बुकिंग में भीड़ है। फिर कोशिश करें।',credits:'आवाज़ अभी उपलब्ध नहीं है। नीचे टाइप करें।',retry:'फिर कोशिश करें',rate:'आवाज़ सेवा अभी व्यस्त है। एक मिनट बाद कोशिश करें, या टाइप करें।',blocked:'माइक ब्लॉक है। ब्राउज़र में अनुमति दें, या टाइप करें।',nomic:'माइक उपलब्ध नहीं है। टाइप करें।',net:'सर्वर से कनेक्शन नहीं है। नेटवर्क देखकर फिर कोशिश करें।',more:'और मदद',read:'इसे पढ़कर सुनाइए',readsub:'टिकट या बोर्ड की फ़ोटो',real:'क्या यह बुकिंग साइट असली है?',realsub:'लिंक डालकर जाँचें',check:'जाँचें',elder:'बड़ा, आवाज़ वाला दृश्य',eldersub:'बड़ा बटन, बोलकर मदद',hear:'इस्तेमाल का तरीका सुनें',you:'आपने कहा',today:'आज'}
};
const X={
en:{yes:'Yes',no:'No',rh:'High risk',rc:'Be careful',ru:'Cannot check',langlbl:'Language',tap1:'Tap once to start talking',end:'End',live:'Listening. Just speak.',photo:'Take or choose a photo',orig:'Text in the photo',pasteph:'Paste the link, or type what the person offered',langauto:'Automatic',blip:'I did not catch that. Please tap and say it again.',slow:'The network is slow. One moment.',booked:'Booked'},
ml:{yes:'ശരി',no:'വേണ്ട',rh:'ഉയർന്ന അപകടം',rc:'ജാഗ്രത',ru:'പരിശോധിക്കാനായില്ല',langlbl:'ഭാഷ',tap1:'ഒരു തവണ അമർത്തി സംസാരിക്കൂ',end:'അവസാനിപ്പിക്കുക',live:'കേൾക്കുന്നു. സംസാരിക്കൂ.',photo:'ഫോട്ടോ എടുക്കുക',orig:'ഫോട്ടോയിലെ എഴുത്ത്',pasteph:'ലിങ്ക് ഒട്ടിക്കൂ, അല്ലെങ്കിൽ പറഞ്ഞത് ടൈപ്പ് ചെയ്യൂ',langauto:'സ്വയം',blip:'മനസ്സിലായില്ല. വീണ്ടും അമർത്തി പറയൂ.',slow:'നെറ്റ്‌വർക്ക് പതുക്കെയാണ്. ഒരു നിമിഷം.',booked:'ബുക്ക് ചെയ്തു'},
ta:{yes:'ஆம்',no:'இல்லை',rh:'அதிக ஆபத்து',rc:'கவனம்',ru:'சரிபார்க்க இயலவில்லை',langlbl:'மொழி',tap1:'ஒரு முறை அழுத்திப் பேசுங்கள்',end:'முடிக்க',live:'கேட்கிறேன். பேசுங்கள்.',photo:'புகைப்படம் எடுக்கவும்',orig:'புகைப்படத்திலுள்ள எழுத்து',pasteph:'இணைப்பை ஒட்டவும், அல்லது சொன்னதைத் தட்டச்சு செய்யவும்',langauto:'தானாக',blip:'புரியவில்லை. மீண்டும் அழுத்திச் சொல்லுங்கள்.',slow:'நெட்வொர்க் மெதுவாக உள்ளது. ஒரு நிமிடம்.',booked:'பதிவானது'},
te:{yes:'అవును',no:'వద్దు',rh:'అధిక ప్రమాదం',rc:'జాగ్రత్త',ru:'తనిఖీ చేయలేకపోయాము',langlbl:'భాష',tap1:'ఒకసారి నొక్కి మాట్లాడండి',end:'ముగించు',live:'వింటున్నాను. మాట్లాడండి.',photo:'ఫోటో తీయండి',orig:'ఫోటోలోని పాఠం',pasteph:'లింక్ అతికించండి, లేదా చెప్పినది టైప్ చేయండి',langauto:'ఆటోమేటిక్',blip:'అర్థం కాలేదు. మళ్లీ నొక్కి చెప్పండి.',slow:'నెట్‌వర్క్ నెమ్మదిగా ఉంది. ఒక్క నిమిషం.',booked:'బుక్ అయింది'},
kn:{yes:'ಹೌದು',no:'ಬೇಡ',rh:'ಹೆಚ್ಚಿನ ಅಪಾಯ',rc:'ಎಚ್ಚರಿಕೆ',ru:'ಪರಿಶೀಲಿಸಲಾಗಲಿಲ್ಲ',langlbl:'ಭಾಷೆ',tap1:'ಒಮ್ಮೆ ಒತ್ತಿ ಮಾತನಾಡಿ',end:'ಮುಗಿಸಿ',live:'ಕೇಳುತ್ತಿದ್ದೇನೆ. ಮಾತನಾಡಿ.',photo:'ಫೋಟೋ ತೆಗೆಯಿರಿ',orig:'ಫೋಟೋದಲ್ಲಿನ ಪಠ್ಯ',pasteph:'ಲಿಂಕ್ ಅಂಟಿಸಿ, ಅಥವಾ ಹೇಳಿದ್ದನ್ನು ಟೈಪ್ ಮಾಡಿ',langauto:'ಸ್ವಯಂ',blip:'ಅರ್ಥವಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಒತ್ತಿ ಹೇಳಿ.',slow:'ನೆಟ್‌ವರ್ಕ್ ನಿಧಾನವಾಗಿದೆ. ಒಂದು ಕ್ಷಣ.',booked:'ಬುಕ್ ಆಗಿದೆ'},
hi:{yes:'हाँ',no:'नहीं',rh:'ज़्यादा जोखिम',rc:'सावधान',ru:'जाँच नहीं हो सकी',langlbl:'भाषा',tap1:'एक बार दबाकर बोलिए',end:'बंद करें',live:'सुन रहा हूँ। बोलिए।',photo:'फोटो लें',orig:'फोटो का लिखा हुआ',pasteph:'लिंक चिपकाइए, या जो कहा गया वह लिखिए',langauto:'अपने आप',blip:'समझ नहीं आया। फिर दबाकर बोलिए।',slow:'नेटवर्क धीमा है। एक पल।',booked:'बुक हो गया'}};
for(const k in X)Object.assign(T[k],X[k]);
const EX={en:'Book a slot for 2 people tomorrow morning',ml:'നാളെ രാവിലെ 2 പേർക്ക് സ്ലോട്ട് വേണം',ta:'நாளை காலை 2 பேருக்கு ஸ்லாட் வேண்டும்',te:'రేపు ఉదయం 2 మందికి స్లాట్ కావాలి',kn:'ನಾಳೆ ಬೆಳಿಗ್ಗೆ 2 ಜನರಿಗೆ ಸ್ಲಾಟ್ ಬೇಕು',hi:'कल सुबह 2 लोगों के लिए स्लॉट चाहिए'};
const t=k=>(T[lang]&&T[lang][k])||T.en[k];
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const val=x=>x&&typeof x==='object'?(x.value!==undefined?x.value:x.enabled):x;
const flag=n=>val(F[n]!==undefined?F[n]:(F.flags&&F.flags[n]));
const isLite=()=>DEMO==='lite'||(Q.map_mode||flag('map_mode'))==='lite';
const isStag=()=>(Q.slot_mode||flag('slot_mode'))==='staggered'||(mySlot&&mySlot.mode==='staggered');
const isElder=()=>DEMO==='elder'||VF||localStorage.elder==='1'||!!(F.traits&&(F.traits.age_65_plus||F.traits.age65));
const gname=id=>{const g=(Q.gates||[]).find(x=>x.id===id);return g?(g.name||g.id):String(id||'')};
const ICON=n=>`<svg aria-hidden="true"><use href="#i-${n}"/></svg>`;

/* ---------- messages: by real cause, calm, never stale ---------- */
function say(key,kind){const m=$('#msg');clearTimeout(msgTimer);
 if(!key){m.hidden=true;return}
 m.className='msg'+(kind?' msg-'+kind:'');m.dataset.k=key;
 const act=key==='credits'||key==='blocked'||key==='nomic'?'type':(['net','busy','rate','blip','lost'].includes(key)?'retry':'');
 m.innerHTML=ICON('info')+'<span>'+esc(t(key)||key)+'</span>'+(act?'<button type="button" class="msg-act">'+esc(t(act))+'</button>':'');m.hidden=false;
 const b=m.querySelector('.msg-act');if(b)b.onclick=()=>{say(null);if(act==='type'){openType();const i=$('#typed');if(i){i.scrollIntoView({block:'center',behavior:'smooth'});i.focus()}}else $('#mic').click()};
 if(kind!=='bad')msgTimer=setTimeout(()=>{m.hidden=true},9000)}
function causeOf(status,j){const s=((j&&(j.notice||j.error||j.detail))||'')+'';
 if(status===402||/credit/i.test(s))return 'credits';
 if(status===429||/rate.?limit|too many/i.test(s))return 'rate';
 if(status>=500)return 'busy';
 if(s)return /voice unavailable/i.test(s)?'credits':'busy';
 return null}
function setState(k){const s=$('#state');document.body.classList.toggle('st',!!k);
 if(k==='think'){s.innerHTML='<span>'+esc(t('think'))+'</span><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>';return}
 s.textContent=k?t(k):''}

/* ---------- text ---------- */
function langs(){const L=[['', t('langauto')]].concat(ORDER.map(k=>[k,LN[k]]));
 $('#langs').innerHTML=L.map(([k,n])=>`<button type="button" ${k?`lang="${k}"`:''} data-k="${k}" aria-pressed="${k===forced}">${esc(n)}</button>`).join('');
 document.querySelectorAll('#langs button').forEach(b=>b.onclick=()=>{forced=b.dataset.k;if(forced){localStorage.langForced=forced;lang=forced}else{localStorage.removeItem('langForced');lang=phoneLang()}langs();text();loadFlags();pollQueue()})}
/* example phrases cycle through the six scripts until the first words are heard, then stay in the person's language */
/* ---------- site map ---------- */
let SM=null;
function initMap(){if(!window.SiteMap)return;SM=SiteMap.create($('#siteMap'),{uid,lang:()=>lang,mode:()=>isLite()?'lite':'full',
  onTake:s=>askMap(s.say),onHere:s=>askMap(s.say,true)});SM.start(5000)}
async function askMap(sentence,quiet){try{const r=await fetch('/api/directions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:sentence,uid,lang})});const j=await r.json().catch(()=>({}));
  if(!r.ok)return;if(!quiet||j.reply_text){$('#reply').hidden=false;$('#heard').textContent='';$('#replyText').textContent=j.reply_text||'';$('#replyText').lang=j.lang||lang;lastAudio=j.audio_base64;$('#replyPlay').hidden=!j.audio_base64;if(j.audio_base64)play(j.audio_base64);document.body.classList.add('has-result')}
  if(SM)SM.apply(Object.assign({},j,{show:'none'}),true)}catch(e){}}
function mapTexts(){const e=$('#mapLink');if(e){e.textContent=(SiteMap.STR[lang]||SiteMap.STR.en).title}}
let exI=0,exTimer=0,heard=false,COPY=null,VF=false;
async function loadCopy(){try{const r=await fetch('/api/ui-copy?lang='+lang);if(r.ok){COPY=await r.json();examples()}}catch(e){}}   // Flagsmith remote config 'ui_copy'
async function loadVF(){try{const r=await fetch('/api/flags/decisions?uid='+encodeURIComponent(uid)+'&lang='+lang+(localStorage.age65==='1'?'&age65=true':''));
 if(r.ok){const j=await r.json();const f=(j.flags||[]).find(x=>x.flag==='voice_first');const v=!!(f&&f.enabled);if(v!==VF){VF=v;text()}}}catch(e){}}
function examples(){const e=$('#examples');if(!e)return;clearInterval(exTimer);
 const show=()=>{const one=heard||forced;const k=one?lang:ORDER[exI++%ORDER.length];e.classList.remove('in');
  const line=(one&&COPY&&COPY.lang===k&&COPY.examples&&COPY.examples.length)?COPY.examples[exI++%COPY.examples.length]:EX[k];
  setTimeout(()=>{e.lang=k;e.textContent='\u201c'+line+'\u201d';e.classList.add('in')},180)};
 show();if(!heard&&!forced&&!matchMedia('(prefers-reduced-motion:reduce)').matches)exTimer=setInterval(show,2600)}
function text(){document.documentElement.lang=lang;
 const set=(id,k)=>{const e=$(id);if(e)e.textContent=t(k)};
 set('#prompt',live?'live':'tap1');set('#endLive','end');set('#cYes','yes');set('#cNo','no');set('#photoLbl','photo');set('#origLbl','orig');set('#langLbl','langlbl');set('#typeLbl','type');set('#go','send');set('#book','book');set('#crowdH','crowd');set('#reachedLbl','reached');
 set('#passK','slot');set('#passGateK','gate');set('#moreH','more');set('#readLbl','read');set('#readSub','readsub');set('#realLbl','real');set('#realSub','realsub');
 set('#realGo','check');set('#elderLbl','elder');set('#elderSub','eldersub');set('#hearLbl','hear');set('#soon1','soon');set('#typedLbl','type');
 document.querySelectorAll('.lbl-again').forEach(e=>e.textContent=t('again'));
 $('#typed').placeholder=t('ph');$('#mic').setAttribute('aria-label',t('tap1'));$('#realText').placeholder=t('pasteph');window.DARSHAN_LANG=lang;window.DARSHAN_BADGE={high_risk:t('rh'),caution:t('rc'),unknown:t('ru')};examples();if(COPY&&COPY.lang!==lang)loadCopy();
 $('#elderToggle').textContent=isElder()?(T.en.elderOff):(T.en.elderOn);
 if(!rec&&!busy)setState('');
 route();chrome();renderQ();renderSlot();if(window.SiteMap){mapTexts();if(SM)SM.refresh()}}

/* ---------- mode chrome ---------- */
function chrome(){const lite=isLite();document.body.classList.toggle('lite',lite);document.body.classList.toggle('elder',isElder());
 const l=$('#liteLine');l.hidden=!lite;l.textContent=t('lite');
 $('#stagNote').hidden=!isStag();$('#stagNote').textContent=t('stag')}

/* ---------- crowd rows ---------- */
function norm(l){l=+l||0;return l>1?Math.min(l/100,1):Math.max(l,0)}
function renderQ(){const gs=(Q.gates||[]).slice(0,5);const box=$('#gates');
 if(!gs.length){box.innerHTML=`<li class="empty-row">${esc(t('empty'))}</li>`;$('#route').innerHTML='';return}
 const best=gs.reduce((a,g)=>a==null||g.wait_min<a.wait_min?g:a,null).id;const mine=mySlot&&mySlot.gate;
 box.innerHTML=gs.map(g=>{const l=norm(g.load),c=l>.66?'high':l>.4?'mid':'';
  const chip=g.id===mine?`<span class="chip chip-me">${esc(t('mine'))}</span>`:g.id===best?`<span class="chip chip-ok">${esc(t('short'))}</span>`:'';
  return `<li class="${g.id===best?'best':''}"><div class="g-line"><span class="g-name" lang="en">${esc(g.name||g.id)}${chip}</span><span class="g-min num">${esc(g.wait_min)}<small>${esc(t('min'))}</small></span></div><div class="g-bar"><i class="${c}" style="width:${Math.max(4,Math.round(l*100))}%"></i></div></li>`}).join('');
 $('#crowdAge').textContent='';
 drawRoute(gs)}
function drawRoute(gs){const mine=mySlot&&mySlot.gate;
 $('#route').innerHTML=`<li class="you"><span>${esc(t('here'))}</span></li>`+gs.map(g=>`<li class="${g.id===mine?'mine':''}"><span lang="en">${esc(g.name||g.id)}</span><span class="r-min">${esc(g.wait_min)} ${esc(t('min'))}</span></li>`).join('')}
let routeOpen=null;
function route(){const b=$('#routeBtn');const open=routeOpen==null?(val(F.voice_directions)==='map'):routeOpen;
 b.setAttribute('aria-expanded',String(open));$('#route').hidden=!open;$('#routeLbl').textContent=open?t('hide'):t('route')}
$('#routeBtn').onclick=()=>{routeOpen=$('#routeBtn').getAttribute('aria-expanded')!=='true';route()};

/* ---------- the pass ---------- */
function slotFrom(j,gate){let s=j.slot;if(!s)return null;if(typeof s!=='object')s={label:String(s)};
 const label=s.label||s.time||s.start||'';const m=String(label).match(/\d{1,2}:\d{2}/g)||[];
 return {gate:s.gate||gate,label,start:s.start||m[0]||label,end:s.end||m[1]||'',mode:j.mode||s.mode}}
function renderSlot(){try{if(mySlot)localStorage.slot=JSON.stringify(mySlot)}catch(e){}
 const p=$('#pass');document.body.classList.toggle('booked',!!mySlot);document.body.classList.toggle('has-result',!!mySlot||!$('#reply').hidden);
 if(!mySlot){p.hidden=true;return}
 p.hidden=false;const tm=$('#passTime');tm.textContent=mySlot.start;tm.classList.toggle('long',String(mySlot.start).length>6);
 let d='';try{d=new Intl.DateTimeFormat(LOC[lang],{weekday:'long',day:'numeric',month:'long'}).format(new Date())}catch(e){d=t('today')}
 $('#passDate').textContent=d+(mySlot.end?', '+mySlot.start+' to '+mySlot.end:'');
 $('#passGate').textContent=gname(mySlot.gate);$('#passGate').lang='en'}

/* ---------- network ---------- */
async function loadFlags(){try{const age=localStorage.elder==='1'?'&age65=true':'';
 const r=await fetch('/api/flags?uid='+encodeURIComponent(uid)+'&lang='+lang+age+(exposed?'&expose=0':''));if(r.ok){F=await r.json();exposed=true;chrome();route();
  const v=F.experiment_variant||val(F.voice_directions);$('#expLine').textContent=v?('Directions style for you, chosen by Flagsmith: '+(v==='map'?'route':'voice')+'.'):''}}catch(e){}}
async function pollQueue(){try{const r=await fetch(`/api/queue?uid=${encodeURIComponent(uid)}&lang=${lang}`);if(!r.ok)throw 0;Q=await r.json();lastQ=Date.now();
  if($('#msg').dataset.k==='net')say(null)}catch(e){if(Date.now()-lastQ>9000&&lastQ){say('net','warn');$('#msg').dataset.k='net'}}
 chrome();renderQ();if(mySlot)renderSlot()}
function play(b64){if(!b64)return false;const p=$('#player');p.src='data:audio/wav;base64,'+b64;p.play().catch(()=>{});return true}
function deviceSpeak(text){if(!window.speechSynthesis)return false;const u=new SpeechSynthesisUtterance(text);u.lang=LOC[lang];speechSynthesis.cancel();speechSynthesis.speak(u);return true}

let live=false,fails=0,primed=false,AC=null;
const SILENT='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=';
function prime(){ /* first tap: unlock audio for iPhone, once */
 if(primed)return;primed=true;const p=$('#player');p.src=SILENT;p.play().catch(()=>{});
 try{AC=new (window.AudioContext||window.webkitAudioContext)();AC.resume()}catch(e){}}
function openType(){const r=$('#typeRow');if(r)r.open=true}
async function directions(fd,isAudio){fd.append('uid',uid);fd.append('lang',isAudio?(forced||'auto'):(forced||lang));
 const slow=setTimeout(()=>say('slow','warn'),10000);
 let r,j={};try{r=await fetch('/api/directions',{method:'POST',body:fd});j=await r.json().catch(()=>({}))}catch(e){clearTimeout(slow);say('net','bad');return null}
 clearTimeout(slow);if($('#msg').dataset.k==='slow')say(null);
 const c=causeOf(r.status,j);
 if(!r.ok){say(c||'busy','bad');return null}
 if(j.notice&&!j.audio_base64){j._voiceOff=c||'credits'}
 if(j.transcript)heard=true;
 if(isAudio&&j.lang&&!forced&&j.transcript&&j.lang!==lang){lang=j.lang;text()}   // follow the person's language
 return j}

/* ---------- actions ---------- */
async function sendVoice(fd,isAudio){busy=true;setState('think');say(null);$('#mic').disabled=true;
 const j=await directions(fd,isAudio);busy=false;$('#mic').disabled=false;setState('');if(!j){fails++;if(fails>=2)openType();return}
 const isNotice=j.notice&&j.reply_text===j.notice;
 if(isNotice){say(j._voiceOff||'credits','warn');openType();return}
 if(isAudio&&!j.transcript){fails++;say('blip','warn');if(fails>=2)openType();return}
 fails=0;if(j.intent==='age'||j.age_set){localStorage.age65='1';loadVF()}
 $('#reply').hidden=false;$('#heard').innerHTML=j.transcript?esc(t('you'))+': '+esc(j.transcript):'';$('#replyText').textContent=j.reply_text||'';
 $('#replyText').lang=j.lang||lang;
 lastAudio=j.audio_base64;$('#replyPlay').hidden=!j.audio_base64;play(j.audio_base64);
 if(j._voiceOff)say(j._voiceOff,'warn');
 if(j.slot){mySlot=slotFrom(j,j.slot.gate);}
 renderSlot();renderQ();if(SM)SM.apply(j)}
let lastAudio=null;
$('#replyPlay').onclick=()=>play(lastAudio);
$('#say').onsubmit=e=>{e.preventDefault();const v=$('#typed').value.trim();if(!v)return;const fd=new FormData();fd.append('text',v);sendVoice(fd,false)};

/* single-utterance recording: tap to start, ends by itself after silence, or tap again. Level meter while listening. */
function setMic(on){const m=$('#mic');m.classList.toggle('is-listening',on);m.innerHTML=ICON(on?'stop':'mic');if(!on)m.style.removeProperty('--lvl')}
async function startSingle(){
 if(!navigator.mediaDevices||!window.MediaRecorder){say('nomic','warn');openType();return}
 let stream;
 try{stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}})}
 catch(e){const n=e&&e.name;say(n==='NotAllowedError'||n==='SecurityError'?'blocked':'nomic','warn');openType();return}
 const mt=['audio/webm;codecs=opus','audio/mp4','audio/webm'].find(x=>MediaRecorder.isTypeSupported&&MediaRecorder.isTypeSupported(x));
 chunks=[];rec=mt?new MediaRecorder(stream,{mimeType:mt}):new MediaRecorder(stream);
 let spoke=false,lastVoice=0,t0=Date.now(),raf=0,an=null,ctx=null;
 try{ctx=AC||new (window.AudioContext||window.webkitAudioContext)();an=ctx.createAnalyser();an.fftSize=512;ctx.createMediaStreamSource(stream).connect(an)}catch(e){an=null}
 const buf=an?new Uint8Array(an.fftSize):null;
 const tick=()=>{if(!rec)return;let v=0;
  if(an){an.getByteTimeDomainData(buf);let sum=0;for(const x of buf){const d=(x-128)/128;sum+=d*d}v=Math.sqrt(sum/buf.length)}
  $('#mic').style.setProperty('--lvl',Math.min(1,v*6).toFixed(2));
  const now=Date.now();if(v>0.03){spoke=true;lastVoice=now}
  if(an&&((spoke&&now-lastVoice>1500)||now-t0>12000||(!spoke&&now-t0>6000))){rec.stop();return}
  raf=requestAnimationFrame(tick)};
 rec.ondataavailable=e=>chunks.push(e.data);
 rec.onstop=()=>{cancelAnimationFrame(raf);stream.getTracks().forEach(x=>x.stop());const type=(rec&&rec.mimeType)||mt||'audio/webm';const blob=new Blob(chunks,{type});rec=null;setMic(false);setState('');
  if(an&&!spoke){fails++;say('blip','warn');if(fails>=2)openType();return}
  const fd=new FormData();fd.append('audio',blob,/mp4|aac/.test(type)?'speech.m4a':'speech.webm');sendVoice(fd,true)};
 rec.start();say(null);setMic(true);setState('listen');if(an)raf=requestAnimationFrame(tick)}

/* Live mode (addons_ui/live.js): one tap, then it listens, answers aloud and listens again. Single-tap flow is the fallback. */
let liveSess=null;
const Live={
 supported(){return !!(window.LiveSession&&(window.AudioContext||window.webkitAudioContext)&&navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)},
 async start(){
  const s=new LiveSession({endpoint:'/api/live/turn',promptEndpoint:'/api/live/prompt',uid,lang:forced||lang,auto:!forced,audioEl:$('#player'),greeting:false});
  const m=$('#mic'),caps=$('#caps'),end=$('#endLive');let youT='',appT='';
  const paint=()=>{caps.hidden=!(youT||appT);caps.textContent=appT||youT;caps.lang=lang};
  s.on('state',st=>{const map={listening:'live',hearing:'live',thinking:'think',speaking:'live'};setState(map[st]||'');
   m.classList.toggle('is-listening',st==='listening'||st==='hearing');
   if(st==='thinking')m.style.setProperty('--lvl',0)});
  s.on('level',v=>m.style.setProperty('--lvl',(+v).toFixed(2)));
  s.on('caption',c=>{if(c.who==='you'){youT=c.text;appT=''}else appT=c.text;paint()});
  s.on('turn',m=>{$('#confirmYN').hidden=!(m&&m.state==='confirm');heard=true;if(m&&(m.intent==='age'))localStorage.age65='1';if(s.lang&&!forced&&s.lang!==lang){lang=s.lang;text()}restore(true);loadVF();if(SM&&m&&m.raw)SM.apply(m.raw)});
  s.on('error',e=>{if(e&&(e.code==='denied'))say('blocked','warn');else if(e&&e.code==='nomic')say('nomic','warn');else if(e&&e.code==='network')say('net','warn');else if(e&&e.code==='server'&&/credit|unavailable/i.test(e.message||''))say('credits','warn')});
  s.on('end',()=>{$('#confirmYN').hidden=true;liveSess=null;live=false;document.body.classList.remove('live');end.hidden=true;m.classList.remove('is-listening');m.style.removeProperty('--lvl');m.innerHTML=ICON('mic');setState('');text()});
  liveSess=s;live=true;document.body.classList.add('live');end.hidden=false;say(null);text();
  await s.start();
  if(s.phase==='off'){liveSess=null;live=false;document.body.classList.remove('live');end.hidden=true;return false}
  m.innerHTML=ICON('stop');return true}};
window.DarshanLive=Live;
/* tap fallback for the spoken "shall I book it?": same dialogue, typed answer */
async function answer(word){const s=liveSess;if(!s)return;$('#confirmYN').hidden=true;
 try{const fd=new FormData();fd.append('uid',uid);fd.append('lang',forced||lang);fd.append('session_id',s.sessionId);fd.append('text',word);
  const r=await fetch('/api/live/turn',{method:'POST',body:fd});const j=await r.json();
  if(j.reply_text){s._caption('you',t(word));s._caption('app',j.reply_text)}
  if(j.audio_base64)s._enqueue(j.audio_base64);
  if(j.state==='confirm')$('#confirmYN').hidden=false;restore(true)}catch(e){say('net','warn');$('#confirmYN').hidden=false}}
$('#cYes').onclick=()=>answer('yes');$('#cNo').onclick=()=>answer('no');
$('#endLive').onclick=()=>{if(liveSess)liveSess.stop()};
$('#mic').onclick=async()=>{prime();
 if(liveSess){liveSess.stop();return}
 if(rec){rec.stop();return}
 if(Live.supported()&&!window.__noLive&&localStorage.noLive!=='1'){let ok=false;try{ok=await Live.start()}catch(e){ok=false}if(ok)return}
 startSingle()};
$('#book').onclick=async()=>{const gs=Q.gates||[];if(!gs.length){say('empty');return}
 const g=gs.reduce((a,x)=>x.wait_min<a.wait_min?x:a);const b=$('#book');b.disabled=true;say(null);
 try{const r=await fetch('/api/slots/book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid,gate:g.id,lang})});
  if(!r.ok)throw r.status;const j=await r.json();mySlot=slotFrom(j,g.id);mySlot.mode=j.mode;chrome();renderSlot();renderQ();readback();
  $('#pass').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'center'});
 }catch(e){say(typeof e==='number'?'busy':'net','bad')}
 b.disabled=false};

async function readback(){if(!mySlot)return;const fd=new FormData();
 const line=`${t('slot')}. ${gname(mySlot.gate)}. ${mySlot.label||mySlot.start}`;
 fd.append('text',line);fd.append('readback','1');
 const j=await directions(fd,false);
 if(j&&j.audio_base64){play(j.audio_base64);$('#passNote').textContent='';return}
 if(deviceSpeak(line))$('#passNote').textContent=t('device')}
$('#play').onclick=readback;
$('#reached').onclick=async()=>{if(!mySlot)return;const b=$('#reached');b.disabled=true;
 try{await fetch('/api/event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid,event:'reached_gate',gate:mySlot.gate,lang})})}catch(e){}
 b.classList.add('is-done');$('#passNote').textContent=t('thanks')};

/* elder: spoken prompt; Sarvam first, device voice if Sarvam is unavailable */
$('#hearHelp').onclick=async()=>{const fd=new FormData();fd.append('text',t('prompt'));fd.append('readback','1');
 const j=await directions(fd,false);if(j&&j.audio_base64)play(j.audio_base64);else deviceSpeak(t('prompt'))};
$('#elderToggle').onclick=()=>{localStorage.elder=localStorage.elder==='1'?'0':'1';loadFlags();text();window.scrollTo({top:0})};

/* add-ons (read a photo, is this site real): collapsed under More help; they use the detected language */
try{window.AddonsReadPhoto&&AddonsReadPhoto.init($('#ad-read'),{uid});window.AddonsSiteCheck&&AddonsSiteCheck.init($('#ad-site'),{uid})}catch(e){}

/* about sheet */
function sheet(open){document.body.classList.toggle('sheet-open',open);if(open)$('#sheetClose').focus()}
$('#aboutBtn').onclick=()=>sheet(true);$('#sheetClose').onclick=$('#sheetBack').onclick=()=>sheet(false);
document.addEventListener('keydown',e=>{if(e.key==='Escape')sheet(false)});

/* restore my booking after reload */
async function restore(quiet){try{if(!mySlot&&localStorage.slot){mySlot=JSON.parse(localStorage.slot);renderSlot();renderQ()}const r=await fetch('/api/slots?uid='+encodeURIComponent(uid));if(!r.ok)return;const j=await r.json();
 if(j.mine){mySlot=slotFrom({slot:j.mine,mode:j.mode},j.mine.gate);renderSlot();renderQ()}}catch(e){}}

/* screenshot-only states (?demo=...), never used in the live flow */
function demo(){if(DEMO==='listening'){document.body.classList.add('live');$('#mic').classList.add('is-listening');$('#mic').style.setProperty('--lvl',.45);setState('live');$('#endLive').hidden=false}
 if(DEMO==='speaking'){document.body.classList.add('live');setState('live');$('#caps').hidden=false;$('#caps').textContent=lang==='ml'?'നാളെ രാവിലെ 7:30, ഗേറ്റ് 2. ശരിയാണോ?':'Tomorrow 7:30 am, Base Camp gate. Shall I book it?';$('#confirmYN').hidden=false;$('#endLive').hidden=false}
 if(DEMO==='thinking'){setState('think');busy=true}
 if(DEMO==='reply'){$('#reply').hidden=false;$('#heard').textContent=t('you')+': '+(lang==='ml'?'ഫോറസ്റ്റ് പാതയിൽ എത്ര സമയം?':'How long at Forest Path?');$('#replyText').textContent=lang==='ml'?'ഫോറസ്റ്റ് പാതയിൽ ഇപ്പോൾ ഏകദേശം 31 മിനിറ്റ് കാത്തിരിക്കണം.':'Forest Path has about 31 minutes of waiting right now.';$('#replyPlay').hidden=false;renderSlot()}
 if(DEMO==='error')say('credits','warn')}

langs();text();loadFlags();pollQueue();restore();loadCopy();loadVF();demo();initMap();mapTexts();
if(qs.get('pos')&&SM){SM.setPos(qs.get('pos'),true);SM.state.focus=qs.get('pos');setTimeout(()=>SM.render(),300)}
setInterval(pollQueue,3000);setInterval(loadFlags,5000);
})();

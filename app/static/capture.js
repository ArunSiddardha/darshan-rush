/* Demo capture mode (?capture=1). For recording the video frame by frame. It never fakes a backend result:
   it only picks which REAL state to show. Params: uid=<name> (a real uid you booked through the API first),
   lang=te|ml|..., state=booked|map|more|help (pilgrim) or walk|crowd|qa|overview|requests (staff). Load BEFORE app.js. */
(function(){const q=new URLSearchParams(location.search);if(q.get('capture')!=='1')return;
 document.documentElement.classList.add('capture');
 const u=q.get('uid');if(u){try{localStorage.uid=u;localStorage.removeItem('slot')}catch(e){}}
 const st=document.createElement('style');st.textContent='html.capture,html.capture *{cursor:none!important;caret-color:transparent}'+
  'html.capture .tag{animation:none!important}html.capture #expLine,html.capture .dev,html.capture #lat{display:none!important}'+
  'html.capture ::-webkit-scrollbar{display:none}';document.head.appendChild(st);
 const state=q.get('state')||'';
 const go=()=>{const $=s=>document.querySelector(s);
  const scroll=el=>{if(el)el.scrollIntoView({block:'start'})};
  if(state==='booked')scroll($('#pass:not([hidden])')||$('#hero'));
  else if(state==='map')scroll($('#siteMap'));
  else if(state==='more'){scroll($('#moreH'))}
  else if(state==='help'){const b=$('#needHelp');if(b)b.click()}
  else if(state==='walk'){const b=$('#goWalk');if(b)b.click()}
  else if(state==='crowd'){const b=$('#goCrowd');if(b)b.click()}
  else if(state==='qa'){const b=$('#goAsk');if(b)b.click()}
  else if(state==='overview'){const d=$('#siteOv');if(d){d.open=true;scroll(d)}}
  else if(state==='requests'){scroll($('#careNear'))}};
 window.addEventListener('load',()=>setTimeout(go,1800));
})();

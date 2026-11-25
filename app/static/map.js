// Simple SVG route map, no tile service. DarshanMap.update(gates, {mode, best, mine})
(function(){
  const NS='http://www.w3.org/2000/svg';
  const ME={x:180,y:228};
  const G=[{x:36,y:70},{x:108,y:36},{x:180,y:26},{x:252,y:36},{x:324,y:70}];
  const HALL={x:180,y:92,r:34};
  let svg,gates=[],mode='full',best=null,mine=null,dots=[],raf=0,t0=0;
  const col=l=>l>.66?'#b4476b':l>.33?'#e9a84b':'#3e7c6b';
  const norm=l=>{l=+l||0;return l>1?Math.min(l/100,1):Math.max(l,0)};
  function el(n,a,p){const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e}
  function path(i){const g=G[i];return `M${ME.x} ${ME.y} C ${ME.x} ${(ME.y+g.y)/2+30}, ${g.x} ${(ME.y+g.y)/2+30}, ${g.x} ${g.y+10}`}
  function draw(){
    if(!svg)return;svg.innerHTML='';dots=[];
    el('circle',{cx:HALL.x,cy:HALL.y,r:HALL.r,fill:'#fff7ec',stroke:'#2a2140','stroke-opacity':.25});
    const t=el('text',{x:HALL.x,y:HALL.y+4,'text-anchor':'middle','font-size':11,fill:'#5b5073',stroke:'#fff7ec','stroke-width':4,'paint-order':'stroke'});t.textContent='Queue hall';
    gates.slice(0,5).forEach((g,i)=>{
      const l=norm(g.load),c=col(l),isBest=best===g.id,isMine=mine===g.id;
      const p=el('path',{d:path(i),fill:'none',stroke:isMine?'#2a2140':c,'stroke-width':isMine?4:isBest?3:2,'stroke-opacity':isMine?1:.55,'stroke-dasharray':isMine?'':'5 5'});
      el('circle',{cx:G[i].x,cy:G[i].y,r:17,fill:c});
      const n=el('text',{x:G[i].x,y:G[i].y+5,'text-anchor':'middle','font-size':14,'font-weight':700,fill:'#fff'});n.textContent=g.wait_min!=null?g.wait_min:'?';
      const lb=el('text',{x:G[i].x,y:G[i].y-24,'text-anchor':'middle','font-size':10,fill:'#2a2140'});lb.textContent=(g.name||g.id||'Gate '+(i+1)).slice(0,12);
      if(mode==='full'){const k=Math.round(2+l*9);for(let j=0;j<k;j++){const d=el('circle',{r:2.6,fill:c});dots.push({d,p,off:j/k,sp:.05+.06*(1-l)})}}
    });
    el('circle',{cx:ME.x,cy:ME.y,r:9,fill:'#2a2140'});
    const y=el('text',{x:ME.x+16,y:ME.y+4,'font-size':11,fill:'#2a2140'});y.textContent='You';
    if(mode==='full'&&!raf)loop();
  }
  function loop(){
    raf=requestAnimationFrame(function f(ts){
      if(mode!=='full'||!dots.length){raf=0;return}
      if(matchMedia('(prefers-reduced-motion:reduce)').matches){raf=0;return}
      t0=t0||ts;const s=(ts-t0)/1000;
      for(const o of dots){const len=o.len||(o.len=o.p.getTotalLength());const u=(o.off+s*o.sp)%1;const pt=o.p.getPointAtLength(u*len);o.d.setAttribute('cx',pt.x);o.d.setAttribute('cy',pt.y)}
      raf=requestAnimationFrame(f)});
  }
  window.DarshanMap={
    init(s){svg=s;draw()},
    update(g,o){gates=g||[];mode=(o&&o.mode)||'full';best=o&&o.best;mine=o&&o.mine;cancelAnimationFrame(raf);raf=0;draw()},
    colour:col,norm
  };
})();

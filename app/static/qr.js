/* Minimal QR encoder (byte mode, ECC M, versions 1-10), copied unchanged from v1 judge.html. No external requests. */
function makeQR(text){
 const bytes=Array.from(new TextEncoder().encode(text));
 const ECC=[10,16,26,18,24,16,18,22,22,26],NB=[1,1,1,2,2,4,4,4,5,5];
 const raw=v=>{let r=(16*v+128)*v+64;if(v>=2){const a=Math.floor(v/7)+2;r-=(25*a-10)*a-55;if(v>=7)r-=36}return r};
 let ver=0;for(let v=1;v<=10;v++){const cap=Math.floor(raw(v)/8)-ECC[v-1]*NB[v-1];if(4+(v<10?8:16)+8*bytes.length<=cap*8){ver=v;break}}
 if(!ver)throw new Error('URL too long');
 const size=ver*4+17,nEcc=ECC[ver-1],nBlk=NB[ver-1],rawCw=Math.floor(raw(ver)/8),dataCw=rawCw-nEcc*nBlk;
 let bits=[];const put=(x,n)=>{for(let i=n-1;i>=0;i--)bits.push((x>>>i)&1)};
 put(4,4);put(bytes.length,ver<10?8:16);bytes.forEach(b=>put(b,8));
 put(0,Math.min(4,dataCw*8-bits.length));while(bits.length%8)bits.push(0);
 const data=[];for(let i=0;i<bits.length;i+=8){let b=0;for(let j=0;j<8;j++)b=b*2+bits[i+j];data.push(b)}
 for(let p=0xEC;data.length<dataCw;p^=0xEC^0x11)data.push(p);
 const mul=(x,y)=>{let z=0;for(let i=7;i>=0;i--){z=(z<<1)^((z>>>7)*0x11D);z^=((y>>>i)&1)*x}return z&255};
 const div=[];for(let i=0;i<nEcc;i++)div.push(0);div[nEcc-1]=1;
 for(let r=1,i=0;i<nEcc;i++){for(let j=0;j<nEcc;j++){div[j]=mul(div[j],r);if(j+1<nEcc)div[j]^=div[j+1]}r=mul(r,2)}
 const rs=d=>{const res=new Array(nEcc).fill(0);for(const b of d){const f=b^res.shift();res.push(0);for(let i=0;i<nEcc;i++)res[i]^=mul(div[i],f)}return res};
 const nShort=nBlk-rawCw%nBlk,shortLen=Math.floor(rawCw/nBlk),blocks=[];
 for(let i=0,k=0;i<nBlk;i++){const d=data.slice(k,k+shortLen-nEcc+(i<nShort?0:1));k+=d.length;const e=rs(d);if(i<nShort)d.push(0);blocks.push(d.concat(e))}
 const all=[];for(let i=0;i<blocks[0].length;i++)blocks.forEach((b,j)=>{if(i!==shortLen-nEcc||j>=nShort)all.push(b[i])});
 const M=[],fn=[];for(let i=0;i<size;i++){M.push(new Array(size).fill(false));fn.push(new Array(size).fill(false))}
 const set=(x,y,d)=>{M[y][x]=!!d;fn[y][x]=true};
 for(let i=0;i<size;i++){set(6,i,i%2==0);set(i,6,i%2==0)}
 const finder=(cx,cy)=>{for(let dy=-4;dy<=4;dy++)for(let dx=-4;dx<=4;dx++){const x=cx+dx,y=cy+dy;if(x>=0&&x<size&&y>=0&&y<size){const d=Math.max(Math.abs(dx),Math.abs(dy));set(x,y,d!=2&&d!=4)}}};
 finder(3,3);finder(size-4,3);finder(3,size-4);
 const ap=[];if(ver>1){const n=Math.floor(ver/7)+2,step=Math.ceil((ver*4+4)/(n*2-2))*2;ap.push(6);for(let p=size-7;ap.length<n;p-=step)ap.splice(1,0,p)}
 ap.forEach((cx,i)=>ap.forEach((cy,j)=>{if((i==0&&j==0)||(i==0&&j==ap.length-1)||(i==ap.length-1&&j==0))return;for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++)set(cx+dx,cy+dy,Math.max(Math.abs(dx),Math.abs(dy))!=1)}));
 const fmt=mask=>{const d=mask;let r=d;for(let i=0;i<10;i++)r=(r<<1)^((r>>>9)*0x537);const b=((d<<10)|r)^0x5412,g=i=>(b>>>i)&1;
  for(let i=0;i<=5;i++)set(8,i,g(i));set(8,7,g(6));set(8,8,g(7));set(7,8,g(8));for(let i=9;i<15;i++)set(14-i,8,g(i));
  for(let i=0;i<8;i++)set(size-1-i,8,g(i));for(let i=8;i<15;i++)set(8,size-15+i,g(i));set(8,size-8,true)};
 fmt(0);
 if(ver>=7){let r=ver;for(let i=0;i<12;i++)r=(r<<1)^((r>>>11)*0x1F25);const b=(ver<<12)|r;for(let i=0;i<18;i++){const a=size-11+i%3,c=Math.floor(i/3),d=(b>>>i)&1;set(a,c,d);set(c,a,d)}}
 let k=0;for(let right=size-1;right>=1;right-=2){if(right==6)right=5;for(let v=0;v<size;v++)for(let j=0;j<2;j++){const x=right-j,up=((right+1)&2)==0,y=up?size-1-v:v;if(!fn[y][x]&&k<all.length*8){M[y][x]=((all[k>>>3]>>>(7-(k&7)))&1)==1;k++}}}
 const maskFn=[(x,y)=>(x+y)%2==0,(x,y)=>y%2==0,(x,y)=>x%3==0,(x,y)=>(x+y)%3==0,(x,y)=>(Math.floor(x/3)+Math.floor(y/2))%2==0,(x,y)=>x*y%2+x*y%3==0,(x,y)=>(x*y%2+x*y%3)%2==0,(x,y)=>((x+y)%2+x*y%3)%2==0];
 const applyMask=m=>{for(let y=0;y<size;y++)for(let x=0;x<size;x++)if(!fn[y][x]&&maskFn[m](x,y))M[y][x]=!M[y][x]};
 const penalty=()=>{let p=0;for(let a=0;a<2;a++)for(let i=0;i<size;i++){let run=1;for(let j=1;j<=size;j++){const cur=j<size?(a?M[j][i]:M[i][j]):null,prev=a?M[j-1][i]:M[i][j-1];if(j<size&&cur===prev)run++;else{if(run>=5)p+=run-2;run=1}}}
  for(let y=0;y<size-1;y++)for(let x=0;x<size-1;x++)if(M[y][x]==M[y][x+1]&&M[y][x]==M[y+1][x]&&M[y][x]==M[y+1][x+1])p+=3;
  let dark=0;M.forEach(r=>r.forEach(c=>{if(c)dark++}));p+=Math.floor(Math.abs(dark*20-size*size*10)/(size*size))*10;return p};
 let best=0,bp=1e9;for(let m=0;m<8;m++){applyMask(m);const pn=penalty();if(pn<bp){bp=pn;best=m}applyMask(m)}
 applyMask(best);fmt(best);return M;
}
function drawQR(canvas,text){const M=makeQR(text),n=M.length,q=4,s=Math.floor(canvas.width/(n+q*2)),off=Math.floor((canvas.width-s*n)/2),c=canvas.getContext('2d');
 c.fillStyle='#fff';c.fillRect(0,0,canvas.width,canvas.height);c.fillStyle='#000';for(let y=0;y<n;y++)for(let x=0;x<n;x++)if(M[y][x])c.fillRect(off+x*s,off+y*s,s,s)}

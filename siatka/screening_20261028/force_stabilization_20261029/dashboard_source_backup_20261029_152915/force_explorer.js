/* Responsive force explorer; measured rows embedded in this HTML only. */
const forceColours={M03:'#14796f',M02:'#c65928',M04:'#5267ad',M05:'#6d7136'};
const forceMeshes=Object.keys(evidence.histories).filter(m=>evidence.histories[m].length);
const forceRows=Object.fromEntries(forceMeshes.map(m=>[m,[...new Map(evidence.histories[m].map(r=>[Number(r.physical_time_s).toFixed(9),r])).values()].sort((a,b)=>a.physical_time_s-b.physical_time_s)]));
let forceRange='continuation';
document.querySelector('[data-force-range="recent"]').disabled=Math.min(...Object.values(forceRows).map(a=>a.at(-1).physical_time_s))<.6;
const chartDefs=[{id:'cdChart',key:'CD',label:'Drag coefficient, CD',digits:5},{id:'clChart',key:'CL_total',label:'Lift coefficient, CL',digits:4}];
function rangeBounds(){
 const ends=Object.values(forceRows).filter(a=>a.length).map(a=>a.at(-1).physical_time_s);
 const end=Math.max(...ends),common=Math.min(...ends);
 return forceRange==='startup'?[0,end]:forceRange==='recent'?[Math.max(.2,common-.4),common]:[.2,end];
}
function renderForceChart(def){
 const host=document.getElementById(def.id),svg=host.querySelector('svg');
 const [lo,hi]=rangeBounds(),series=Object.fromEntries(Object.entries(forceRows).map(([m,rr])=>[m,rr.filter(r=>r.physical_time_s>=lo-1e-8&&r.physical_time_s<=hi+1e-8)]));
 const vals=Object.values(series).flat().map(r=>r[def.key]).filter(Number.isFinite);
 if(!vals.length)return;
 const w=Math.max(260,host.clientWidth-2),h=w<600?290:340,left=w<600?68:78,right=22,top=18,bottom=50;
 let ymin=Math.min(...vals),ymax=Math.max(...vals),pad=Math.max((ymax-ymin)*.12,Math.abs(ymax)*.004,1e-6);
 ymin-=pad;ymax+=pad;
 const X=t=>left+(t-lo)/(hi-lo||1)*(w-left-right),Y=v=>h-bottom-(v-ymin)/(ymax-ymin)*(h-top-bottom);
 const fixed=forceRange==='startup'?2:def.digits;
 svg.setAttribute('viewBox','0 0 '+w+' '+h);svg.setAttribute('width',w);svg.setAttribute('height',h);
 let s='<title>'+def.label+' — measured samples, '+lo.toFixed(3)+' to '+hi.toFixed(3)+' s</title><rect width="'+w+'" height="'+h+'" fill="white"/>';
 const ticks=w<600?4:6;
 for(let i=0;i<=4;i++){const v=ymin+(ymax-ymin)*i/4,y=Y(v);s+='<line x1="'+left+'" y1="'+y+'" x2="'+(w-right)+'" y2="'+y+'" stroke="#e4ebee"/><text x="'+(left-11)+'" y="'+(y+4)+'" text-anchor="end" fill="#4b6372" font-size="13" font-family="Segoe UI,Arial">'+v.toFixed(fixed)+'</text>';}
 for(let i=0;i<=ticks;i++){const t=lo+(hi-lo)*i/ticks,x=X(t);s+='<line x1="'+x+'" y1="'+top+'" x2="'+x+'" y2="'+(h-bottom)+'" stroke="#f0f3f5"/><text x="'+x+'" y="'+(h-bottom+24)+'" text-anchor="middle" fill="#4b6372" font-size="13" font-family="Segoe UI,Arial">'+t.toFixed(2)+'</text>';}
 if(lo<.2&&hi>.2)s+='<line x1="'+X(.2)+'" y1="'+top+'" x2="'+X(.2)+'" y2="'+(h-bottom)+'" stroke="#7c8c95" stroke-dasharray="3 4"/><text x="'+(X(.2)+6)+'" y="'+(top+15)+'" fill="#536b79" font-size="12" font-family="Segoe UI,Arial">Restart</text>';
 s+='<text x="'+((left+w-right)/2)+'" y="'+(h-6)+'" text-anchor="middle" fill="#4b6372" font-size="13" font-family="Segoe UI,Arial">Physical time [s]</text>';
 for(const [mesh,rr] of Object.entries(series)){
  if(!rr.length)continue;
  const d=rr.map((r,i)=>(i?'L':'M')+X(r.physical_time_s).toFixed(2)+','+Y(r[def.key]).toFixed(2)).join(' ');
  const last=rr.at(-1);s+='<path class="measured-line" data-mesh="'+mesh+'" data-count="'+rr.length+'" data-first-time="'+rr[0].physical_time_s+'" data-last-value="'+last[def.key]+'" d="'+d+'" fill="none" stroke="'+forceColours[mesh]+'" stroke-width="2.7" '+(mesh==='M02'?'stroke-dasharray="7 3"':'')+'/><circle cx="'+X(last.physical_time_s)+'" cy="'+Y(last[def.key])+'" r="4.5" fill="'+forceColours[mesh]+'"/>';
 }
 s+='<g class="crosshair" visibility="hidden"><line y1="'+top+'" y2="'+(h-bottom)+'" stroke="#83949e" stroke-dasharray="3 4"/></g>';
 svg.innerHTML=s;
 host.querySelector('.chart-readout').textContent='Hover or touch the chart to read measured values.';
 svg.onpointermove=e=>{
  const rect=svg.getBoundingClientRect(),px=(e.clientX-rect.left)*w/rect.width;
  const t=lo+(px-left)/(w-left-right)*(hi-lo);if(t<lo||t>hi)return;
  const group=svg.querySelector('.crosshair');group.setAttribute('visibility','visible');
  group.firstElementChild.setAttribute('x1',X(t));group.firstElementChild.setAttribute('x2',X(t));
  const bits=[];
  for(const [mesh,rr] of Object.entries(series)){
   if(!rr.length||t>rr.at(-1).physical_time_s+.0005||t<rr[0].physical_time_s-.0005)continue;
   let a=0,b=rr.length-1;while(a<b){const mid=Math.floor((a+b)/2);if(rr[mid].physical_time_s<t)a=mid+1;else b=mid;}
   let row=rr[a];if(a>0&&Math.abs(rr[a-1].physical_time_s-t)<Math.abs(row.physical_time_s-t))row=rr[a-1];
   bits.push(mesh+' '+row[def.key].toFixed(6)+' at '+row.physical_time_s.toFixed(3)+' s');
  }
  host.querySelector('.chart-readout').textContent=bits.join('   |   ')||'No sample at this time.';
 };
 svg.onpointerleave=()=>svg.querySelector('.crosshair').setAttribute('visibility','hidden');
 host.querySelector('.svg-download').onclick=()=>saveFile(def.key+'_'+forceRange+'.svg',new XMLSerializer().serializeToString(svg),'image/svg+xml');
}
function renderForces(){
 const [lo,hi]=rangeBounds();
 document.getElementById('forceRangeNote').textContent=(forceRange==='startup'?'Full startup is visible; the initial impulse dominates this scale. ':forceRange==='recent'?'Same physical-time interval for both meshes. ':'Startup before 0.2 s is outside this view. ')+lo.toFixed(3)+'–'+hi.toFixed(3)+' s · raw samples, no smoothing · y-axes fit the visible data.';
 for(const def of chartDefs){
  const host=document.getElementById(def.id);
  host.querySelector('.chart-values').innerHTML=forceMeshes.map(m=>{const rr=forceRows[m].filter(r=>r.physical_time_s>=lo-1e-8&&r.physical_time_s<=hi+1e-8),v=rr.at(-1);return v?'<span style="color:'+forceColours[m]+'"><b>'+m+'</b> '+v[def.key].toFixed(def.digits)+' <small>at '+v.physical_time_s.toFixed(3)+' s</small></span>':''}).join('');
  renderForceChart(def);
 }
}
document.querySelectorAll('[data-force-range]').forEach(b=>b.onclick=()=>{
 forceRange=b.dataset.forceRange;document.querySelectorAll('[data-force-range]').forEach(n=>n.setAttribute('aria-pressed',String(n===b)));renderForces();
});
new ResizeObserver(()=>renderForces()).observe(document.getElementById('forceExplorer'));
renderForces();
/* Enlarge fields and diagnostics without another file. */
const viewer=document.getElementById('imageViewer'),viewerImg=viewer.querySelector('img');
let imageOpener;
document.querySelectorAll('figure img').forEach(img=>{
 img.tabIndex=0;img.setAttribute('role','button');img.setAttribute('aria-label','Enlarge: '+img.alt);
 function open(){imageOpener=img;viewerImg.src=img.src;viewerImg.alt=img.alt;viewerImg.classList.remove('original-size');viewer.showModal();}
 img.onclick=open;img.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}};
});
document.getElementById('closeImage').onclick=()=>viewer.close();
document.getElementById('fitImage').onclick=()=>viewerImg.classList.remove('original-size');
document.getElementById('actualImage').onclick=()=>viewerImg.classList.add('original-size');
viewer.addEventListener('close',()=>imageOpener?.focus());
viewer.addEventListener('click',e=>{if(e.target===viewer)viewer.close();});

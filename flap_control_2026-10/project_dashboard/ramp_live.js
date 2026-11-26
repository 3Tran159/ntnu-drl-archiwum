/* NTNU SCIENCE · independent read-only active flap monitor. */
(function(){
"use strict";
const $=id=>document.getElementById(id);
const ok=x=>typeof x==="number"&&Number.isFinite(x);
const C={teal:"#53e2cc",blue:"#80b6ff",amber:"#f3c17b",rose:"#f28e98",violet:"#b7a7fa"};
const S={data:null,cursor:null,zoom:null,loading:false,enabled:new Set(["angle","actual_angle","rate","CL","CD","Fx","Fz","Mh","pabs","mass","overset","k_floor","omega_floor","min_quality","Pmech"]),range:null};
const charts=[
 ["rl-angle-chart","time",[["angle","Commanded δ",C.blue],["actual_angle","Measured δ",C.teal]],"deg"],
 ["rl-rate-chart","time",[["rate","Angular rate",C.teal]],"deg/s"],
 ["rl-cl-chart","time",[["CL","CL",C.teal]],"[-]"],
 ["rl-cd-chart","time",[["CD","CD",C.blue]],"[-]"],
 ["rl-fx-chart","time",[["Fx","Fx",C.blue]],"N"],
 ["rl-fz-chart","time",[["Fz","Fz",C.teal]],"N"],
 ["rl-mh-chart","time",[["Mh","Mh",C.amber]],"N·m"],
 ["rl-power-chart","time",[["Pmech","Signed Pmech",C.violet]],"W"],
 ["rl-pabs-chart","time",[["pabs","pABS minimum",C.teal]],"kPa"],
 ["rl-mass-chart","time",[["mass","Mass imbalance",C.blue]],"[-]"],
 ["rl-overset-chart","time",[["overset","Overset errors",C.amber]],"cells"],
 ["rl-floor-chart","time",[["k_floor","k floor",C.blue],["omega_floor","ω floor",C.amber]],"cells"],
 ["rl-quality-chart","time",[["min_quality","Qmin",C.teal]],"[-]"],
 ["rl-cl-angle-chart","param",["actual_angle","CL"],"[-]"],
 ["rl-cd-angle-chart","param",["actual_angle","CD"],"[-]"],
 ["rl-mh-angle-chart","param",["actual_angle","Mh"],"N·m"],
 ["rl-mh-rate-chart","param",["rate","Mh"],"N·m"]
];
const escapeHTML=v=>String(v??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
function fmt(n,d=3){if(!ok(n))return "N/A";return Math.abs(n)>0&&(Math.abs(n)<.00001||Math.abs(n)>=1e6)?n.toExponential(2):n.toLocaleString("en-US",{maximumFractionDigits:d});}
const pct=x=>ok(x)?fmt(x*100,1)+"%":"N/A";
function stamp(x){const dt=new Date(x);return x&&!Number.isNaN(+dt)?dt.toLocaleTimeString("en-GB"):"unavailable";}
function age(n){return ok(n)?n<60?fmt(n,0)+"s":fmt(n/60,1)+"min":"unknown";}
function set(id,text){const n=$(id);if(n)n.textContent=text==null?"—":String(text);}
function updatePill(id,state){const e=$(id);if(!e)return;e.dataset.state=state||"HOLD";e.textContent=state||"NO DATA";}
function fill(id,value){const e=$(id);if(e)e.style.width=(ok(value)?Math.max(0,Math.min(100,value*100)):0)+"%";}
function renderQuick(d){
 const row=d?.current||{};
 updatePill("rl-quick-status",d?.state||"OFFLINE");
 set("rl-quick-detail",(d?.experiment_id||"No ramp source")+" · "+(d?.phase||"UNKNOWN"));
 set("rl-quick-progress-text",pct(d?.progress));fill("rl-quick-progress",d?.progress);
 set("rl-quick-angle",ok(row.actual_angle)?fmt(row.actual_angle,3)+"°":"N/A");
 set("rl-quick-cl",fmt(row.CL,5));set("rl-quick-cd",fmt(row.CD,6));
 set("rl-quick-pabs",ok(row.pabs)?fmt(row.pabs/1000,2)+" kPa":"N/A");
 set("rl-quick-time",fmt(row.t,3));
 set("rl-quick-updated","Source "+stamp(d?.source_updated_at)+" · age "+age(d?.source_age_s));
}
function renderTop(d){
 const r=d?.current||{};
 updatePill("rl-state",d?.state||"OFFLINE");set("rl-phase",d?.phase||"UNKNOWN");
 set("rl-run-info",(d?.experiment_id||"No active ID")+" · "+(d?.active_job?.macro||"No active macro"));
 fill("rl-progress",d?.progress);set("rl-progress-text",pct(d?.progress)+" · "+(d?.profile?"0.650 → 0.850 s":"no confirmed profile"));
 set("rl-angle",fmt(r.actual_angle,4));set("rl-cl",fmt(r.CL,6));set("rl-cd",fmt(r.CD,7));
 set("rl-time",fmt(r.t,4));set("rl-mh",fmt(r.Mh,4));
 set("rl-pabs",ok(r.pabs)?fmt(r.pabs/1000,3):"N/A");
 const p=$("rl-pabs");if(p)p.style.color=ok(r.pabs)&&r.pabs<12340?C.rose:"";
 set("rl-data-count",(d?.rows||0)+" recorded samples · "+(d?.segments?.length||0)+" segments");
 set("rl-status-reason",d?.reason||"");
 set("rl-last-updated","Native CSV updated "+stamp(d?.source_updated_at)+" · "+age(d?.source_age_s)+" ago");
 set("rl-checkpoint",d?.checkpoint?.path||"No checkpoint recorded in current metadata");
 set("rl-source",d?.source_file||"No history source");
 set("rl-segments",(d?.segments||[]).map(x=>(x.id||"segment")+" · "+x.rows+" rows · "+(x.state||"unknown")).join("\n")||"No completed CSV segment available");
 set("rl-resid-note",d?.residuals_note||"Residuals cannot be mapped to physical time");
}
function currentRows(){
 const arr=S.data?.history||[],v=$("rl-window")?.value||"all";
 const selected=v==="all"?arr:arr.slice(-Number(v));
 if(!selected.length)return [];
 if(!S.zoom)return selected;
 return selected.filter(p=>p.t>=S.zoom.lo-1e-10&&p.t<=S.zoom.hi+1e-10);
}
function limits(rows){
 if(!rows.length)return null;
 let lo=rows[0].t,hi=rows[rows.length-1].t;
 if(hi<=lo){lo-=.001;hi+=.001;}
 return {lo,hi};
}
function nearest(t){
 const rows=S.data?.history||[];if(!rows.length)return null;
 let lo=0,hi=rows.length-1;
 while(lo<hi){let m=(lo+hi)>>1;if(rows[m].t<t)lo=m+1;else hi=m;}
 return lo>0&&Math.abs(rows[lo-1].t-t)<Math.abs(rows[lo].t-t)?rows[lo-1]:rows[lo];
}
function inspector(row){
 if(!row)return;
 set("rl-timeline-cursor","t "+fmt(row.t,4)+" s · step "+fmt(row.step,0)+" · iteration "+fmt(row.iteration,0));
 set("rl-time-selection",row.segment||"recorded sample");
 const fields=[
 ["δ commanded",row.angle,"°",4],["δ measured",row.actual_angle,"°",4],
 ["ω recorded",row.rate,"°/s",3],["CL",row.CL,"[-]",6],["CD",row.CD,"[-]",7],
 ["Fx",row.Fx,"N",3],["Fz",row.Fz,"N",3],["Mh",row.Mh,"N·m",3],
 ["pabs min",ok(row.pabs)?row.pabs/1000:null,"kPa",3],
 ["pabs reserve",ok(row.pabs)?(row.pabs-12340)/1000:null,"kPa",3],
 ["Mass imbalance",row.mass,"[-]",4],["Overset errors",row.overset,"cells",0],
 ["k floor",row.k_floor,"cells",0],["ω floor",row.omega_floor,"cells",0],
 ["Min Q",row.min_quality,"[-]",4],["Min volume",row.min_volume,"m³",5],
 ["Face validity",row.face_validity,"[-]",4],["y+ maximum",row.yplus_max,"[-]",1],
 ["μt/μ maximum",row.viscosity_ratio,"[-]",2],["Signed Pmech",row.Pmech,"W",3]];
 $("rl-field-values").innerHTML=fields.map(([k,v,u,d])=>"<div><small>"+escapeHTML(k)+" ["+escapeHTML(u)+"]</small><b>"+escapeHTML(fmt(v,d))+"</b></div>").join("");
}
function plotGeo(){
 const mobile=window.innerWidth<=600,w=mobile?420:650,h=mobile?245:260;
 return {w,h,left:mobile?64:67,right:w-20,top:18,bottom:h-38};
}
function markCursor(t){
 S.cursor=t;inspector(nearest(t));
 if(typeof window.NTNU_FLOW_CURSOR_TIME==="function")window.NTNU_FLOW_CURSOR_TIME(t);
 if(!S.range)return;
 const g=plotGeo();
 document.querySelectorAll(".rl-plot .rl-cursor[data-kind='time']").forEach(line=>{
  const x=g.left+(g.right-g.left)*Math.max(0,Math.min(1,(t-S.range.lo)/(S.range.hi-S.range.lo)));
  line.setAttribute("x1",x);line.setAttribute("x2",x);
  line.classList.toggle("show",t>=S.range.lo&&t<=S.range.hi);
 });
}
function short(n){if(!ok(n))return "N/A";return Math.abs(n)>0&&(Math.abs(n)<1e-5||Math.abs(n)>99999)?n.toExponential(1):fmt(n,Math.abs(n)<.01?5:Math.abs(n)<1?3:2);}
function chart(id,series,opts={}){
 const el=$(id);if(!el)return;
 const candidates=series.filter(s=>s.points.length);
 if(!candidates.length){el.innerHTML="<div class='rl-nodata'><b>NO RECORDED DATA</b>Signal missing in native CSV or series disabled.</div>";return;}
 const {w,h,left,right,top,bottom}=plotGeo();
 const allX=candidates.flatMap(s=>s.points.map(p=>p.x));
 const allY=candidates.flatMap(s=>s.points.map(p=>opts.log?Math.log10(p.y):p.y));
 if(opts.threshold!=null)allY.push(opts.threshold);
 let lo=opts.xrange?opts.xrange.lo:Math.min(...allX),hi=opts.xrange?opts.xrange.hi:Math.max(...allX);
 if(hi<=lo){lo-=0.001;hi+=0.001;}
 let ymin=Math.min(...allY),ymax=Math.max(...allY);
 if(ymax<=ymin){const delta=Math.max(Math.abs(ymin)*.02,0.00001);ymin-=delta;ymax+=delta;}
 else {const dy=(ymax-ymin)*.12;ymin-=dy;ymax+=dy;}
 const X=x=>left+(x-lo)/(hi-lo)*(right-left),Y=y=>bottom-(y-ymin)/(ymax-ymin)*(bottom-top);
 const f=n=>Number(n.toFixed(3));
 let svg="<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 "+w+" "+h+"' preserveAspectRatio='xMidYMid meet' role='img' aria-label='"+escapeHTML(id)+"'>";
 svg+="<rect width='"+w+"' height='"+h+"' fill='#0e1926'/>";
 if(opts.kind==="time"&&S.data?.profile){
  const a=S.data.profile.start_s,b=S.data.profile.end_s;
  if(a<hi&&b>lo){const aa=Math.max(a,lo),bb=Math.min(b,hi);svg+="<rect x='"+f(X(aa))+"' y='"+top+"' width='"+f(X(bb)-X(aa))+"' height='"+(bottom-top)+"' fill='#123b39' opacity='.38'/>";}
  [[a,"RAMP"],[b,"HOLD"]].forEach(([x,label])=>{if(x<lo||x>hi)return;const at=f(X(x));
   svg+="<line x1='"+at+"' x2='"+at+"' y1='"+top+"' y2='"+bottom+"' stroke='#567b83' stroke-dasharray='4 4'/>";
   svg+="<text x='"+(at+4)+"' y='12' fill='#7aafb0' font-size='10'>"+label+"</text>";});
 }
 for(let i=0;i<=4;i++){
  const x=left+i*(right-left)/4,y=top+i*(bottom-top)/4;
  svg+="<line x1='"+x+"' x2='"+x+"' y1='"+top+"' y2='"+bottom+"' stroke='#1d3044'/>";
  svg+="<line x1='"+left+"' x2='"+right+"' y1='"+y+"' y2='"+y+"' stroke='#25364a'/>";
  svg+="<text class='rl-axislabel' x='"+x+"' y='"+(h-15)+"' fill='#8da3b5' text-anchor='middle'>"+escapeHTML(short(lo+i*(hi-lo)/4))+"</text>";
  const val=ymax-i*(ymax-ymin)/4;
  svg+="<text class='rl-axislabel' x='56' y='"+(y+4)+"' fill='#8da3b5' text-anchor='end'>"+escapeHTML(opts.log?"10^"+fmt(val,1):short(val))+"</text>";
 }
 if(opts.threshold!=null){
  const y=f(Y(opts.threshold));svg+="<line x1='"+left+"' x2='"+right+"' y1='"+y+"' y2='"+y+"' stroke='"+C.rose+"' stroke-width='1.4' stroke-dasharray='6 4'/>";
  svg+="<text x='"+(right-5)+"' y='"+(y-6)+"' font-size='11' text-anchor='end' fill='"+C.rose+"'>12.34 kPa threshold</text>";
 }
 candidates.forEach(s=>{
  // Break a displayed line over missing numerical steps; never bridge absent data.
  const visible=s.points.filter(p=>p.x>=lo-1e-10&&p.x<=hi+1e-10),groups=[];
  let group=[],previous=null;
  for(const p of visible){
   const isGap=opts.kind==="time"&&previous&&p.x-previous.x>2.5*(S.data?.profile?.dt_s||.002);
   if(isGap&&group.length){groups.push(group);group=[];}
   group.push(p);previous=p;
  }
  if(group.length)groups.push(group);
  groups.forEach(segment=>{
   const xy=segment.map(p=>f(X(p.x))+","+f(Y(opts.log?Math.log10(p.y):p.y))).join(" ");
   if(segment.length===1)svg+="<circle cx='"+f(X(segment[0].x))+"' cy='"+f(Y(segment[0].y))+"' r='2.8' fill='"+s.color+"'/>";
   else svg+="<polyline points='"+xy+"' stroke='"+s.color+"' stroke-width='2.2' fill='none' stroke-linejoin='round' vector-effect='non-scaling-stroke'/>";
  });
 });
 svg+="<text x='"+(w/2)+"' y='"+(h-1)+"' fill='#92adbf' text-anchor='middle' font-family='Consolas,monospace' font-size='13'>"+escapeHTML(opts.xLabel||"Physical time [s]")+"</text>";
 if(opts.kind==="time"){
  const cursorPos=ok(S.cursor)?X(S.cursor):0;
  svg+="<line class='rl-cursor"+(ok(S.cursor)&&S.cursor>=lo&&S.cursor<=hi?" show":"")+"' data-kind='time' x1='"+f(cursorPos)+"' x2='"+f(cursorPos)+"' y1='"+top+"' y2='"+bottom+"'/>";
  svg+="<rect class='rl-hit' x='"+left+"' y='"+top+"' width='"+(right-left)+"' height='"+(bottom-top)+"' fill='transparent'/>";
 }
 svg+="</svg>";
 el.innerHTML=svg;
 if(opts.kind==="time"){
  const root=el.querySelector("svg");
  const select=event=>{
   const rect=root.getBoundingClientRect();
   const x=event.clientX-rect.left;
   const ratio=(x/rect.width*w-left)/(right-left);
   markCursor(lo+Math.max(0,Math.min(1,ratio))*(hi-lo));
  };
  root.addEventListener("pointermove",event=>{if(event.pointerType!=="touch")select(event);});
  root.addEventListener("click",select);
 }
}

function makeSeries(rows,item,scale=1){
 const [key,name,color]=item;
 if(!S.enabled.has(key))return {name,color,points:[]};
 return {name,color,points:rows.filter(p=>ok(p.t)&&ok(p[key])).map(p=>({x:p.t,y:p[key]*scale}))};
}
function renderPlots(){
 const rows=currentRows(),range=limits(rows);
 S.range=range;
 if(!range){charts.forEach(([id])=>chart(id,[]));chart("rl-resid-chart",[]);return;}
 charts.forEach(([id,type,items])=>{
  if(type==="time"){
   const scale=id==="rl-pabs-chart"?.001:1;
   const series=items.map(item=>makeSeries(rows,item,scale));
   chart(id,series,{kind:"time",xrange:range,threshold:id==="rl-pabs-chart"?12.34:null});
  }else{
   const [xKey,yKey]=items;
   const points=S.enabled.has(yKey)?rows.filter(p=>ok(p[xKey])&&ok(p[yKey])).map(p=>({x:p[xKey],y:p[yKey]})):[];
   chart(id,[{name:yKey,color:C.teal,points}],{kind:"param",xLabel:xKey==="rate"?"Angular velocity [deg/s]":"Measured flap δ [deg]"});
  }
 });
 const residuals=S.data?.residuals||{};
 const palette=[C.teal,C.blue,C.amber,C.violet,C.rose,"#82b9a8"];
 const entries=Object.entries(residuals).slice(0,6);
 const traces=entries.map(([key,value],idx)=>({
  name:key,color:palette[idx%palette.length],
  points:(value.points||[]).filter(p=>ok(p.x)&&ok(p.y)&&p.y>0).map(p=>({x:p.x,y:p.y}))
 }));
 chart("rl-resid-chart",traces,{kind:"residuals",log:true,xLabel:"Native solver iteration [-]"});
 if(ok(S.cursor))markCursor(S.cursor);
 else if(rows.length)inspector(rows[rows.length-1]);
}
function seriesToggles(){
 const defs=[
 ["angle","Commanded δ"],["actual_angle","Actual δ"],["rate","Angular rate"],
 ["CL","CL"],["CD","CD"],["Fx","Fx"],["Fz","Fz"],["Mh","Mh"],
 ["pabs","pabs"],["mass","Mass balance"],["overset","Overset errors"],
 ["k_floor","k floor"],["omega_floor","ω floor"],["min_quality","Qmin"],["Pmech","Signed Pmech"]
 ];
 const wrap=$("rl-toggles");if(!wrap)return;
 wrap.innerHTML="<span class='rl-label'>SHOW SERIES</span>"+defs.map(([key,label])=>"<label><input type='checkbox' data-rl-channel='"+escapeHTML(key)+"' "+(S.enabled.has(key)?"checked":"")+">"+escapeHTML(label)+"</label>").join("");
 wrap.querySelectorAll("[data-rl-channel]").forEach(el=>el.addEventListener("change",()=>{
  if(el.checked)S.enabled.add(el.dataset.rlChannel);else S.enabled.delete(el.dataset.rlChannel);
  renderPlots();
 }));
}
function zoom(multiplier){
 const rows=currentRows(),full=limits(rows);if(!full)return;
 const total=full.hi-full.lo;
 const center=ok(S.cursor)?S.cursor:(full.hi+full.lo)/2;
 const width=Math.min(total,Math.max(.002,total*multiplier));
 S.zoom={lo:Math.max(full.lo,center-width/2),hi:Math.min(full.hi,center+width/2)};
 if(S.zoom.hi-S.zoom.lo<width){if(S.zoom.lo===full.lo)S.zoom.hi=Math.min(full.hi,S.zoom.lo+width);else S.zoom.lo=Math.max(full.lo,S.zoom.hi-width);}
 renderPlots();
}
function download(name,blob){
 const a=document.createElement("a"),url=URL.createObjectURL(blob);
 a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
 window.setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function exportCsv(){
 const data=S.data;if(!data?.history?.length)return;
 const headers=["t","step","iteration","segment","angle","actual_angle","rate","CL","CD","Fx","Fz","Mh","pabs","mass","cav_margin","overset","k_floor","omega_floor","viscosity_ratio","min_quality","min_volume","face_validity","yplus_max","Pmech","source"];
 const escapeCsv=s=>'"'+String(s??"").replaceAll('"','""')+'"';
 const body=[headers.join(",")].concat(data.history.map(r=>headers.map(k=>escapeCsv(r[k])).join(","))).join("\r\n");
 download("NTNU_"+(data.experiment_id||"ramp")+"_native_history.csv",new Blob(["\uFEFF"+body+"\r\n"],{type:"text/csv;charset=utf-8"}));
}
function exportPng(){
 const id=$("rl-export-plot")?.value;
 const svg=$(id)?.querySelector("svg");if(!svg)return;
 const clone=svg.cloneNode(true);
 // Cursor is an interaction-only overlay, not part of exported data.
 clone.querySelectorAll(".rl-cursor,.rl-hit").forEach(x=>x.remove());
 clone.setAttribute("width","1600");clone.setAttribute("height","504");
 const raw=new XMLSerializer().serializeToString(clone);
 const url="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(raw);
 const pic=new Image();
 pic.onload=()=>{
  const canvas=document.createElement("canvas");canvas.width=1600;canvas.height=504;
  const ctx=canvas.getContext("2d");ctx.fillStyle="#0e1926";ctx.fillRect(0,0,1600,504);ctx.drawImage(pic,0,0,1600,504);
  canvas.toBlob(blob=>{if(blob)download("NTNU_"+id+".png",blob);URL.revokeObjectURL(url);},"image/png");
 };
 pic.onerror=()=>URL.revokeObjectURL(url);
 pic.src=url;
}
function bind(){
 $("rl-window")?.addEventListener("change",()=>{S.zoom=null;renderPlots();});
 $("rl-zoom-in")?.addEventListener("click",()=>zoom(.58));
 $("rl-zoom-out")?.addEventListener("click",()=>{const rows=windowRowsWithoutZoom(),rng=limits(rows);if(!rng)return;const lim=S.zoom||rng;const center=(lim.lo+lim.hi)/2;const width=Math.min(rng.hi-rng.lo,(lim.hi-lim.lo)*1.8);S.zoom={lo:Math.max(rng.lo,center-width/2),hi:Math.min(rng.hi,center+width/2)};renderPlots();});
 $("rl-reset")?.addEventListener("click",()=>{S.zoom=null;S.cursor=null;renderPlots();});
 $("rl-export-csv")?.addEventListener("click",exportCsv);
 $("rl-export-png")?.addEventListener("click",exportPng);
 document.querySelectorAll("[data-page='ramp'],[data-open='ramp']").forEach(x=>x.addEventListener("click",()=>{if(S.data)renderPlots();}));
 window.addEventListener("hashchange",()=>{if(location.hash==="#ramp"&&S.data)renderPlots();});
 window.addEventListener("resize",()=>{if(location.hash==="#ramp"&&S.data)renderPlots();});
 seriesToggles();
}
function windowRowsWithoutZoom(){
 const history=S.data?.history||[];const w=$("rl-window")?.value||"all";
 return w==="all"?history:history.slice(-Number(w));
}
async function update(){
 if(S.loading)return;S.loading=true;
 try{
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),11000);
  let resp;
  try{resp=await fetch("/api/ramp",{cache:"no-store",signal:controller.signal});}
  finally{clearTimeout(timeout);}
  if(!resp.ok)throw Error("HTTP "+resp.status);
  const data=await resp.json();
  if(!Array.isArray(data.history))throw Error("No ramp history");
  S.data=data;window.NTNU_RAMP_DATA=data;
  // Ramp is an archived, independently selected experiment. Only the
  // controller registry in app.js may author Overview/CFD Live status.
  renderTop(data);
  if($("page-ramp")?.classList.contains("active"))renderPlots();
 }catch(err){
  if(S.data){S.data.state="STALE";S.data.reason="Dashboard ramp feed unavailable: "+err.message;renderTop(S.data);}
  else{updatePill("rl-state","OFFLINE");set("rl-status-reason",String(err.message));}
 }finally{S.loading=false;}
}
function boot(){
 window.NTNU_RAMP_SELECT_TIME=function(t){if(Number.isFinite(t)&&S.data){markCursor(t);if(location.hash==="#ramp")renderPlots();}};
 bind();update();setInterval(update,15000);
}
document.addEventListener("DOMContentLoaded",boot);
})();

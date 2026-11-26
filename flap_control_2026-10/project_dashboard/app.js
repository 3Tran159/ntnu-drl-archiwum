/* NTNU Science · Project Control Center. No external packages and no CFD actions. */
(function(){
"use strict";
var state={snapshot:null,series:{},history:null,current:"overview",syncing:false,hardwareHistory:[],
 runRegistry:[],activeRunId:null,liveFollowActive:true,liveInitialized:false,liveOverlay:new Set(),validationChoices:new Set(["B0","C0"]),registrySignature:""};
var COLORS={blue:"#80b6ff",teal:"#53e2cc",amber:"#f3c17b",rose:"#f28e98",muted:"#90a1b4"};
var METRIC={
  CL:["Lift coefficient","CL [-]"],
  CD:["Drag coefficient","CD [-]"],
  Fx:["Drag force","Fx [N]"],
  Fz:["Lift force","Fz [N]"],
  Mh:["Flap hinge moment","Mh [N·m]"],
  pabs:["Minimum absolute pressure","pabs,min [Pa]"],
  cav:["Cavitation margin","pabs - pv [Pa]"],
  mass:["Relative mass imbalance","Mass imbalance [-]"],
  angle:["Flap deflection","δ [deg]"],
  angular_rate:["Flap angular speed","ω [deg/s]"],
  angle_error:["Angle tracking error","Δδ [deg]"],
  center_error:["Hinge center error","Δr [m]"],
  quality:["Minimum cell quality","Qmin [-]"],
  orphan:["Overset error cells","count [-]"]
};
var $=function(id){return document.getElementById(id);};
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
function set(id,text){var el=$(id);if(el)el.textContent=text==null?"—":String(text);}
function finite(n){return typeof n==="number"&&Number.isFinite(n);}
function fmt(n,d){if(!finite(n))return "N/A";var x=Math.abs(n);if(x>0&&(x<.0001||x>=1000000))return n.toExponential(2);return n.toLocaleString("en-US",{maximumFractionDigits:d===undefined?4:d,minimumFractionDigits:d===undefined?0:d});}
function signed(n,d){if(!finite(n))return "N/A";return (n>0?"+":"")+fmt(n,d);}
function pct(n){return finite(n)?signed(n,3)+"%":"N/A";}
function timeLabel(x){if(!x)return "No timestamp";var d=new Date(x);return Number.isNaN(+d)?String(x):d.toLocaleString("en-GB",{month:"short",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"});}
function tailPath(p){if(!p)return "—";var a=String(p).split(/[\\/]/);return a.slice(-2).join(" / ");}
function age(seconds){if(!finite(seconds))return "unknown";if(seconds<60)return Math.round(seconds)+" s ago";if(seconds<3600)return Math.round(seconds/60)+" min ago";return (seconds/3600).toFixed(1)+" h ago";}
function toast(msg){var el=$("toast");el.textContent=msg;el.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(function(){el.classList.remove("show");},2300);}
function pair(label,value,cls){return "<div class='kv'><dt>"+esc(label)+"</dt><dd"+(cls?" class='"+cls+"'":"")+">"+esc(value)+"</dd></div>";}
function makeMetric(title,val,unit,foot,cls){return "<div class='metric'><div class='metric-label'>"+esc(title)+"<span>"+esc(unit||"")+"</span></div><div class='metric-value "+(cls||"")+"'>"+esc(val)+"</div><div class='metric-foot'>"+esc(foot||"")+"</div></div>";}
function isPaused(data){return data&&data.state==="HOLD";}
function numStats(run,key){return run&&run.stats?run.stats[key]:null;}
async function fetchJSON(url){
  var controller=new AbortController(),id=setTimeout(function(){controller.abort();},9000);
  try{var res=await fetch(url,{cache:"no-store",signal:controller.signal});if(!res.ok)throw Error("HTTP "+res.status);return await res.json();}
  finally{clearTimeout(id);}
}
function initNavigation(){
  function change(name){
    if(!$("page-"+name))return;
    state.current=name;
    document.querySelectorAll(".page").forEach(function(e){e.classList.toggle("active",e.id==="page-"+name);});
    document.querySelectorAll(".navitem").forEach(function(e){e.classList.toggle("active",e.dataset.page===name);});
    set("top-current-page",($("page-"+name).dataset.title||name).toUpperCase());
    if(location.hash!=="#"+name)history.replaceState(null,"","#"+name);
    window.scrollTo({top:0,behavior:"instant"});
    if(name==="history")loadHistory();
    renderCurrent();
  }
  document.querySelectorAll("[data-page]").forEach(function(btn){btn.addEventListener("click",function(){change(btn.dataset.page);});});
  document.querySelectorAll("[data-open]").forEach(function(btn){btn.addEventListener("click",function(){change(btn.dataset.open);});});
  window.addEventListener("hashchange",function(){change(location.hash.slice(1)||"overview");});
  $("refresh-button").addEventListener("click",function(){sync(true);});
  $("copy-checkpoint").addEventListener("click",function(){
    var path=state.snapshot&&state.snapshot.checkpoint;
    if(!path)return toast("No checkpoint path available");
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(path).then(function(){toast("Checkpoint path copied");}).catch(function(){toast("Clipboard unavailable");});}
    else toast("Clipboard unavailable");
  });
  ["live-run","live-metric","live-window"].forEach(function(k){$(k).addEventListener("change",function(){
    if(k==="live-run"){state.liveFollowActive=false;$("live-follow-active").checked=false;
      $("live-metric").value=$("live-run").value==="K0"?"angle":"CL";}
    renderLive();refreshSelectedDynamicSeries().then(renderLive);
  });});
  $("live-follow-active").addEventListener("change",function(){
    state.liveFollowActive=this.checked;
    if(this.checked && state.activeRunId && state.runRegistry.some(r=>r.id===state.activeRunId)){
      $("live-run").value=state.activeRunId;
      refreshSelectedDynamicSeries().then(renderLive);
    }
  });
  $("wave-run").addEventListener("change",function(){renderWaves();});
  $("validation-registry-metric").addEventListener("change",renderDynamicValidation);
  $("export-chart").addEventListener("click",function(){
    var svg=$("live-chart").querySelector("svg");if(!svg)return toast("No chart to export");
    var str='<?xml version="1.0" encoding="UTF-8"?>\n'+new XMLSerializer().serializeToString(svg);
    var a=document.createElement("a"),objectURL=URL.createObjectURL(new Blob([str],{type:"image/svg+xml"}));
    a.href=objectURL;a.download="NTNU_"+$("live-run").value+"_"+$("live-metric").value+".svg";a.click();
    setTimeout(function(){URL.revokeObjectURL(objectURL);},1000);toast("SVG export created");
  });
  change((location.hash||"#overview").slice(1));
}
function blankChart(id,head,detail){
  var el=$(id);if(el)el.innerHTML="<div class='no-data'><strong>"+esc(head)+"</strong>"+esc(detail||"No validated measurements found.")+"</div>";
}
function plot(id,series,options){
  var node=$(id);if(!node)return;
  options=options||{};
  var all=[], transformed=[];
  (series||[]).forEach(function(s){
    var filtered=(s.points||[]).filter(function(p){return finite(p.x)&&finite(p.y)&&(options.log?p.y>0:true);});
    var points=filtered.map(function(p){return {x:p.x,y:options.log?Math.log10(p.y):p.y,raw:p.y};});
    transformed.push({name:s.name,color:s.color,points:points});
    all.push.apply(all,points);
  });
  if(!all.length)return blankChart(id,"NO DATA","This signal is not available in the recorded source.");
  var w=920,h=285,left=64,right=25,top=19,bottom=39;
  var xmin=Math.min.apply(null,all.map(function(p){return p.x;}));
  var xmax=Math.max.apply(null,all.map(function(p){return p.x;}));
  var ymin=Math.min.apply(null,all.map(function(p){return p.y;}));
  var ymax=Math.max.apply(null,all.map(function(p){return p.y;}));
  var xrange=xmax-xmin||1, yrange=ymax-ymin||Math.max(.000001,Math.abs(ymin)*.02);
  var padded=yrange*.12; ymin-=padded;ymax+=padded;yrange=ymax-ymin;
  var x=function(v){return left+(v-xmin)/(xmax-xmin||1)*(w-left-right);};
  var y=function(v){return top+(ymax-v)/yrange*(h-top-bottom);};
  var src="<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 "+w+" "+h+"' role='img' aria-label='"+esc(options.label||"scientific plot")+"' preserveAspectRatio='none'>";
  src+="<rect x='0' y='0' width='"+w+"' height='"+h+"' rx='5' fill='#0e1724'/>";
  for(var k=0;k<=4;k++){
    var yy=top+k*(h-top-bottom)/4;
    var val=ymax-k*yrange/4;
    var label=options.log?"1e"+fmt(val,1):fmt(val,Math.abs(val)<.01?5:3);
    src+="<line x1='"+left+"' y1='"+yy+"' x2='"+(w-right)+"' y2='"+yy+"' stroke='#263448' stroke-width='1'/>";
    src+="<text x='"+(left-10)+"' y='"+(yy+3.3)+"' fill='#8194a8' font-size='11' font-family='Consolas,monospace' text-anchor='end'>"+esc(label)+"</text>";
  }
  for(var j=0;j<=5;j++){
    var xx=left+j*(w-left-right)/5,t=xmin+j*xrange/5;
    src+="<line x1='"+xx+"' y1='"+top+"' x2='"+xx+"' y2='"+(h-bottom)+"' stroke='#1a2b3e' stroke-width='1'/>";
    src+="<text x='"+xx+"' y='"+(h-17)+"' fill='#8298a9' font-size='11' font-family='Consolas,monospace' text-anchor='middle'>"+fmt(t,Math.abs(xrange)<1?3:1)+"</text>";
  }
  src+="<text x='"+(w/2)+"' y='"+(h-2)+"' fill='#7490a6' font-size='11' text-anchor='middle'>"+esc(options.xLabel||"Physical time, t [s]")+"</text>";
  transformed.forEach(function(s,index){
    if(!s.points.length)return;
    var points=s.points.map(function(p){return x(p.x).toFixed(2)+","+y(p.y).toFixed(2);}).join(" ");
    var dash=index>=2?" stroke-dasharray='5 3'":"";
    src+="<polyline points='"+points+"' fill='none' stroke='"+esc(s.color||COLORS.blue)+"' stroke-width='2.1' stroke-linejoin='round' stroke-linecap='round' vector-effect='non-scaling-stroke'"+dash+"/>";
    var last=s.points[s.points.length-1];
    src+="<circle cx='"+x(last.x)+"' cy='"+y(last.y)+"' r='3.5' fill='"+esc(s.color||COLORS.blue)+"' />";
  });
  src+="<text x='"+left+"' y='11' fill='#8ba5b9' font-size='10' letter-spacing='1'>"+esc(options.label||"MEASURED")+"</text></svg>";
  node.innerHTML=src;
  var svg=node.querySelector("svg");
  if(!svg)return;
  var bubble=document.createElement("div");bubble.style.cssText="position:absolute;right:8px;top:8px;background:#112c38;border:1px solid #377478;border-radius:5px;color:#e5f7f5;font:11px Consolas,monospace;padding:6px 9px;display:none;pointer-events:none;";
  node.appendChild(bubble);
  svg.addEventListener("mousemove",function(e){
    var rect=svg.getBoundingClientRect();var px=(e.clientX-rect.left)/rect.width*w;
    var source=transformed.find(function(s){return s.points.length;});if(!source)return;
    var targetX=xmin+(px-left)/(w-left-right)*(xmax-xmin);
    var nearest=source.points.reduce(function(a,b){return Math.abs(b.x-targetX)<Math.abs(a.x-targetX)?b:a;});
    bubble.textContent=source.name+": "+fmt(nearest.raw,5)+" · t="+fmt(nearest.x,3)+" s";bubble.style.display="block";
  });
  svg.addEventListener("mouseleave",function(){bubble.style.display="none";});
}
function chartPoints(r,key,windowCount){
  if(!r)return [];
  var all=r.history.filter(function(p){return finite(p[key])&&finite(p.t);});
  if(windowCount!=="all"){all=all.slice(-Number(windowCount));}
  return all.map(function(p){return {x:p.t,y:p[key]};});
}
function registryStatus(meta){return String(meta?.status||"DIAGNOSTIC").toUpperCase();}
function registryName(meta){return (meta?.label||meta?.id||"run")+" · "+registryStatus(meta);}
function registryColor(index){
 return [COLORS.blue,COLORS.teal,COLORS.amber,COLORS.rose,"#bba4f7","#77bfac","#f0a46d","#ca9de5"][index%8];
}
function registryOptionsHTML(selection,type){
 const all=state.runRegistry||[];
 return all.map(function(meta){
  var status=registryStatus(meta),checked=selection.has(meta.id)?"checked":"";
  return "<label class='run-choice'><input type='checkbox' data-rgroup='"+type+"' data-run-id='"+esc(meta.id)+"' "+checked+"><span class='run-choice-name'>"+esc(meta.label||meta.id)+"</span><span class='run-choice-status' data-status='"+esc(status)+"'>"+esc(status)+"</span><small>"+esc(meta.count??"N/A")+" pts</small></label>";
 }).join("")||"<span class='registry-helper'>No controller cases available</span>";
}
function populateRegistryControls(){
 const list=state.runRegistry||[];
 if(!list.length)return;
 const select=$("live-run");
 const old=select.value;
 const available=new Set(list.map(x=>x.id));
 const signature=list.map(x=>x.id+":"+x.status+":"+x.count).join("|")+"|ACTIVE="+(state.activeRunId||"none");
 if(state.registrySignature===signature)return;
 state.registrySignature=signature;
 const options=list.map(m=>{
  const option=document.createElement("option");
  option.value=m.id;
  option.textContent=registryName(m);
  return option;
 });
 select.replaceChildren(...options);
 if(!state.liveInitialized){
  const candidate=list.find(m=>m.id===state.activeRunId)||
    list.find(m=>registryStatus(m)==="ACTIVE")||
    list.find(m=>!m.is_static_reference && m.count>=5);
  select.value=candidate?candidate.id:(available.has("B0")?"B0":list[0].id);
  state.liveInitialized=true;
 }else if(state.liveFollowActive && available.has(state.activeRunId)){
  select.value=state.activeRunId;
 }else{
  select.value=available.has(old)?old:(available.has("B0")?"B0":list[0].id);
 }
 $("live-follow-active").checked=state.liveFollowActive;
 for(const id of state.liveOverlay)if(!available.has(id))state.liveOverlay.delete(id);
 for(const id of state.validationChoices)if(!available.has(id))state.validationChoices.delete(id);
 const liveList=$("live-compare-list");
 liveList.innerHTML=registryOptionsHTML(state.liveOverlay,"live");
 const validList=$("validation-registry-picker");
 validList.innerHTML=registryOptionsHTML(state.validationChoices,"validation");
 set("registry-total",list.length+" RUNS");
 set("validation-registry-count",list.length+" AVAILABLE");
 [liveList,validList].forEach(el=>el.querySelectorAll("input[data-run-id]").forEach(input=>{
  input.addEventListener("change",function(){
   const dest=this.dataset.rgroup==="live"?state.liveOverlay:state.validationChoices;
   if(this.checked)dest.add(this.dataset.runId);else dest.delete(this.dataset.runId);
   refreshSelectedDynamicSeries().then(()=>{
    if(this.dataset.rgroup==="live")renderLive();else renderDynamicValidation();
   });
  });
 }));
}
async function refreshSelectedDynamicSeries(){
 const runs=new Set([state.activeRunId,$("live-run").value,...state.liveOverlay,...state.validationChoices]);
 const dynamic=Array.from(runs).filter(id=>id && !["B0","C0","K0","A0","W02","W03","W04pre"].includes(id));
 await Promise.all(dynamic.map(async id=>{
  try{state.series[id]=await fetchJSON("/api/run_series?id="+encodeURIComponent(id));}
  catch(error){console.warn("Dynamic controller history unavailable",id,error.message);}
 }));
}
function renderDynamicValidation(){
 if(!state.runRegistry?.length)return;
 const key=$("validation-registry-metric").value;
 const ids=Array.from(state.validationChoices).filter(id=>state.runRegistry.some(s=>s.id===id));
 const points=ids.map((id,i)=>{
  const run=state.series[id];
  return {name:(state.runRegistry.find(x=>x.id===id)?.label||id),
    color:registryColor(i),points:chartPoints(run,key,"all")};
 });
 plot("validation-registry-chart",points,{label:key+(["CL","CD","angle"].includes(key)?" [-]":"")});
 $("validation-registry-legend").innerHTML=ids.map((id,i)=>{
  const info=state.runRegistry.find(x=>x.id===id)||{};
  return "<span class='registry-legend-item'><span class='legend-dot' style='background:"+registryColor(i)+"'></span>"+esc(info.label||id)+" <small>("+esc(info.status||"DIAGNOSTIC")+")</small></span>";
 }).join("");
 $("validation-registry-table").innerHTML=ids.map(id=>{
  const run=state.series[id],meta=state.runRegistry.find(x=>x.id===id)||{};
  const stat=numStats(run,key);
  return "<tr><td>"+esc(meta.label||id)+" <span class='run-choice-status' data-status='"+esc(meta.status||"DIAGNOSTIC")+"'>"+esc(meta.status||"DIAGNOSTIC")+"</span></td>"+
   "<td>"+esc(run?.count??"N/A")+"</td>"+
   "<td>"+(stat?fmt(stat.mean,6):"N/A")+"</td>"+
   "<td>"+(stat?fmt(stat.from_s,3)+"–"+fmt(stat.to_s,3):"N/A")+"</td>"+
   "<td>"+esc(meta.segments??1)+"</td>"+
   "<td title='"+esc(meta.source||"")+"'>"+esc(tailPath(meta.source||""))+"</td></tr>";
 }).join("")||"<tr><td colspan='6'>Select a run to compare recorded data.</td></tr>";
}
function renderOverview(){
  var s=state.snapshot;if(!s)return;
  set("overview-source-time",timeLabel(s.source_status_at));
  set("overview-age",age(s.source_age_s));set("overview-footer-update","Last refresh "+new Date().toLocaleTimeString());
  set("overall-state",s.state||"OFFLINE");set("overall-reason",s.reason);
  $("status-pulse").className="pulse-circle"+(s.state==="RUNNING"?" running":s.state==="FAILED"?" failed":"");
  set("source-flag",s.paused?"PAUSE PROTECTED":"READ ONLY");
  set("m-phase",s.kinematic_passed?"02 / MOTION POC":"01 / VALIDATION");
  set("m-case",(s.case||"—").split(",")[0]);
  set("m-case-foot",s.kinematic_passed?"Frozen-flow sweep completed":"STAR-CCM+ 2606");
  set("m-time",fmt(s.physical_time_s,3));set("m-step","Step "+fmt(s.timestep,0)+" · Iteration "+fmt(s.iteration,0));
  set("m-gate",s.scientific_gate?"ACCEPTED":"PENDING");
  var v=s.validation||{};
  set("ov-bcl",fmt(v.B0&&v.B0.CL,6));set("ov-ccl",fmt(v.C0&&v.C0.CL,6));
  set("ov-dcl",pct(v.delta_CL_pct));set("ov-dcd",pct(v.delta_CD_pct));
  var max=Math.max(Math.abs(v.delta_CL_pct||0),Math.abs(v.delta_CD_pct||0));
  $("poc-fill").style.width=Math.max(1,Math.min(100,(max/2)*100))+"%";
  $("poc-fill").style.background=max<=1?COLORS.teal:COLORS.amber;
  set("poc-threshold","max Δ "+fmt(max,3)+"% · target <1%");
  set("ov-decision",s.decision||"No decision in current source.");
  set("ov-blocker",s.obstacle||"No explicit blocker.");
  set("ov-next",s.next||"Awaiting scientific decision.");
  var roadmap=document.querySelector(".roadmap-item:nth-child(2) b");
  if(roadmap)roadmap.textContent=s.kinematic_passed?"KINEMATIC PASS":"CHECK";
  set("checkpoint-path",s.checkpoint||"No checkpoint in source.");
  set("checkpoint-tag",s.checkpoint_verified?"REOPEN VERIFIED":s.checkpoint_complete?"SAVE COMPLETE":"REVIEW NEEDED");
  set("checkpoint-size",finite(s.checkpoint_bytes)?fmt(s.checkpoint_bytes/1e6,0)+" MB · source integrity metadata":"No verified file-size metadata");
  // Overview always follows the *current controller-owned experiment*. Flap Live
  // can still show its failed historical ramp, but must not replace this status.
  var meta=state.runRegistry.find(x=>x.id===state.activeRunId)||
    state.runRegistry.find(x=>!x.is_static_reference);
  if(meta){
    var series=state.series[meta.id],last=series&&series.history?.length?
      series.history[series.history.length-1]:null;
    var stat=registryStatus(meta);
    var title=String(meta.label||meta.id).replace(/_20[0-9]{6}.*$/,"").replace(/_/g," ");
    var current=meta.id===state.activeRunId;
    var displayed=current&&stat==="ACTIVE"?"RUNNING":stat;
    set("rl-quick-label",current?"CURRENT EXPERIMENT":"LATEST RECORDED EXPERIMENT");
    set("rl-quick-title",title);
    set("rl-quick-status",displayed);
    $("rl-quick-status").dataset.state=stat;
    set("rl-quick-detail",(last?.phase?last.phase+" · ":"")+(meta.experiment_id||meta.run_id||meta.id));
    set("rl-quick-progress-text",(meta.count??"N/A")+" samples");
    $("rl-quick-progress").parentElement.style.display="none";
    set("rl-quick-angle",finite(last?.angle)?fmt(last.angle,3)+"°":"N/A");
    set("rl-quick-cl",fmt(last?.CL,5));
    set("rl-quick-cd",fmt(last?.CD,6));
    set("rl-quick-pabs",finite(last?.pabs)?fmt(last.pabs/1000,2)+" kPa":"N/A");
    set("rl-quick-time",finite(last?.t)?fmt(last.t,3):fmt(meta.last_time_s,3));
    set("rl-quick-updated","Source "+timeLabel(meta.last_updated_at)+" · "+(current?"CONTROLLER ACTIVE":"LATEST ARCHIVE")+" · read only");
    $("rl-quick-open").dataset.open="live";
    $("rl-quick-open").textContent="Open CFD Live →";
    // These values describe the selected native controller history, not an
    // unrelated frozen-flow PoC, even when the controller has stopped.
    set("m-phase",last?.phase||(current?"CONTROLLER RUN":"LAST RECORDED"));
    set("m-case",s.case||title);
    set("m-case-foot",(current?"CURRENT · ":"ARCHIVED · ")+meta.label+" · "+stat);
    set("m-time",fmt(last?.t,3));
    set("m-step","Step "+fmt(last?.step,0)+" · Iteration "+fmt(last?.iteration,0));
    set("m-gate",meta.scientific_approved?"ACCEPTED":"DIAGNOSTIC");
    if(current){
      set("overall-state",displayed);
      set("overall-reason",meta.label+" · "+(last?.phase||"native CFD history")+" · "+(meta.count||0)+" measured steps");
      $("status-pulse").className="pulse-circle"+(stat==="ACTIVE"?" running":stat==="FAILED"?" failed":"");
    }
  }
}
function renderLive(){
  if(!state.snapshot)return;
  var runId=$("live-run").value,metric=$("live-metric").value,windowCount=$("live-window").value;
  var r=state.series[runId];
  var name=METRIC[metric]||[metric,metric];
  set("live-chart-title",name[0]+" · "+runId);
  var ids=[runId,...Array.from(state.liveOverlay).filter(id=>id!==runId)];
  var series=ids.map(function(id,i){
    const obj=state.series[id];
    return {name:(state.runRegistry.find(x=>x.id===id)?.label||id),
      color:registryColor(i),points:chartPoints(obj,metric,windowCount)};
  });
  plot("live-chart",series,{label:name[1],xLabel:"Native physical time, t [s]"});
  $("live-legend").innerHTML=ids.map((id,i)=>{
    const meta=state.runRegistry.find(x=>x.id===id)||{};
    return "<span class='registry-legend-item'><span class='legend-dot' style='background:"+registryColor(i)+"'></span>"+esc(meta.label||id)+
     " <small>("+esc(meta.status||"DIAGNOSTIC")+")</small></span>";
  }).join("");
  var specs=runId==="K0"?
    [["angle","δ","deg"],["angular_rate","Angular rate","deg/s"],["angle_error","Angle error","deg"],["center_error","Center error","m"],["quality","Qmin","[-]"],["orphan","Overset errors","count"]]:
    [["CL","CL","[-]"],["CD","CD","[-]"],["Fx","Fx","N"],["Fz","Fz","N"],["Mh","Mh","N·m"],["pabs","pabs,min","Pa"]];
  $("live-stats").innerHTML=specs.map(function(z){
    var st=numStats(r,z[0]);return makeMetric(z[1],st?fmt(st.mean,4):"N/A",z[2],st?"Range "+fmt(st.max-st.min,4):"Missing", "numeric");
  }).join("");
  if(r&&Object.keys(r.residuals||{}).length){
    var names=Object.keys(r.residuals),palette=[COLORS.teal,COLORS.blue,COLORS.amber,COLORS.rose,"#bb9cf2","#89caa3"];
    plot("residual-chart",names.map(function(n,i){return {name:n,color:palette[i%palette.length],points:r.residuals[n]||[]};}),{log:true,label:"Normalized residuals [-]",xLabel:"Solver iteration [-]"});
    $("residual-legend").innerHTML=names.map(function(n,i){return "<span class='legend-dot' style='background:"+palette[i%palette.length]+"'></span>"+esc(n);}).join(" ");
  }else blankChart("residual-chart","NO RESIDUAL SOURCE","Native residuals have not been integrated for this run.");
  var last=(r&&r.history.length)?r.history[r.history.length-1]:{};
  $("live-safety").innerHTML=[
    pair("Physical time",fmt(last.t,5)+" s"),
    pair("Recorded timestep",fmt(last.dt,5)+" s"),
    pair("pabs minimum",fmt(last.pabs,2)+" Pa"),
    pair("Cavitation margin",fmt(last.cav,2)+" Pa",finite(last.cav)&&last.cav>0?"pass":"warn"),
    pair("Mass imbalance",fmt(last.mass,7)),
    pair("y+ mean",fmt(last.yplus,2)),
    pair("Minimum cell quality",fmt(last.quality,4)),
    pair("Overset error cells",fmt(last.orphan,0),last.orphan===0?"pass":"warn"),
    pair("Flow solve / K0",runId==="K0"?"NO · frozen flow":"Solver history",runId==="K0"?"warn":""),
    pair("Window drift CL",numStats(r,"CL")?pct(numStats(r,"CL").drift_pct):"N/A")
  ].join("");
  var sr=numStats(r,runId==="K0"?"angle":"CL");
  set("live-source",r?"Source: "+r.source+" · last 25 valid samples, t="+fmt(sr&&sr.from_s,3)+"–"+fmt(sr&&sr.to_s,3)+" s"+(runId==="K0"?" · NO FLOW SOLVE":""):"Run source missing");
}
function renderValidation(){
  if(!state.snapshot)return;
  var v=state.snapshot.validation||{},b=state.series.B0,c=state.series.C0;
  var clb=numStats(b,"CL"),clc=numStats(c,"CL"),cdb=numStats(b,"CD"),cdc=numStats(c,"CD");
  $("validation-kpis").innerHTML=makeMetric("ΔCL · C0 VS B0",pct(v.delta_CL_pct),"[-]","Last 25 samples","numeric")+
    makeMetric("ΔCD · C0 VS B0",pct(v.delta_CD_pct),"[-]","Last 25 samples","numeric")+
    makeMetric("B0 WINDOW",(clb?fmt(clb.from_s,3)+"–"+fmt(clb.to_s,3):"N/A"),"s",clb?clb.n+" samples":"No source","sm")+
    makeMetric("C0 WINDOW",(clc?fmt(clc.from_s,3)+"–"+fmt(clc.to_s,3):"N/A"),"s",clc?clc.n+" samples":"No source","sm");
  ["CL","CD"].forEach(function(metric){
    plot("validation-"+metric.toLowerCase(),[
      {name:"B0",color:COLORS.blue,points:chartPoints(b,metric,"all")},
      {name:"C0",color:COLORS.teal,points:chartPoints(c,metric,"all")}],
      {label:metric+" [-]"});
  });
  var rowSpecs=[["Lift coefficient","CL","[-]"],["Drag coefficient","CD","[-]"],
       ["Drag force","Fx","N"],["Lift force","Fz","N"],["Hinge moment","Mh","N·m"]];
  $("validation-table").innerHTML=rowSpecs.map(function(row){
    var sb=numStats(b,row[1]),sc=numStats(c,row[1]);
    var a=sb&&sb.mean,z=sc&&sc.mean;
    var delta=finite(a)&&a!==0&&finite(z)?(z/a-1)*100:null;
    return "<tr><td>"+esc(row[0])+"</td><td>"+fmt(a,6)+"</td><td>"+fmt(z,6)+"</td><td>"+pct(delta)+"</td><td>"+esc(row[2])+"</td></tr>";
  }).join("");
  $("validation-provenance").textContent="B0: "+(v.B_source||"—")+" | C0: "+(v.C_source||"—")+
     " | Window: 25 last valid CSV samples, not matched physical times. All results DIAGNOSTIC.";
  $("validation-quality").innerHTML=[
    pair("B0 | CL range / mean",clb?pct(clb.range_pct):"N/A"),
    pair("C0 | CL range / mean",clc?pct(clc.range_pct):"N/A"),
    pair("B0 | CL window drift",clb?pct(clb.drift_pct):"N/A"),
    pair("C0 | CL window drift",clc?pct(clc.drift_pct):"N/A"),
    pair("B0 | CD range / mean",cdb?pct(cdb.range_pct):"N/A"),
    pair("C0 | CD range / mean",cdc?pct(cdc.range_pct):"N/A"),
    pair("Technical force screen",Math.max(Math.abs(v.delta_CL_pct||99),Math.abs(v.delta_CD_pct||99))<1?"<1% PASS (technical)":"NOT PASSED",Math.max(Math.abs(v.delta_CL_pct||99),Math.abs(v.delta_CD_pct||99))<1?"pass":"warn"),
    pair("Scientific qualification",v.scientific_approved?"ACCEPTED":"NOT APPROVED","warn")
  ].join("");
}
function imageFor(match){var imgs=state.snapshot&&state.snapshot.images||[];return imgs.find(function(x){return x.name===match;});}
function renderMesh(){
  var s=state.snapshot;if(!s)return;
  var m=s.mesh||{},bg=m.regions&&m.regions.Background||{},ov=m.regions&&m.regions.FlapOverset||{};
  var total=finite(bg.cells)&&finite(ov.cells)?bg.cells+ov.cells:null;
  $("mesh-metrics").innerHTML=makeMetric("C0 CELLS",fmt(total,0),"cells","Corrected cage","numeric")+
    makeMetric("ACCEPTORS",fmt((bg.acceptors||0)+(ov.acceptors||0),0),"cells","Both regions","numeric")+
    makeMetric("ERROR CELLS",fmt((bg.error_cells||0)+(ov.error_cells||0),0),"cells","Must equal zero","numeric")+
    makeMetric("MIN QUALITY",fmt(Math.min(bg.min_quality||1,ov.min_quality||1),4),"[-]","Mesh guard","numeric");
  var preferred=[
    "C0_interface_before_after_tight_cage.png","C0_overset_resolution_diagnostic.png",
    "C0_overlap_mesh_c0_overlap_distance_audit_20261103_002542.png",
    "C0_overlap_mesh_c0_overlap_band05mm_20261103_003837.png",
    "BC_nearwall_resolution.png","C0_night_diagnostics.png"
  ];
  var imgs=preferred.map(imageFor).filter(Boolean);
  $("mesh-images").innerHTML=imgs.length?imgs.map(function(img){
    return "<figure class='figure'><div class='panel-kicker'>STAR-CCM+ EXPORT</div><img loading='lazy' src='"+esc(img.url)+"' alt='"+esc(img.name)+"'><figcaption>"+esc(img.name.replace(/_/g," ").replace(".png",""))+"</figcaption></figure>";
  }).join(""):"<div class='no-data'>No actual mesh images found in permitted folders.</div>";
  var ratio=ov.acceptor_size_ratio_quantiles||{};
  $("mesh-guards").innerHTML=[
    pair("Background original / corrected",fmt(m.background&&m.background.control_cells,0)+" / "+fmt(m.background&&m.background.candidate_cells,0)),
    pair("Background coordinate identity",m.background&&m.background.identity_pass?"PASSED":"NOT CONFIRMED",m.background&&m.background.identity_pass?"pass":"warn"),
    pair("Background active cells",fmt(bg.active,0)),
    pair("Overset active cells",fmt(ov.active,0)),
    pair("Orphan / error cells",fmt((bg.error_cells||0)+(ov.error_cells||0),0)),
    pair("Difficult stencils",fmt((bg.difficult_cells||0)+(ov.difficult_cells||0),0)),
    pair("Max acceptor size ratio",fmt(ratio["1.0"],4)),
    pair("Error screen",m&&total?"TECHNICAL ONLY":"NO DATA","warn")
  ].join("");
}
function renderWaves(){
  var s=state.snapshot;if(!s)return;
  var waves=s.waves||[];
  $("wave-cases").innerHTML=waves.length?waves.map(function(w){
    return "<div class='case-row'><strong>"+esc(w.id)+"</strong><span class='tag subtle'>"+esc(String(w.status).slice(0,22))+"</span><small title='"+esc(w.source)+"'>"+esc(w.details||tailPath(w.source))+"</small></div>";
  }).join(""):"<div class='no-data'>No independently verified wave campaign records accessible.</div>";
  var runId=$("wave-run").value;
  var w=state.series[runId];
  var best=(w&&w.history||[]).some(function(r){return finite(r.CL)&&finite(r.t);})?"CL":"Fx";
  plot("wave-chart",[{name:runId,color:COLORS.teal,points:chartPoints(w,best,"all")}],{label:best+" · "+runId,xLabel:"Physical time [s]"});
  var gauges=(w&&w.gauges)||[];
  plot("wave-gauge-chart",[{name:"VOF η(x=-0.5m)",color:COLORS.blue,points:gauges}],{label:"η(x = -0.5 m) [m]",xLabel:"Physical time [s]"});
  set("wave-source",w?"Source: "+w.source+" · "+w.category+" · not a quantitative added-resistance validation":"No external history found.");
  set("wave-gauge-source",gauges.length?("Source: "+w.source.replace("history.csv","gauges.csv")+" · "+gauges.length+" samples · no analytical wave overlaid"):"No time-resolved foil probe found for this run.");
}
function renderFlap(){
  var s=state.snapshot;if(!s)return;var g=s.geometry||{};
  $("flap-geometry").innerHTML=makeMetric("NOMINAL CHORD",fmt(g.nominal_chord_m,3),"m","Native profile geometry","numeric")+
    makeMetric("HINGE LOCATION",fmt(g.hinge_fraction*100,1),"% c","x="+fmt(g.hinge_x_m,4)+" m","numeric")+
    makeMetric("HINGE GAP",fmt(g.gap_m*1e3,2),"mm","Minimum clearance "+fmt(g.min_clearance_m*1e3,2)+" mm","numeric")+
    makeMetric("QUASI-2D SPAN",fmt(g.span_m*1000,0),"mm","Reference model","numeric");
  $("flap-details").innerHTML=[
    pair("Profile",g.native_source||"N/A"),
    pair("Hinge axis",Array.isArray(g.hinge_axis)?g.hinge_axis.join(", "):"N/A"),
    pair("Hinge x",fmt(g.hinge_x_m,6)+" m"),
    pair("Hinge z",fmt(g.hinge_z_m,6)+" m"),
    pair("Native profile points",fmt(g.native_profile_points,0)),
    pair("Test angle increment",fmt(g.tested_angle_step_deg,2)+"°"),
    pair("Current δ | B0",fmt(state.series.B0&&state.series.B0.history.at(-1)&&state.series.B0.history.at(-1).angle,2)+"°"),
    pair("Current angular speed",fmt(state.series.B0&&state.series.B0.history.at(-1)&&state.series.B0.history.at(-1).angular_rate,2)+"°/s")
  ].join("");
  set("flap-source","Source: "+(g.folder||"—")+" / current_geometry.json");
  var k=state.series.K0, info=s.kinematic||{},last=info.motion_last||{},kstatus=s.kinematic_passed?"KINEMATIC PASS":"DIAGNOSTIC";
  set("flap-kinematic-status",kstatus);
  $("kinematic-metrics").innerHTML=
    makeMetric("RECORDED STEPS",fmt(info.steps,0),"steps","Frozen-flow PoC","numeric")+
    makeMetric("ANGLE SPAN",k&&k.history.length?fmt(Math.min.apply(null,k.history.map(function(x){return x.angle;})),2)+"° / "+fmt(Math.max.apply(null,k.history.map(function(x){return x.angle;})),2)+"°":"N/A","deg","Actual motion range","sm")+
    makeMetric("ANGLE ERROR",numStats(k,"angle_error")?fmt(Math.max.apply(null,k.history.map(function(x){return Math.abs(x.angle_error||0);}).filter(finite)),9)+"°":"N/A","deg","Maximum absolute error","numeric")+
    makeMetric("OVERSET ERRORS",fmt(last.orphan,0),"cells",info.hydrodynamics_solved===false?"Flow explicitly frozen":"Not a force solve","numeric");
  plot("kinematic-chart",[{name:"Prescribed δ(t)",color:COLORS.teal,points:chartPoints(k,"angle","all")}],{label:"δ [deg]"});
  set("kinematic-source","Source: "+info.source+" · "+(info.status||"NO STATUS")+" · Hydrodynamics solved: "+(info.hydrodynamics_solved===false?"NO":"NOT VERIFIED"));
  var img=imageFor("flap_native_geometry_range.png")||imageFor("geometry_native_gap25mm.png");
  $("flap-image").innerHTML=img?"<img src='"+esc(img.url)+"' alt='STAR native flap geometry'>":"<div class='no-data'>Native geometry image not found.</div>";
}
function renderHardware(){
  var s=state.snapshot;if(!s)return;var h=s.hardware||{};
  $("hardware-metrics").innerHTML=makeMetric("CPU LOAD",finite(h.cpu_percent)?fmt(h.cpu_percent,1)+"%":"N/A","system","Native Windows counter","numeric")+
    makeMetric("CPU FREQUENCY",finite(h.cpu_nominal_MHz)?fmt(h.cpu_nominal_MHz/1000,2):"N/A","GHz","Nominal hardware clock","numeric")+
    makeMetric("RAM IN USE",fmt(h.ram_used_GB,1)+" / "+fmt(h.ram_total_GB,1),"GB","Physical system memory","numeric")+
    makeMetric("GPU LOAD",finite(h.gpu_percent)?fmt(h.gpu_percent,0)+"%":"N/A","NVIDIA","nvidia-smi utilization","numeric")+
    makeMetric("GPU VRAM",finite(h.vram_used_MB)?fmt(h.vram_used_MB/1024,2)+" / "+fmt(h.vram_total_MB/1024,2):"N/A","GiB","Reported by nvidia-smi","numeric")+
    makeMetric("GPU TEMP",finite(h.gpu_temperature_C)?fmt(h.gpu_temperature_C,0)+"°C":"N/A","sensor","Throttling status unavailable","numeric")+
    makeMetric("STAR PROCESSES",fmt((h.star_processes||[]).length,0),"count","Observed processes","numeric")+
    makeMetric("CPU TEMP",finite(h.cpu_temperature_C)?fmt(h.cpu_temperature_C,0)+"°C":"N/A","sensor","No reliable sensor","numeric");
  $("disk-health").innerHTML=(h.disk||[]).map(function(d){
    var used=100*(1-d.free_GB/d.total_GB);
    return "<div class='progress-row'><div><span>"+esc(d.name)+" · "+fmt(d.free_GB,1)+" GB free</span><b>"+fmt(used,1)+"% used</b></div><div class='progress-track'><div class='progress-inner' style='width:"+Math.max(0,Math.min(100,used))+"%'></div></div></div>";
  }).join("")||"<div class='no-data'>Disk counters unavailable.</div>";
  var items=h.star_processes||[];
  $("hardware-procs").innerHTML=pair("STAR processes",fmt(items.length,0))+
       pair("MPI launchers",finite(h.mpi_ranks)?fmt(h.mpi_ranks,0):"N/A")+
       pair("CPU temperature","N/A · no verified sensor","warn")+
       pair("Thermal / power limiting","N/A · no verified sensor","warn")+
       items.map(function(p){return pair("STAR PID "+p.pid,p.name);}).join("");
  var history=state.hardwareHistory.filter(function(x){return finite(x.used)&&finite(x.total);});
  plot("hardware-chart",[{name:"RAM utilisation",color:COLORS.teal,points:history.map(function(p){return {x:p.t-history[0].t,y:p.used/p.total*100};})}],{label:"RAM in use [%]",xLabel:"Elapsed monitoring time [s]"});
}
async function loadHistory(){
  try{state.history=await fetchJSON("/api/history");if(state.current==="history")renderHistory();}
  catch(e){if(state.current==="history")$("history-reviews").innerHTML="<div class='no-data'>History endpoint unavailable.</div>";}
}
function renderHistory(){
  var h=state.history;if(!h)return;
  var reviews=h.reviews||[],decisions=h.decisions||[];
  set("history-count",reviews.length+" RECORDS");
  $("history-reviews").innerHTML=reviews.map(function(r){
    return "<div class='history-entry'><div class='entry-top'><strong>"+esc(r.id)+"</strong><time>"+esc(timeLabel(r.at))+"</time></div>"+
       "<span class='tag "+(r.scientific_approved?"teal":"amber")+"'>"+esc(r.status)+"</span>"+
       "<p>CL "+fmt(r.CL,6)+" · CD "+fmt(r.CD,6)+" · Mh "+fmt(r.Mh,3)+" N·m</p>"+
       "<small>"+esc(tailPath(r.run||r.source))+"</small></div>";
  }).join("")||"<div class='no-data'>No historical reviews.</div>";
  $("history-decisions").innerHTML=decisions.map(function(r){
    return "<div class='history-entry'><div class='entry-top'><strong>"+esc(r.case||"Controller decision")+"</strong><time>"+esc(timeLabel(r.at))+"</time></div>"+
       "<p>"+esc(r.decision||"Source contains no summary field.")+"</p><small>"+esc(tailPath(r.source))+"</small></div>";
  }).join("")||"<div class='no-data'>No scientific decisions could be parsed.</div>";
}
function renderCurrent(){
  if(!state.snapshot)return;
  ({overview:renderOverview,live:renderLive,validation:renderValidation,mesh:renderMesh,waves:renderWaves,
    flap:renderFlap,hardware:renderHardware,history:renderHistory})[state.current]?.();
}
function renderAll(){
  renderOverview();
  renderLive();
  renderValidation();
  renderDynamicValidation();
  renderMesh();
  renderWaves();
  renderFlap();
  renderHardware();
  renderCurrent();
}
async function sync(force){
  if(state.syncing)return;
  state.syncing=true;set("connection-label","SYNCING");
  try{
    var results=await Promise.all([
      fetchJSON("/api/snapshot"),
      fetchJSON("/api/series?id=B0"),
      fetchJSON("/api/series?id=C0"),
      fetchJSON("/api/series?id=K0"),
      fetchJSON("/api/series?id=A0"),
      fetchJSON("/api/series?id=W02"),
      fetchJSON("/api/series?id=W03"),
      fetchJSON("/api/series?id=W04pre"),
      fetchJSON("/api/runs")
    ]);
    state.snapshot=results[0];["B0","C0","K0","A0","W02","W03","W04pre"].forEach(function(id,i){state.series[id]=results[i+1];});
    state.runRegistry=results[8].runs||[];
    state.activeRunId=results[8].active_run_id||null;
    populateRegistryControls();
    await refreshSelectedDynamicSeries();
    var h=state.snapshot.hardware||{};
    state.hardwareHistory.push({t:Date.now()/1000,used:h.ram_used_GB,total:h.ram_total_GB});
    if(state.hardwareHistory.length>90)state.hardwareHistory.shift();
    $("connection-dot").style.background=COLORS.teal;set("connection-label","CONNECTED · 15 S");renderAll();
  }catch(err){
    $("connection-dot").style.background=COLORS.rose;set("connection-label","OFFLINE");
    if(!state.snapshot){set("overall-state","OFFLINE");set("overall-reason","Cannot read local dashboard server. Check startup and local connection.");}
    if(force)toast("Refresh failed: "+err.message);
  }finally{state.syncing=false;}
}
function init(){
  initNavigation();sync(false);
  setInterval(function(){sync(false);},15000);
  setInterval(function(){set("local-clock",new Date().toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"}));},1000);
  set("local-clock",new Date().toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"}));
}
document.addEventListener("DOMContentLoaded",init);
})();

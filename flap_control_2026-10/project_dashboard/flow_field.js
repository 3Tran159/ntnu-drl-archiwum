/* NTNU Science · native flow field viewer. Source: read-only server /api/flow/*. */
(function(){
"use strict";
const $=id=>document.getElementById(id);
const num=v=>typeof v==="number"&&Number.isFinite(v);
const fmt=(x,p=3)=>num(x)?x.toLocaleString("en-US",{maximumFractionDigits:p}):"N/A";
const escapeHTML=s=>String(s??"").replace(/[&<>"']/g,x=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
const vals={u:3,w:4,speed:5,pabs:6,gauge:7,k:8,omega:9,mu:10,quality:11,volume:12};
const scOptions={
 speed:{label:"Velocity magnitude",unit:"m/s",scale:1},
 pabs:{label:"Absolute pressure",unit:"kPa",scale:.001},
 gauge:{label:"STAR Pressure",unit:"kPa",scale:.001},
 vorticity:{label:"Approx. out-of-plane vorticity",unit:"1/s",scale:1},
 k:{label:"Turbulent kinetic energy k",unit:"J/kg",scale:1},
 omega:{label:"Specific dissipation rate ω",unit:"1/s",scale:1},
 mu:{label:"Turbulent viscosity ratio",unit:"[-]",scale:1},
 quality:{label:"Cell quality",unit:"[-]",scale:1},
};
const G={manifest:null, mode:"live",field:"speed",region:"foil",frameId:null,compareId:null,
 frames:new Map(),gridCache:new Map(),loading:new Map(),zoom:1,panX:0,panY:0,
 contours:true,streamlines:true,vectors:false,samples:false,walls:true,density:14,playing:false,timer:null,
 hovered:null,version:null,loadedAt:0,compareLocked:true};
const RAMP_THRESHOLD=12.339;
const palette=[[0.10,0.13,0.28],[0.10,0.30,0.56],[0.10,0.58,0.57],[0.42,0.75,0.36],[0.94,0.82,0.25],[0.92,0.37,0.19]];
function color(t,diverge){
 t=Math.max(0,Math.min(1,t));
 if(diverge){
  const stops=[[0.13,0.44,0.72],[0.47,0.73,0.84],[0.91,0.92,0.89],[0.94,0.66,0.37],[0.74,0.22,0.28]];
  return mixPalette(stops,t);
 }
 return mixPalette(palette,t);
}
function mixPalette(stops,t){
 const i=Math.min(stops.length-2,Math.floor(t*(stops.length-1)));
 const f=t*(stops.length-1)-i;
 return stops[i].map((a,k)=>Math.round(255*(a*(1-f)+stops[i+1][k]*f)));
}
function frameByID(id){return G.manifest?.frames?.find(f=>f.id===id)||null;}
function sortedFrames(){return G.manifest?.frames||[];}
function latest(field=G.field){
 const all=sortedFrames();
 const compatible=all.filter(f=>field==="quality"|| (field==="vorticity"||field==="speed"?f.has_velocity:
   field==="pabs"||field==="gauge"?f.has_pressure:f.has_turbulence));
 return compatible.length?compatible[compatible.length-1]:all[all.length-1]||null;
}
function set(id,value){if($(id))$(id).textContent=value==null?"—":String(value);}
function setMode(mode){
 G.mode=mode;
 document.querySelectorAll("[data-flow-mode]").forEach(el=>el.classList.toggle("selected",el.dataset.flowMode===mode));
 if(mode==="live"){
  const f=latest();if(f)G.frameId=f.id;
 }
 refreshCurrent();
}
function sourceLabel(f){
 if(!f)return "NO NATIVE FILE";
 return "t = "+fmt(f.time_s,4)+" s · "+(f.kind==="flow"?"FULL FIELD":"MESH ONLY")+" · "+f.stage.toUpperCase();
}
function arraysFor(frame){
 if(!frame)return null;
 const key=frame.frame_id+"::"+frame.region;
 if(G.gridCache.has(key))return G.gridCache.get(key);
 const count=frame.nx*frame.ny;
 const cells=new Array(count).fill(null);
 const background=frame.layers?.find(x=>x.name==="Background")||{};
 const overset=frame.layers?.find(x=>x.name==="FlapOverset")||{};
 const assign=(src,name,replace)=>{
  for(const cell of src.cells||[]){
   const i=cell[0],j=cell[1];
   if(!Number.isInteger(i)||!Number.isInteger(j)||i<0||j<0||i>=frame.nx||j>=frame.ny)continue;
   const at=j*frame.nx+i;
   if(!replace&&cells[at])continue;
   cells[at]={i,j,count:cell[2],vars:cell,region:name};
  }
 };
 assign(background,"Background",false);
 // Only active fluid cell status=0 enters these arrays. Overset overrides at its own
 // valid bins; donor and acceptor statuses are not blended or treated as physical fields.
 assign(overset,"FlapOverset",true);
 const result={cells,nx:frame.nx,ny:frame.ny,bounds:frame.bounds,frame};
 result.wallShapes=(frame.walls||[]).map(wall=>envelope(wall,frame.bounds)).filter(Boolean);
 G.gridCache.set(key,result);
 if(G.gridCache.size>15)G.gridCache.delete(G.gridCache.keys().next().value);
 return result;
}
function dataAt(grid,i,j,key){
 if(!grid||i<0||j<0||i>=grid.nx||j>=grid.ny)return null;
 const cell=grid.cells[j*grid.nx+i];
 if(!cell)return null;
 const slot=vals[key];
 const value=cell.vars[slot];
 return num(value)?value:null;
}
function sameRegion(grid,i,j,region){
 if(i<0||j<0||i>=grid.nx||j>=grid.ny)return false;
 return grid.cells[j*grid.nx+i]?.region===region;
}
function vorticityAt(grid,i,j){
 // ω_y = ∂u_x/∂z - ∂u_z/∂x in (x,z) plane.
 const self=grid.cells[j*grid.nx+i];if(!self)return null;
 const bg=self.region,dx=(grid.bounds.x1-grid.bounds.x0)/grid.nx,
   dz=(grid.bounds.z1-grid.bounds.z0)/grid.ny;
 if(![[i-1,j],[i+1,j],[i,j-1],[i,j+1]].every(p=>sameRegion(grid,...p,bg)))return null;
 const uUp=dataAt(grid,i,j+1,"u"),uDn=dataAt(grid,i,j-1,"u"),
       wR=dataAt(grid,i+1,j,"w"),wL=dataAt(grid,i-1,j,"w");
 if([uUp,uDn,wR,wL].some(v=>!num(v)))return null;
 return (uUp-uDn)/(2*dz)-(wR-wL)/(2*dx);
}
function cellScalar(grid,cell,field){
 if(!cell)return null;
 if(field==="vorticity")return vorticityAt(grid,cell.i,cell.j);
 const v=cell.vars[vals[field]];
 return num(v)?v*(scOptions[field]?.scale||1):null;
}
function readRange(grid,field){
 if(!grid)return null;
 const data=[];
 for(const cell of grid.cells){
  const v=cellScalar(grid,cell,field);
  if(num(v))data.push(v);
 }
 if(!data.length)return null;
 data.sort((a,b)=>a-b);
 const ix=i=>data[Math.max(0,Math.min(data.length-1,Math.floor(i*(data.length-1))))];
 // Explicit percentile clipping of the display, not modification of source values.
 let min=ix(.02),max=ix(.98);
 if(max-min<1e-13){const e=Math.max(Math.abs(min)*.02,1e-5);min-=e;max+=e;}
 return {min,max,rawMin:data[0],rawMax:data[data.length-1],
         n:data.length,clipped:true};
}
function baseRaster(grid,field,range,contours){
 const c=document.createElement("canvas");c.width=grid.nx;c.height=grid.ny;
 const ctx=c.getContext("2d",{alpha:true});const pixels=ctx.createImageData(grid.nx,grid.ny);
 for(const cell of grid.cells){
  if(!cell)continue;
  const value=cellScalar(grid,cell,field);
  if(!num(value))continue;
  const t=(value-range.min)/(range.max-range.min);
  const rgb=color(t,field==="vorticity");
  const pos=4*((grid.ny-1-cell.j)*grid.nx+cell.i);
  pixels.data[pos]=rgb[0];pixels.data[pos+1]=rgb[1];pixels.data[pos+2]=rgb[2];pixels.data[pos+3]=contours?245:0;
 }
 ctx.putImageData(pixels,0,0);
 return c;
}
function worldMapping(grid,w,h,zoom=1,panX=0,panY=0){
 const b=grid.bounds;const cx=(b.x0+b.x1)/2,cz=(b.z0+b.z1)/2;
 const base=Math.min((w-36)/(b.x1-b.x0),(h-40)/(b.z1-b.z0));
 const scale=base*zoom;
 return {
  x:x=>w/2+(x-cx)*scale+panX,
  z:z=>h/2-(z-cz)*scale+panY,
  fromX:px=>cx+(px-w/2-panX)/scale,
  fromZ:py=>cz-(py-h/2-panY)/scale,
  scale};
}
function envelope(samples,b){
 const points=samples?.points||[];
 if(points.length<30)return null;
 const dx=Math.max(.0012,(b.x1-b.x0)/650);
 const buckets=new Map();
 for(const [x,z] of points){
  const idx=Math.round(x/dx);
  const a=buckets.get(idx)||{x:idx*dx,lo:Infinity,hi:-Infinity};
  a.lo=Math.min(a.lo,z);a.hi=Math.max(a.hi,z);buckets.set(idx,a);
 }
 const rows=[...buckets.values()].sort((a,b)=>a.x-b.x);
 return rows.length>=12?rows:null;
}
function paintWalls(ctx,grid,mapping){
 // Actual native wall samples, not a stitched or fabricated polygon.
 for(const wall of grid.frame.walls||[]){
  ctx.fillStyle=wall.part==="Flap"?"rgba(247,192,128,.96)":"rgba(232,242,247,.94)";
  for(const [x,z] of wall.points||[]){
   ctx.fillRect(mapping.x(x)-.8,mapping.z(z)-.8,1.6,1.6);
  }
 }
}
function isSolid(grid,x,z){
 // A streamline is accepted only on four native active-fluid display bins
 // of the same region, so empty/solid space has no vector path.
 const b=grid.bounds;
 const i=Math.floor((x-b.x0)/(b.x1-b.x0)*grid.nx);
 const j=Math.floor((z-b.z0)/(b.z1-b.z0)*grid.ny);
 return i<0||j<0||i>=grid.nx||j>=grid.ny||!grid.cells[j*grid.nx+i];
}
function fluidVector(grid,x,z){
 const b=grid.bounds,ii=(x-b.x0)/(b.x1-b.x0)*grid.nx-.5,
 jj=(z-b.z0)/(b.z1-b.z0)*grid.ny-.5;
 const i=Math.floor(ii),j=Math.floor(jj),fx=ii-i,fz=jj-j;
 const a=[[i,j],[i+1,j],[i,j+1],[i+1,j+1]];
 const row=a.map(([x,y])=>x>=0&&y>=0&&x<grid.nx&&y<grid.ny?grid.cells[y*grid.nx+x]:null);
 if(row.some(r=>!r)||new Set(row.map(r=>r.region)).size!==1||isSolid(grid,x,z))return null;
 const bilerp=k=>{
  const vs=row.map(r=>r.vars[vals[k]]);
  if(vs.some(v=>!num(v)))return null;
  return vs[0]*(1-fx)*(1-fz)+vs[1]*fx*(1-fz)+vs[2]*(1-fx)*fz+vs[3]*fx*fz;
 };
 const u=bilerp("u"),w=bilerp("w");
 return num(u)&&num(w)?{u,w}:null;
}

function streamlines(ctx,grid,mapping,density=14){
 const b=grid.bounds,dx=(b.x1-b.x0)/grid.nx,dz=(b.z1-b.z0)/grid.ny;
 const step=Math.min(dx,dz)*1.2,maxSteps=340;
 let drawn=0;
 const xStart=b.x0+.13*(b.x1-b.x0);
 for(let n=0;n<density;n++){
  const startZ=b.z0+(n+0.5)/density*(b.z1-b.z0);
  let x=xStart,z=startZ,points=[];
  for(let stepNo=0;stepNo<maxSteps;stepNo++){
   const a=fluidVector(grid,x,z);
   if(!a)break;
   const m=Math.hypot(a.u,a.w);
   if(m<.04)break;
   points.push([x,z]);
   x+=step*a.u/m;z+=step*a.w/m;
   if(x>=b.x1||x<b.x0||z<b.z0||z>b.z1)break;
  }
  if(points.length<4)continue;
  ctx.beginPath();points.forEach((p,i)=>{
   const xx=mapping.x(p[0]),zz=mapping.z(p[1]);
   if(!i)ctx.moveTo(xx,zz);else ctx.lineTo(xx,zz);
  });
  ctx.strokeStyle="rgba(247,250,254,.76)";ctx.lineWidth=1.05;
  ctx.lineCap="round";ctx.stroke();drawn++;
  // Draw a small arrowhead near the last recorded vector direction.
  const nPoints=points.length,j=Math.floor(nPoints*.65);
  if(j>0&&j<nPoints){
   const [x0,z0]=points[j-1],[x1,z1]=points[j];
   const angle=Math.atan2(mapping.z(z1)-mapping.z(z0),mapping.x(x1)-mapping.x(x0));
   ctx.save();ctx.translate(mapping.x(x1),mapping.z(z1));ctx.rotate(angle);
   ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(-5,-2.5);ctx.lineTo(-5,2.5);ctx.closePath();
   ctx.fillStyle="rgba(249,252,255,.9)";ctx.fill();ctx.restore();
  }
 }
 return drawn;
}
function drawBinSamples(ctx,grid,mapping){
 for(let p=0;p<grid.cells.length;p++){
  const item=grid.cells[p];
  if(!item)continue;
  const x=grid.bounds.x0+(item.i+.5)*(grid.bounds.x1-grid.bounds.x0)/grid.nx;
  const z=grid.bounds.z0+(item.j+.5)*(grid.bounds.z1-grid.bounds.z0)/grid.ny;
  ctx.fillStyle=item.region==="FlapOverset"?"rgba(252,178,88,.63)":"rgba(136,194,252,.36)";
  ctx.fillRect(mapping.x(x)-.7,mapping.z(z)-.7,1.4,1.4);
 }
}
function drawVectorGlyphs(ctx,grid,mapping,density=14){
 const dx=(grid.bounds.x1-grid.bounds.x0)/grid.nx,
       dz=(grid.bounds.z1-grid.bounds.z0)/grid.ny;
 const strideX=Math.max(6,Math.round(grid.nx/(density*1.8)));
 const strideZ=Math.max(6,Math.round(grid.ny/density));
 let count=0;
 for(let j=4;j<grid.ny;j+=strideZ){
  for(let i=4;i<grid.nx;i+=strideX){
   const sample=grid.cells[j*grid.nx+i];if(!sample)continue;
   const u=sample.vars[vals.u],w=sample.vars[vals.w];
   if(!num(u)||!num(w))continue;
   const n=Math.hypot(u,w);if(n<.05)continue;
   const x=grid.bounds.x0+(i+.5)*dx,z=grid.bounds.z0+(j+.5)*dz;
   const px=mapping.x(x),pz=mapping.z(z);
   const vx=9*u/n,vz=-9*w/n;
   ctx.beginPath();ctx.moveTo(px-3*vx/9,pz-3*vz/9);ctx.lineTo(px+vx,pz+vz);
   ctx.strokeStyle="rgba(239,249,253,.7)";ctx.lineWidth=1;ctx.stroke();
   ctx.beginPath();ctx.moveTo(px+vx,pz+vz);
   ctx.lineTo(px+vx-3*(vx+.4*vz)/9,pz+vz-3*(vz-.4*vx)/9);
   ctx.lineTo(px+vx-3*(vx-.4*vz)/9,pz+vz-3*(vz+.4*vx)/9);
   ctx.closePath();ctx.fillStyle="rgba(239,249,253,.72)";ctx.fill();
   count++;
  }
 }
 return count;
}
function pressurePointsFor(frame){
 if(!G.manifest?.pressure_zones?.points||!frame)return [];
 return G.manifest.pressure_zones.points.filter(p=>Math.abs(p.t-frame.time_s)<.0000001);
}
function drawPressureMarker(ctx,frame,mapping){
 const matches=pressurePointsFor(frame).filter(x=>x.zone==="liquid_all");
 if(!matches.length)return;
 const min=matches.reduce((a,b)=>a.pabs<=b.pabs?a:b);
 const x=mapping.x(min.x),z=mapping.z(min.z);
 ctx.beginPath();ctx.arc(x,z,5,0,2*Math.PI);
 ctx.strokeStyle="#ff9d83";ctx.lineWidth=2;ctx.stroke();
 ctx.beginPath();ctx.moveTo(x-10,z);ctx.lineTo(x+10,z);ctx.moveTo(x,z-10);ctx.lineTo(x,z+10);
 ctx.strokeStyle="#ff9d83";ctx.lineWidth=1;ctx.stroke();
}
function getRaster(grid,field,range){
 const key=grid.frame.frame_id+"::"+grid.frame.region+"::"+field+"::"+range.min+"::"+range.max;
 G.rasterCache ||= new Map();
 if(G.rasterCache.has(key))return G.rasterCache.get(key);
 const raster=baseRaster(grid,field,range,true);
 if(G.rasterCache.size>12)G.rasterCache.delete(G.rasterCache.keys().next().value);
 G.rasterCache.set(key,raster);
 return raster;
}
function drawNative(frameData,canvas,scalar,options={}){
 if(!canvas||!frameData)return null;
 const grid=arraysFor(frameData);
 const bounding=canvas.getBoundingClientRect();
 const cssWidth=options.width||Math.round(bounding.width);
 const cssHeight=options.height||Math.round(bounding.height);
 if(cssWidth<10||cssHeight<10)return null;
 const dpi=options.dpi||Math.min(2,window.devicePixelRatio||1);
 canvas.width=Math.round(cssWidth*dpi);canvas.height=Math.round(cssHeight*dpi);
 const ctx=canvas.getContext("2d",{alpha:false});
 ctx.setTransform(dpi,0,0,dpi,0,0);ctx.clearRect(0,0,cssWidth,cssHeight);
 ctx.fillStyle="#081522";ctx.fillRect(0,0,cssWidth,cssHeight);
 const mapping=worldMapping(grid,cssWidth,cssHeight,options.zoom||1,options.panX||0,options.panY||0);
 const available=readRange(grid,scalar);
 const display=options.sharedRange||available;
 if(available&&display&&options.contours!==false){
  const raster=getRaster(grid,scalar,display);
  const b=grid.bounds;
  ctx.imageSmoothingEnabled=false;
  ctx.drawImage(raster,mapping.x(b.x0),mapping.z(b.z1),
    (b.x1-b.x0)*mapping.scale,(b.z1-b.z0)*mapping.scale);
 }
 if((options.samples||false)&&grid.cells.length)drawBinSamples(ctx,grid,mapping);
 const nVectors=options.vectors&&frameData.has_velocity?drawVectorGlyphs(ctx,grid,mapping,options.density||14):0;
 let nStream=0;
 if(options.streamlines&&frameData.has_velocity&&["speed","pabs","gauge","k","omega","mu","vorticity","quality"].includes(scalar)){
  nStream=streamlines(ctx,grid,mapping,options.density||14);
 }
 if(options.walls)paintWalls(ctx,grid,mapping);
 drawPressureMarker(ctx,frameData,mapping);
 // Physical coordinate rulers from actual field export axes.
 ctx.font="11px Consolas,monospace";ctx.fillStyle="#b4ccda";
 ctx.fillText("x [m]",8,14);ctx.fillText("z [m]",8,27);
 ctx.fillStyle="rgba(215,226,239,.72)";
 ctx.fillText("X "+fmt(grid.bounds.x0,2)+" … "+fmt(grid.bounds.x1,2),8,cssHeight-12);
 return {grid,mapping,range:display,available,streamlines:nStream,vectors:nVectors};
}
function selectCell(data,result,px,py){
 const grid=result?.grid,map=result?.mapping;
 if(!grid||!map)return null;
 const x=map.fromX(px),z=map.fromZ(py),b=grid.bounds;
 if(x<b.x0||x>=b.x1||z<b.z0||z>=b.z1)return null;
 const i=Math.floor((x-b.x0)/(b.x1-b.x0)*grid.nx);
 const j=Math.floor((z-b.z0)/(b.z1-b.z0)*grid.ny);
 const cell=grid.cells[j*grid.nx+i];
 if(!cell)return {x,z,missing:true};
 return {x,z,cell,value:cellScalar(grid,cell,G.field),source:data};
}
function updateInspector(point){
 if(!point){set("flow-hover","Tap or hover a colored bin to inspect source-backed values.");return;}
 if(point.missing){set("flow-hover","x="+fmt(point.x,5)+" m · z="+fmt(point.z,5)+" m · no active exported cell sample");return;}
 const {cell}=point;
 set("flow-hover","x="+fmt(point.x,5)+" m · z="+fmt(point.z,5)+" m · "+
  G.field+"="+fmt(point.value,4)+" "+(scOptions[G.field]?.unit||"")+" · "+
  cell.region+" · "+cell.count+" active cell-center samples / display bin");
}
function updateLegend(data){
 const v=G.mainDrawResult?.range;
 const metadata=scOptions[G.field]||scOptions.speed;
 if(!v){set("flow-color-min","N/A");set("flow-color-max","N/A");set("flow-unit",metadata.unit);return;}
 set("flow-color-min",fmt(v.min,3));set("flow-color-max",fmt(v.max,3));
 set("flow-unit",metadata.unit+" · 2–98% display range");
 const bar=$("flow-colorbar");if(!bar)return;
 const ctx=bar.getContext("2d");
 for(let x=0;x<bar.width;x++){
  const rgb=color(x/(bar.width-1),G.field==="vorticity");
  ctx.fillStyle="rgb("+rgb.join(",")+")";ctx.fillRect(x,0,1,bar.height);
 }
}
function updateSide(frame,fieldData,result){
 const mode=frame?.kind==="flow"?"NATIVE CFD FLOW":"NATIVE MESH ONLY";
 $("flow-provenance-tag").dataset.status=frame?.kind==="flow"?"FLOW":"MESH";
 set("flow-provenance-tag",mode);
 set("flow-canvas-title",(scOptions[G.field]?.label||"Field")+" ["+(scOptions[G.field]?.unit||"[-]")+"]");
 set("flow-selected-time",sourceLabel(frame));
 set("flow-selected-detail",frame?.sources?.map(p=>p.split(/[\\/]/).slice(-2).join("/")).join(" + ")||"No source.");
 const b=fieldData?.layers?.find(x=>x.name==="Background"),f=fieldData?.layers?.find(x=>x.name==="FlapOverset");
 const describe=(x)=>x?escapeHTML(x.name)+": "+(x.cells?.length||0)+" active display bins; statuses "+Object.entries(x.all_status_counts||{}).map(([k,v])=>k+":"+v).join(", "):"No source";
 $("flow-quality").innerHTML="<p>"+describe(b)+"</p><p>"+describe(f)+"</p><p>Only status 0 enters the contours. Status -2 acceptors and 1 inactive are excluded.</p>";
 const p=pressurePointsFor(frame).filter(x=>x.zone==="liquid_all");
 if(p.length){
  const x=p.reduce((a,b)=>a.pabs<=b.pabs?a:b);
  $("flow-minima").innerHTML="<strong>"+fmt(x.pabs/1000,4)+" kPa</strong><p>x="+fmt(x.x,5)+" m; z="+fmt(x.z,5)+" m; diagnostic margin "+fmt(x.pabs/1000-RAMP_THRESHOLD,4)+" kPa</p><p>Native point probe, not a full pressure map.</p>";
 }else $("flow-minima").textContent="No pressure minimum probe at this exact exported snapshot time.";
 const overlay=$("flow-canvas-overlay");
 if(!result?.range){
  overlay.hidden=false;
  overlay.textContent=frame?.kind==="mesh"?
   "NO VELOCITY / PRESSURE FIELD AT THIS TIME. Displaying available mesh metadata only. Choose a full-field HISTORY snapshot for contours.":
   "Selected scalar is not present in this native export. No field has been synthesized.";
 }else overlay.hidden=true;
 set("flow-data-note",fieldData?.processing+
   (result?.range?" · "+result.range.n+" populated bins; 2–98% display range, raw values unchanged.":" · Selected signal unavailable.")+
   (result?.streamlines?" · "+result.streamlines+" vector-traced streamlines.":"")+
   (G.streamlines&&!result?.streamlines?" · Strict path check found no reliable continuous streamlines.":"")+
   (result?.vectors?" · "+result.vectors+" observed vector arrows.":""));
}

function currentFrame(){return frameByID(G.frameId);}
function pickFrame(frame,notify=true){
 if(!frame)return;
 G.frameId=frame.id;
 const selector=$("flow-snapshot");if(selector)selector.value=frame.id;
 const i=sortedFrames().findIndex(f=>f.id===frame.id);
 if($("flow-time-slider"))$("flow-time-slider").value=Math.max(0,i);
 set("flow-frame-time",fmt(frame.time_s,4)+" s");
 set("flow-frame-status",frame.kind==="flow"?"SAVED FULL FIELD":"MESH / STATUS ONLY");
 if(notify&&typeof window.NTNU_RAMP_SELECT_TIME==="function"){
  window.NTNU_RAMP_SELECT_TIME(frame.time_s);
 }
 refreshCurrent();
}
function populateOptions(){
 const list=sortedFrames();
 const signature=list.map(x=>x.id+"@"+x.mtime).join("|");
 if(signature===G.version)return;
 G.version=signature;
 const make=(selector)=>{
  if(!selector)return;
  const old=selector.value;
  selector.replaceChildren(...list.map(f=>{
   const option=document.createElement("option");option.value=f.id;
   option.textContent=fmt(f.time_s,4)+" s · "+(f.kind==="flow"?"VECTORS":"MESH ONLY")+" · "+f.stage+" · "+(f.run_id||"run");
   return option;
  }));
  if(list.some(f=>f.id===old))selector.value=old;
 };
 make($("flow-snapshot"));make($("flow-compare-snapshot"));
 if($("flow-time-slider"))$("flow-time-slider").max=Math.max(0,list.length-1);
 if(!G.frameId||!frameByID(G.frameId)){
  G.frameId=latest()?.id||null;
 }
 if(!G.compareId||!frameByID(G.compareId)){
  const another=list.find(f=>f.id!==G.frameId&&f.has_velocity);
  G.compareId=another?.id||list[0]?.id||null;
 }
 $("flow-compare-snapshot").value=G.compareId||"";
 $("flow-snapshot").value=G.frameId||"";
}
async function fetchJSON(url){
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),18000);
 try{const response=await fetch(url,{cache:"no-store",signal:controller.signal});
 if(!response.ok)throw Error("Source HTTP "+response.status);
 return await response.json();}finally{clearTimeout(timeout);}
}
async function loadFrame(frame,roi){
 if(!frame)return null;
 const key=frame.id+"@"+frame.mtime+"@"+roi;
 if(G.frames.has(key))return G.frames.get(key);
 if(G.loading.has(key))return G.loading.get(key);
 const job=fetchJSON("/api/flow/frame?id="+encodeURIComponent(frame.id)+"&region="+encodeURIComponent(roi));
 G.loading.set(key,job);
 try{
  const data=await job;
  if(data.frame_id!==frame.id||data.region!==roi)throw Error("Unexpected source identity");
  if(G.frames.size>6)G.frames.delete(G.frames.keys().next().value);
  G.frames.set(key,data);
  return data;
 }finally{G.loading.delete(key);}
}
function setMainNativeImages(frame){
 const pic=(view,target)=>{
  const el=$(target);if(!el)return;
  const url="/api/flow/native?id="+encodeURIComponent(frame?.id||"")+"&view="+view;
  el.src=url;el.alt="Actual STAR-CCM+ "+view+" mesh image for run "+(frame?.run_id||"unknown");
  el.onerror=()=>{el.alt="No native mesh snapshot available for this source";el.style.display="none";};
  el.onload=()=>{el.style.display="block";};
 };
 pic("mesh_foil","flow-mesh-foil");pic("mesh_hinge","flow-mesh-hinge");
 set("flow-geometry-accuracy","Native STAR mesh screenshots belong to run "+(frame?.run_id||"unknown")+
   ". Their image capture time may differ from the selected physical-time field. These are not remapped onto the contour.");
}
function findExactMinField(frame){
 const m=pressurePointsFor(frame).filter(x=>x.zone==="liquid_all");
 if(!m.length)return null;
 return m.reduce((a,b)=>a.pabs<=b.pabs?a:b);
}
function clearViewer(){
 const c=$("flow-canvas");
 if(!c)return;
 const ctx=c.getContext("2d");ctx.fillStyle="#081522";ctx.fillRect(0,0,c.width,c.height);
}
async function refreshCurrent(){
 const frame=currentFrame();
 if(!frame)return;
 const token=G.frameId+"|"+G.field+"|"+G.region;
 G.requestToken=token;
 set("flow-selected-time",sourceLabel(frame));
 set("flow-frame-time",fmt(frame.time_s,4)+" s");
 set("flow-frame-status",frame.kind==="flow"?"EXPORTED FIELD":"EXPORTED MESH");
 const overlay=$("flow-canvas-overlay");
 overlay.hidden=false;overlay.textContent="Reading validated native source / cached display bins...";
 let data;
 try{data=await loadFrame(frame,G.region);}
 catch(error){
  if(G.requestToken===token){overlay.hidden=false;overlay.textContent="Source temporarily unavailable: "+error.message;}
  return;
 }
 if(G.requestToken!==token)return;
 G.currentData=data;
 try{
  G.mainDrawResult=drawNative(data,$("flow-canvas"),G.field,{
   zoom:G.zoom,panX:G.panX,panY:G.panY,contours:G.contours,
   streamlines:G.streamlines,vectors:G.vectors,samples:G.samples,walls:G.walls,density:G.density
  });
  updateSide(frame,data,G.mainDrawResult);updateLegend(data);
  setMainNativeImages(frame);
  if(G.mode==="live")$("flow-snapshot").value=frame.id;
  await refreshCompare();
  window.NTNU_FLOW_ERROR=null;
 }catch(error){
  window.NTNU_FLOW_ERROR={message:String(error),stack:error.stack};
  console.error("Native flow render error",error);
  overlay.hidden=false;overlay.textContent="Native render error: "+error.message;
 }
}
async function refreshCompare(){
 if(!G.currentData)return;
 const a=G.currentData,metaB=frameByID(G.compareId)||latest();
 if(!metaB)return;
 const expected=G.frameId+"|"+G.compareId+"|"+G.region+"|"+G.field;
 G.compareToken=expected;
 let b;
 try{b=await loadFrame(metaB,G.region);}
 catch(error){set("flow-compare-b-title","Frame B unavailable: "+error.message);return;}
 if(G.compareToken!==expected)return;
 const A=readRange(arraysFor(a),G.field);
 const B=readRange(arraysFor(b),G.field);
 const common=G.compareLocked&&A&&B?{min:Math.min(A.min,B.min),max:Math.max(A.max,B.max)}:null;
 drawNative(a,$("flow-compare-a"),G.field,{width:720,height:360,dpi:1,sharedRange:common,walls:true});
 drawNative(b,$("flow-compare-b"),G.field,{width:720,height:360,dpi:1,sharedRange:common,walls:true});
 set("flow-compare-a-title","A · "+fmt(a.time_s,4)+" s · "+a.stage+" · "+(A?"native scalar":"NO SCALAR"));
 set("flow-compare-b-title","B · "+fmt(b.time_s,4)+" s · "+b.stage+" · "+(B?"native scalar":"NO SCALAR"));
}
function showTop(){
 const m=G.manifest;if(!m)return;
 const ramp=m.ramp||{};
 set("flow-current-experiment",m.experiment||"No experiment");
 set("flow-current-time",ramp.state+" · last recorded t="+fmt(ramp.t,4)+" s");
 set("flow-latest-field",fmt(m.latest_vector_field_time_s,4)+" s");
 set("flow-lag",num(ramp.t)&&num(m.latest_vector_field_time_s)?
   "Full-field lag: "+fmt(ramp.t-m.latest_vector_field_time_s,4)+" s":"No aligned time information");
 const l=m.pressure_zones?.points?.filter(p=>p.zone==="liquid_all")||[];
 const last=l.length?l[l.length-1]:null;
 set("flow-pressure-state",last?
  "Latest recorded min "+fmt(last.pabs/1000,3)+" kPa · margin "+fmt(last.pabs/1000-RAMP_THRESHOLD,3)+" kPa":
  "No point pressure measurements");
 const pill=$("flow-state");pill.dataset.status="FLOW";
 pill.textContent=G.mode.toUpperCase()+" · "+sortedFrames().length+" SOURCES";
 set("flow-ramp-note",sortedFrames().filter(x=>x.has_velocity).length+" real volume field snapshots + "+
    sortedFrames().filter(x=>x.kind==="mesh").length+" mesh-only snapshots. Current solver state "+ramp.state+
    "; field snapshots do not extend to all ramp steps.");
}
async function preview(){
 const frame=latest("speed");
 const canvas=$("flow-preview-canvas");
 if(!frame||!canvas||canvas.getBoundingClientRect().width<10)return;
 try{
  const data=await loadFrame(frame,"foil");
  drawNative(data,canvas,"speed",{width:Math.round(canvas.getBoundingClientRect().width),
    height:Math.round(canvas.getBoundingClientRect().height),contours:true,streamlines:false,walls:true});
  set("flow-overview-title","Velocity · t="+fmt(frame.time_s,4)+" s · native export");
  set("flow-overview-meta","Actual sampled volume field, not current solver time. Newest verified full field t="+
    fmt(frame.time_s,4)+" s. Later force and mesh observations are separate.");
 }catch(error){
  set("flow-overview-title","Field preview unavailable");
  set("flow-overview-meta",error.message);
 }
}
function ensureSelection(){
 const frame=currentFrame();if(!frame)return;
 $("flow-snapshot").value=frame.id;
}
async function refreshManifest(){
 try{
  const m=await fetchJSON("/api/flow/manifest");
  if(!Array.isArray(m.frames))throw Error("Invalid frame manifest");
  G.manifest=m;
  populateOptions();showTop();
  if(G.mode==="live"){const f=latest();if(f)G.frameId=f.id;}
  if($("flow-snapshot"))$("flow-snapshot").value=G.frameId||"";
  const frame=currentFrame();
  if(frame){
   set("flow-frame-time",fmt(frame.time_s,4)+" s");
   $("flow-time-slider").value=sortedFrames().findIndex(x=>x.id===frame.id);
  }
  if($("page-flow")?.classList.contains("active"))await refreshCurrent();
  if($("page-overview")?.classList.contains("active"))await preview();
 }catch(error){
  const pill=$("flow-state");if(pill){pill.textContent="SOURCE OFFLINE";pill.dataset.status="MESH";}
  set("flow-overview-meta","Native source read unavailable: "+error.message);
 }
}

function stopPlayback(){
 G.playing=false;
 if(G.timer){clearInterval(G.timer);G.timer=null;}
 set("flow-play","Play");
}
function advanceSnapshot(){
 const list=sortedFrames();if(!list.length){stopPlayback();return;}
 const current=list.findIndex(f=>f.id===G.frameId);
 const next=list[(current+1)%list.length];
 G.mode="history";setModeWithoutSelection();
 pickFrame(next,true);
}
function setModeWithoutSelection(){
 document.querySelectorAll("[data-flow-mode]").forEach(el=>el.classList.toggle("selected",el.dataset.flowMode===G.mode));
 showTop();
}
function bindFlow(){
 document.querySelectorAll("[data-flow-mode]").forEach(btn=>btn.addEventListener("click",()=>{
  stopPlayback();setMode(btn.dataset.flowMode);
 }));
 $("flow-snapshot").addEventListener("change",event=>{
  stopPlayback();G.mode="history";setModeWithoutSelection();
  G.zoom=1;G.panX=0;G.panY=0;
  pickFrame(frameByID(event.target.value),true);
 });
 $("flow-scalar").addEventListener("change",event=>{
  G.field=event.target.value;
  if(G.mode==="live"){const f=latest();if(f)G.frameId=f.id;}
  refreshCurrent();showTop();
 });
 $("flow-region").addEventListener("change",event=>{
  G.region=event.target.value;G.zoom=1;G.panX=0;G.panY=0;refreshCurrent();
 });
 for(const [element,field] of [
  ["flow-contours","contours"],["flow-streamlines","streamlines"],["flow-vectors","vectors"],
  ["flow-samples","samples"],["flow-wall","walls"]]){
  $(element).addEventListener("change",event=>{G[field]=event.target.checked;refreshCurrent();});
 }
 $("flow-density").addEventListener("input",event=>{
  G.density=Number(event.target.value);set("flow-density-label",G.density);
  if(G.currentData&&G.mainDrawResult)refreshCurrent();
 });
 $("flow-reset-view").addEventListener("click",()=>{
  G.zoom=1;G.panX=0;G.panY=0;refreshCurrent();
 });
 $("flow-time-slider").addEventListener("input",event=>{
  stopPlayback();G.mode="history";setModeWithoutSelection();
  pickFrame(sortedFrames()[Number(event.target.value)],true);
 });
 $("flow-play").addEventListener("click",()=>{
  if(G.playing){stopPlayback();return;}
  if(sortedFrames().length<2)return;
  G.mode="history";setModeWithoutSelection();
  G.playing=true;set("flow-play","Pause");
  // Discrete replay ONLY of individual exported snapshots.
  advanceSnapshot();
  G.timer=setInterval(advanceSnapshot,1450);
 });
 $("flow-compare-snapshot").addEventListener("change",event=>{
  G.compareId=event.target.value;refreshCompare();
 });
 $("flow-same-scale").addEventListener("change",event=>{
  G.compareLocked=event.target.checked;refreshCompare();
 });
 $("flow-export-png").addEventListener("click",async()=>{
  const data=G.currentData,frame=currentFrame();if(!data||!frame)return;
  const image=document.createElement("canvas");
  drawNative(data,image,G.field,{width:2048,height:1050,dpi:1,
    contours:G.contours,streamlines:G.streamlines,vectors:G.vectors,samples:G.samples,walls:G.walls,density:G.density});
  const out=document.createElement("canvas");out.width=2048;out.height=1150;
  const ctx=out.getContext("2d");ctx.fillStyle="#091522";ctx.fillRect(0,0,2048,1150);
  ctx.drawImage(image,0,0);
  ctx.fillStyle="#ecf5fa";ctx.font="600 31px Consolas,monospace";
  ctx.fillText("NTNU Science / "+scOptions[G.field].label,30,1090);
  ctx.fillStyle="#9cb3c4";ctx.font="23px Consolas,monospace";
  ctx.fillText("native t="+fmt(frame.time_s,4)+" s · "+frame.id+
    " · "+G.region+" · "+scOptions[G.field].unit,30,1124);
  out.toBlob(blob=>{
   if(!blob)return;
   const url=URL.createObjectURL(blob);
   const a=document.createElement("a");a.href=url;
   a.download="NTNU_FlowField_"+frame.id+"_"+G.region+"_"+G.field+".png";
   a.click();setTimeout(()=>URL.revokeObjectURL(url),1800);
  },"image/png");
 });
 const canvas=$("flow-canvas");
 let dragging=false,lastX=0,lastY=0,moved=false;
 canvas.addEventListener("wheel",event=>{
  event.preventDefault();
  const mult=event.deltaY<0?1.15:1/1.15;
  G.zoom=Math.max(.8,Math.min(14,G.zoom*mult));refreshCurrent();
 },{passive:false});
 canvas.addEventListener("pointerdown",event=>{
  dragging=true;moved=false;lastX=event.clientX;lastY=event.clientY;
  canvas.setPointerCapture?.(event.pointerId);
 });
 canvas.addEventListener("pointermove",event=>{
  if(dragging){
   const dx=event.clientX-lastX,dy=event.clientY-lastY;
   if(Math.abs(dx)+Math.abs(dy)>1)moved=true;
   G.panX+=dx;G.panY+=dy;lastX=event.clientX;lastY=event.clientY;
   if(G.currentData){
    G.mainDrawResult=drawNative(G.currentData,canvas,G.field,{
     zoom:G.zoom,panX:G.panX,panY:G.panY,contours:G.contours,
     streamlines:G.streamlines,vectors:G.vectors,samples:G.samples,walls:G.walls,density:G.density});
   }
   return;
  }
  const rect=canvas.getBoundingClientRect();
  updateInspector(selectCell(G.currentData,G.mainDrawResult,
   event.clientX-rect.left,event.clientY-rect.top));
 });
 canvas.addEventListener("pointerup",event=>{
  dragging=false;
  if(!moved){
   const rect=canvas.getBoundingClientRect();
   updateInspector(selectCell(G.currentData,G.mainDrawResult,
    event.clientX-rect.left,event.clientY-rect.top));
  }
 });
 canvas.addEventListener("pointercancel",()=>{dragging=false;});
 window.addEventListener("resize",()=>{
  if($("page-flow")?.classList.contains("active")&&G.currentData)refreshCurrent();
  if($("page-overview")?.classList.contains("active"))preview();
 });
 document.querySelectorAll("[data-open='flow'],[data-page='flow']").forEach(button=>button.addEventListener("click",()=>{
  if(G.manifest)refreshCurrent();
 }));
 window.addEventListener("hashchange",()=>{
  if(location.hash==="#flow")refreshCurrent();
  if(location.hash==="#overview")preview();
 });
 window.NTNU_FLOW_CURSOR_TIME=(t)=>{
  if(!num(t)||!G.manifest)return;
  // UI chooses nearest *existing* export and explicitly discloses its own timestamp.
  G.requestedRampTime=t;
  if(G.mode==="history"){
   const f=sortedFrames().reduce((a,b)=>!a||Math.abs(b.time_s-t)<Math.abs(a.time_s-t)?b:a,null);
   if(f)pickFrame(f,false);
  }
 };
}
function init(){
 bindFlow();
 refreshManifest();
 setInterval(refreshManifest,15000);
}
document.addEventListener("DOMContentLoaded",init);
})();

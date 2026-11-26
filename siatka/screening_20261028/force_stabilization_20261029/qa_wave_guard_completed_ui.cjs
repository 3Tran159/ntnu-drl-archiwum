const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),report=[];
 const state=JSON.parse(fs.readFileSync(R+'wave_propagation_state.json','utf8')),diag=JSON.parse(fs.readFileSync(R+'wave_pilot_r3_spatial_diagnostic.json','utf8'));
 const done=JSON.parse(fs.readFileSync(require('path').join(require('path').dirname(diag.source),'completed.json'),'utf8'));
 assert.equal(done.status,'stability_guard');
 for(const kind of ['main','professor'])for(const width of [1920,1360,390]){
  const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
  await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
  await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});
  await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
  const wave=p.locator(kind==='main'?'#wave-preparation-live':'#waves .wave-preparation-status');
  const text=await wave.innerText();
  for(const expected of [state.case,'Previous transient attempt:','W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3',done.time_s.toFixed(3)+' s on the stability guard',diag.max_speed.speed_m_s.toFixed(3)+' m/s in water','not yet been accepted','not accepted'])assert(text.includes(expected),expected);
  if(state.status==='propagation_GPU_running')assert(text.includes('GPU wave propagation pilot running'));
  const captions=await wave.locator('img').evaluateAll(es=>es.map(e=>e.alt));assert(captions.every(x=>x.includes(state.case)));
  await wave.scrollIntoViewIfNeeded();await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  await wave.screenshot({path:R+'wave_guard_completed_'+kind+'_'+width+'.png'});
  const prep=p.locator(kind==='main'?'#wave-foil-preparation-live':'#waves .wave-foil-preparation'),prepText=await prep.innerText();
  for(const expected of ['Mesh prepared; boundary and flow setup pending','CPU preparation completed','246,885 cells','single-span topology passed','0 flow steps','no wave-flow result'])assert(prepText.includes(expected),expected);
  await prep.screenshot({path:R+'foil_mesh_prepared_'+kind+'_'+width+'.png'});
  const calm=await p.locator(kind==='main'?'#selected-mesh-time-live':'#selected-mesh-time-review').innerText();assert(calm.includes('Supported calm mesh template'));assert(calm.includes('Time-step check passed'));assert(calm.includes('-0.002423%'));assert(calm.includes('+0.001453%'));
  const info=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i)}));
  if(info.overflow)console.log(JSON.stringify({kind,width,overflow:await p.evaluate(()=>({doc:document.documentElement.scrollWidth,inner:innerWidth,items:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1&&e.getBoundingClientRect().width>0).filter(e=>{for(let a=e.parentElement;a&&a!==document.body;a=a.parentElement)if(['auto','scroll','hidden','clip'].includes(getComputedStyle(a).overflowX))return false;return true;}).slice(0,40).map(e=>({tag:e.tagName,id:e.id,cls:e.className,text:e.textContent,parent:e.parentElement.outerHTML.substring(0,500),right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width}))}))}));
  assert(!info.overflow,kind+' '+width);assert(!info.duplicateIds.length);assert(!errors.length);
  if(kind==='professor'&&width===1360){
   await p.emulateMedia({media:'print'});info.intentionalPrintPages=await p.locator('.print-report .print-page').count();
   info.printWavePage=await p.locator('.print-report .print-page').evaluateAll(es=>1+es.findIndex(e=>e.querySelector('.wave-preparation-status')));
   assert.equal(info.intentionalPrintPages,18);
   await p.pdf({path:R+'wave_guard_professor_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
  }
  report.push({kind,width,...info,waveText:text,foilPreparationText:prepText,figureCaptions:captions,errors});await p.close();
 }
 await b.close();fs.writeFileSync(R+'wave_guard_completed_dashboard_qa.json',JSON.stringify({checked_at:new Date().toISOString(),case:state.case,previous_case:'W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3',previous_completed:done,views:report},null,2));
 console.log(JSON.stringify(report.map(({kind,width,overflow,duplicateIds,intentionalPrintPages,printWavePage,errors})=>({kind,width,overflow,duplicateIds,intentionalPrintPages,printWavePage,errors}))));
})().catch(e=>{console.error(e);process.exit(1);});

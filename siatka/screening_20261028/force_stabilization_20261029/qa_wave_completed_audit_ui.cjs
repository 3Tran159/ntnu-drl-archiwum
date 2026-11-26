const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),views=[],r8=JSON.parse(fs.readFileSync(R+'wave_halfdt_probe_r8_review.json','utf8'));
 try{
  for(const kind of ['main','professor'])for(const width of [1360,390]){
   const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
   await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
   await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});
   await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
   const wave=p.locator(kind==='main'?'#wave-preparation-live':'#waves .wave-preparation-status'),text=await wave.innerText();
   for(const term of ['Completed — mass-budget criterion not met','0.750 s','Completed steps','500','run ended','Completed half-step result:',r8.budget_halfdt10inner_max_abs_pct.toFixed(9)+'%','6 / 497 half-step samples above the limit',r8.max_gauge_difference_halfdtminus1ms_mm.toFixed(6)+' mm',r8.max_speed_halfdt_m_s.toFixed(4)+' m/s','Longer propagation not admitted','Report definitions are under review'])assert(text.includes(term),term);
   assert(!text.includes('result pending'));assert(!text.includes('GPU wave propagation pilot running'));assert(!text.includes('mass leak'));
   const audit=wave.locator('.wave-report-audit'),auditText=await audit.innerText();assert(auditText.includes('1 CPU worker · no GPU · zero-step diagnostic'));assert(auditText.includes('checkpoint_t0.750.sim'));assert(auditText.includes('No transient steps'));
   const captions=await wave.locator('img').evaluateAll(es=>es.map(e=>e.alt));assert(captions.every(x=>x.includes(r8.case)));
   const fsPanel=p.locator(kind==='main'?'#wave-foil-preparation-live .wave-fs-refinement':'#waves .wave-fs-refinement'),fsText=await fsPanel.innerText();assert(fsText.includes('M10_FS020_r1'));assert(fsText.includes('2 CPU workers · no GPU'));assert(fsText.includes('accepted calm M09 remains separate'));
   const calm=await p.locator(kind==='main'?'#selected-mesh-time-live':'#selected-mesh-time-review').innerText();assert(calm.includes('Supported calm mesh template'));
   await wave.screenshot({path:R+'wave_completed_audit_'+kind+'_'+width+'.png'});await fsPanel.screenshot({path:R+'wave_completed_fs_'+kind+'_'+width+'.png'});
   const info=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i)}));assert(!info.overflow);assert(!info.duplicateIds.length);assert(!errors.length);
   if(kind==='professor'&&width===1360){
    await p.emulateMedia({media:'print'});info.intentionalPrintPages=await p.locator('.print-report .print-page').count();assert.equal(info.intentionalPrintPages,18);
    await p.pdf({path:R+'wave_completed_audit_professor_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
   }
   views.push({kind,width,...info,waveText:text,auditText,fsText,imageCaptions:captions,errors});await p.close();
  }
  fs.writeFileSync(R+'wave_completed_audit_dashboard_qa.json',JSON.stringify({checked_at:new Date().toISOString(),views},null,2));console.log(JSON.stringify(views.map(({kind,width,overflow,duplicateIds,intentionalPrintPages,errors})=>({kind,width,overflow,duplicateIds,intentionalPrintPages,errors}))));
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1);});

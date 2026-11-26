const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),views=[],r6=JSON.parse(fs.readFileSync(R+'wave_inner20_probe_r6_review.json','utf8'));
 try{
  for(const kind of ['main','professor'])for(const width of [1360,390]){
   const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
   await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
   await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});
   await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
   const wave=p.locator(kind==='main'?'#wave-preparation-live':'#waves .wave-preparation-status'),numerics=wave.locator('.wave-numerical-probe'),text=await numerics.innerText();
   for(const term of ['0.502–0.750 s',r6.budget_10inner_max_abs_pct.toFixed(7)+'%',r6.budget_20inner_max_abs_pct.toFixed(7)+'%','0.01% gate not passed','4 samples above',r6.max_gauge_difference_20minus10_mm.toFixed(4)+' mm','0.500 ms · 10 inner','0.500 s checkpoint → 0.750 s target (500 steps)'])assert(text.includes(term),term);
   const waveText=await wave.innerText();assert(waveText.includes('halfdt10inner_r8'));
   const captions=await wave.locator('img').evaluateAll(es=>es.map(e=>e.alt));assert(captions.every(x=>x.includes('halfdt10inner_r8')));
   const fsPanel=p.locator(kind==='main'?'#wave-foil-preparation-live .wave-fs-refinement':'#waves .wave-fs-refinement'),fsText=await fsPanel.innerText();
   for(const term of ['M10_FS020_r1','2 CPU workers · no GPU','28.571 → 20.000 mm','accepted calm M09 remains separate','earlier LE/TE proposal remains unbuilt'])assert(fsText.includes(term),term);
   const calm=await p.locator(kind==='main'?'#selected-mesh-time-live':'#selected-mesh-time-review').innerText();assert(calm.includes('Supported calm mesh template'));
   await wave.screenshot({path:R+'wave_numerics_'+kind+'_'+width+'.png'});await fsPanel.screenshot({path:R+'wave_fs_variant_'+kind+'_'+width+'.png'});
   const info=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i)}));assert(!info.overflow);assert(!info.duplicateIds.length);assert(!errors.length);
   if(kind==='professor'&&width===1360){
    await p.emulateMedia({media:'print'});info.intentionalPrintPages=await p.locator('.print-report .print-page').count();assert.equal(info.intentionalPrintPages,18);
    await p.pdf({path:R+'wave_numerics_fs_professor_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
   }
   views.push({kind,width,...info,waveText,numericsText:text,fsText,imageCaptions:captions,errors});await p.close();
  }
  fs.writeFileSync(R+'wave_numerics_fs_dashboard_qa.json',JSON.stringify({checked_at:new Date().toISOString(),views},null,2));console.log(JSON.stringify(views.map(({kind,width,overflow,duplicateIds,intentionalPrintPages,errors})=>({kind,width,overflow,duplicateIds,intentionalPrintPages,errors}))));
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1);});

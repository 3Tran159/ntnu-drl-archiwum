const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),views=[];
 try{
  for(const kind of ['main','professor'])for(const width of [1360,390]){
   const p=await browser.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
   await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
   await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});
   await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
   const region=p.locator(kind==='main'?'#wave-foil-preparation-live':'#waves .wave-foil-preparation'),paired=region.locator('.wave-foil-case-preparation'),text=await paired.innerText();
   for(const term of ['C01 / W01 input preparation','1 CPU worker · no GPU','Zero-step input preparation only','No foil-flow calculation is admitted by this stage','Saved update:'])assert(text.includes(term),term);
   assert(/(?:C01|W01)_W20L4_M09_env_setup_r2/.test(text));
   const wave=p.locator(kind==='main'?'#wave-preparation-live':'#waves .wave-preparation-status'),waveText=await wave.innerText();
   assert(waveText.includes('W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'));assert(!waveText.includes('Wave validation passed'));
   const imageCaptions=await wave.locator('img').evaluateAll(es=>es.map(e=>e.alt));assert(imageCaptions.every(x=>x.includes('W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4')));
   await region.screenshot({path:R+'paired_input_prep_'+kind+'_'+width+'.png'});
   const info=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i)}));
   assert(!info.overflow);assert(!info.duplicateIds.length);assert(!errors.length);
   if(kind==='professor'&&width===1360){
    await p.emulateMedia({media:'print'});info.printPages=await p.locator('.print-report .print-page').count();assert.equal(info.printPages,18);
    info.preparationHiddenInPrint=await p.locator('.print-report .wave-foil-preparation').evaluate(e=>getComputedStyle(e).display==='none');assert(info.preparationHiddenInPrint);
    await p.pdf({path:R+'paired_input_professor_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
   }
   views.push({kind,width,...info,pairedInputText:text,waveText,imageCaptions,errors});await p.close();
  }
  fs.writeFileSync(R+'paired_input_preparation_dashboard_qa.json',JSON.stringify({checked_at:new Date().toISOString(),views},null,2));
  console.log(JSON.stringify(views.map(({kind,width,overflow,duplicateIds,printPages,preparationHiddenInPrint,errors})=>({kind,width,overflow,duplicateIds,printPages,preparationHiddenInPrint,errors}))));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});

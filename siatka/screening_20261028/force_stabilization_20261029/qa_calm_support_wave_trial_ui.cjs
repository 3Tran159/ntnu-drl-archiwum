const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),report=[];
const result=JSON.parse(fs.readFileSync(R+'selected_mesh_time_results.json','utf8')),decision=JSON.parse(fs.readFileSync(R+'selected_mesh_decision.json','utf8')),fmt=x=>(x>=0?'+':'')+x.toFixed(6)+'%';
assert.equal(decision.status,'supported_calm_mesh_template');
for(const kind of ['main','professor'])for(const width of [1920,1360,390]){
 const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
 await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
 await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
 const panel=p.locator(kind==='main'?'#selected-mesh-time-live':'#selected-mesh-time-review'),wave=p.locator(kind==='main'?'#wave-preparation-live':'#waves .wave-preparation-status');
 if(kind==='main'){const old=await p.locator('#mesh-selection').innerText();assert(old.includes('Historical first-order mesh comparison'));assert(!old.includes('No mesh selected yet'));assert(!old.includes('Wave runs remain on hold'));}
 const text=await panel.innerText();assert(text.includes('Supported calm mesh template'));assert(text.includes('Time-step check passed'));assert(text.includes('214,908 cells'));assert(text.includes('Second-order time · 1.000 ms · 10 inner iterations'));assert(!text.includes('acceptance pending'));
 const row=await panel.locator('tbody tr').first().evaluate(e=>[...e.cells].map(c=>c.innerText));
 assert.deepEqual(row.slice(1),['CD','CL_total','pressure_drag_N','viscous_drag_N'].map(k=>fmt(result.half_vs_1ms_difference_pct[k])));
 await panel.screenshot({path:R+'calm_support_ui_'+kind+'_'+width+'.png'});
 const fields=p.locator(kind==='main'?'#configured-fields-live':'#configured-fields-reviewed');
 if(kind==='main')await fields.locator('summary').click();
 assert.equal(await fields.locator('img').count(),3);
 const fieldChecks=[];
 for(const img of await fields.locator('img').all()){
  const caption=await img.getAttribute('alt');assert(caption.includes('Common-endpoint instantaneous saved field'));assert(caption.includes('t = 2.040 s'));
  const mesh=caption.match(/^M\d+/)[0],src=await img.getAttribute('src'),crypto=require('crypto');
  const actual=crypto.createHash('sha256').update(Buffer.from(src.split(',')[1],'base64')).digest('hex'),expected=crypto.createHash('sha256').update(fs.readFileSync(R+'matched_fields_'+mesh+'.png')).digest('hex');
  assert.equal(actual,expected);fieldChecks.push({mesh,time_s:2.04,image_sha256:actual,caption});
 }
 await fields.locator('figure').last().screenshot({path:R+'matched_fields_ui_'+kind+'_'+width+'.png'});
 const waveText=await wave.innerText();assert(waveText.includes('W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3'));assert(waveText.includes('GPU · 1 CPU worker'));assert(waveText.includes('Previous transient attempt:'));assert(waveText.includes('0.704 s'));assert(waveText.includes('50.735 m/s in air'));assert(waveText.includes('18.482 / 18.477 m/s'));assert(waveText.includes('not accepted'));assert(waveText.includes('not yet been accepted'));
 const captions=await wave.locator('img').evaluateAll(es=>es.map(e=>e.alt));assert(captions.every(x=>x.includes('W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3')&&!x.includes('CPUprop_dt1ms_r2')));
 await wave.scrollIntoViewIfNeeded();await p.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await wave.screenshot({path:R+'wave_trial_ui_'+kind+'_'+width+'.png'});
 const prep=p.locator(kind==='main'?'#wave-foil-preparation-live':'#waves .wave-foil-preparation');assert.equal(await prep.count(),1);assert((await prep.innerText()).includes('no wave-flow result'));await prep.screenshot({path:R+'wave_foil_preparation_ui_'+kind+'_'+width+'.png'});
 const info=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i)}));assert(!info.overflow);assert(!info.duplicateIds.length);assert(!errors.length);
 if(kind==='professor'){
  info.headline=await p.locator('main>.decision').innerText();assert(info.headline.includes('M09 is supported as the calm mesh template.'));assert(!info.headline.includes('Calm-template decision pending'));
  if(width===1920)await p.locator('main>.decision').screenshot({path:R+'calm_support_assessment_1920.png'});
 }
 if(kind==='professor'&&width===1360){
  await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));});
  await p.emulateMedia({media:'print'});info.intentionalPrintPages=await p.locator('.print-report .print-page').count();
  info.printTimePage=await p.locator('.print-report .print-page').evaluateAll(es=>1+es.findIndex(e=>e.querySelector('.selected-mesh-time')));
  info.printWavePage=await p.locator('.print-report .print-page').evaluateAll(es=>1+es.findIndex(e=>e.querySelector('.wave-preparation-status')));
  assert.equal(await p.locator('.print-report .selected-mesh-time').count(),1);
  await p.pdf({path:R+'calm_support_professor_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
 }
 report.push({kind,width,...info,dtRow:row,fieldChecks,waveText,visibleCurrentCaseFigureCount:captions.length,figureCaptions:captions,errors});await p.close();
}
await b.close();fs.writeFileSync(R+'calm_support_wave_trial_dashboard_qa.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report.map(({kind,width,overflow,duplicateIds,dtRow,visibleCurrentCaseFigureCount,intentionalPrintPages,printTimePage,printWavePage,errors})=>({kind,width,overflow,duplicateIds,dtRow,visibleCurrentCaseFigureCount,intentionalPrintPages,printTimePage,printWavePage,errors}))));
})().catch(e=>{console.error(e);process.exit(1);});
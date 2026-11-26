const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),out=[];
for(const kind of ['main','professor'])for(const width of [1360,390]){
 const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
 await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
 if(kind==='main'){await p.locator('#refreshToggle').click();await p.locator('#configured-fields-live summary').click();}
 await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});
 await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
 const sel=kind==='main'?'#configured-fields-live':'#configured-fields-reviewed';
 await p.locator(sel).scrollIntoViewIfNeeded();await p.locator(sel).screenshot({path:R+'configured_fields_ui_'+kind+'_'+width+'.png'});
 const info=await p.locator(sel).evaluate(e=>({text:e.innerText,overflow:document.documentElement.scrollWidth>innerWidth+1,duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i),images:[...e.querySelectorAll('img')].map(i=>({caption:i.alt,loaded:i.complete&&i.naturalWidth>0,width:i.getBoundingClientRect().width,parentWidth:i.parentElement.clientWidth,sha:i.dataset.sourceSha256||null})),historicalProfessorImages:document.querySelectorAll('#fields>figure.field').length,waveText:document.querySelector('#wave-preparation-live,#waves .wave-preparation-status')?.innerText}));
 assert(!info.overflow);assert(!info.duplicateIds.length);assert(info.images.length>=2);assert(info.images.every(x=>x.loaded&&x.caption.includes('second-order time')&&x.caption.includes('1.000 ms')&&x.caption.includes('10 inner iterations')));assert(info.images.some(x=>x.caption.includes('M09')&&x.caption.includes('1.640 s')));assert(info.images.some(x=>x.caption.includes('M08')&&x.caption.includes('2.000 s')));if(kind==='professor')assert.equal(info.historicalProfessorImages,3);
 if(width===390)assert(info.images.every(x=>x.width>=1100));
 assert(info.waveText.includes('propagation pilot'));assert(!info.waveText.includes('Preparation only.'));assert(info.waveText.includes('not yet been accepted'));
 if(kind==='main'){await p.locator(sel+' img').first().click();assert(await p.locator('#imageViewer').evaluate(e=>e.open));await p.locator('#closeImage').click();assert(!(await p.locator('#imageViewer').evaluate(e=>e.open)));}
 else{await p.locator(sel+' .expand-field').first().click();assert(await p.locator('#field-dialog').evaluate(e=>e.open));await p.keyboard.press('Escape');assert(!(await p.locator('#field-dialog').evaluate(e=>e.open)));}
 info.enlargeAndClose=true;assert(!errors.length);
 if(kind==='professor'&&width===1360){await p.emulateMedia({media:'print'});info.intentionalPrintPages=await p.locator('.print-report .print-page').count();assert.equal(info.intentionalPrintPages,13+info.images.length);await p.pdf({path:R+'configured_fields_professor_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});}
 out.push({kind,width,...info,errors});await p.close();
}
await b.close();fs.writeFileSync(R+'configured_fields_dashboard_qa.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out.map(x=>({kind:x.kind,width:x.width,images:x.images.map(i=>i.caption),overflow:x.overflow,duplicateIds:x.duplicateIds,enlargeAndClose:x.enlargeAndClose,intentionalPrintPages:x.intentionalPrintPages,errors:x.errors}))));
})().catch(e=>{console.error(e);process.exit(1);});

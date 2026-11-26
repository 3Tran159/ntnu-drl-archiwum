const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),out=[];
for(const kind of ['main','professor'])for(const width of [1360,390]){
 const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
 await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
 if(kind==='main')await p.locator('#refreshToggle').click();
 await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});
 await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
 const sel=kind==='main'?'#wave-preparation-live':'#waves .wave-preparation-status';
 await p.locator(sel).scrollIntoViewIfNeeded();await p.locator(sel).screenshot({path:R+'wave_prep_'+kind+'_'+width+'.png'});
 const info=await p.locator(sel).evaluate(e=>({text:e.innerText,rect:e.getBoundingClientRect().toJSON(),overflow:document.documentElement.scrollWidth>innerWidth+1,labels:[...e.querySelectorAll('.prep-label')].map(x=>x.textContent),columnOverflow:[...e.querySelectorAll('.wave-prep-grid p')].some(x=>x.scrollWidth>x.clientWidth+1),duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i)}));
 assert(!info.overflow);assert(!info.columnOverflow);assert(!info.duplicateIds.length);assert(!errors.length);
 assert(/W20_H24_X4_Q2D_r[3-9][0-9]*/.test(info.text));assert(info.text.includes('2 CPU workers'));assert(info.text.includes('no GPU'));assert(info.text.includes('No transient propagation result'));assert(info.text.includes('W20_H24_X4_Q2D_r2'));assert(info.text.includes('not admitted'));assert(info.text.includes('Next gate'));
 if(kind==='professor'&&width===1360){await p.emulateMedia({media:'print'});await p.pdf({path:R+'professor_wave_prep_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});}
 out.push({kind,width,...info,errors});await p.close();
}
await b.close();fs.writeFileSync(R+'wave_preparation_dashboard_qa.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out.map(x=>({kind:x.kind,width:x.width,overflow:x.overflow,columnOverflow:x.columnOverflow,duplicateIds:x.duplicateIds,errors:x.errors,labels:x.labels}))));
})().catch(e=>{console.error(e);process.exit(1);});

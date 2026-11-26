const fs=require('fs'),path=require('path');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const B='F:/ntnu/mesh_screening_20261028',R=B+'/force_stabilization_20261029';
const OUT=R+'/accordion_qa_20261030';fs.mkdirSync(OUT,{recursive:true});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function scan(p){
 return p.evaluate(()=>{
  const vis=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
  const ids=[...document.querySelectorAll('[id]')].map(e=>e.id),duplicates=[...new Set(ids.filter((v,i)=>ids.indexOf(v)!==i))];
  const visible=[...document.querySelectorAll('body *')].filter(e=>vis(e));
  const overflow=visible.filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+2&&r.width>5&&!e.closest('.table-wrap,.table-scroll,.wave-data-table,.wave-pilot-scroll,.figure-scroll,.viewer-scroll,svg')}).map(e=>({tag:e.tagName,id:e.id,cls:String(e.className).slice(0,75),right:e.getBoundingClientRect().right,text:(e.innerText||'').slice(0,100)})).slice(0,30);
  return {pageWidth:document.documentElement.scrollWidth,viewport:innerWidth,noPageOverflow:document.documentElement.scrollWidth<=innerWidth+2,duplicates,overflow,brokenImages:[...document.images].filter(e=>vis(e)&&e.complete&&e.naturalWidth===0).map(e=>e.alt),details:[...document.querySelectorAll('details')].map(e=>({id:e.id,open:e.open,summary:e.querySelector(':scope>summary')?.innerText||''})),bodyText:document.body.innerText.slice(0,1400)};
 });
}
async function findDetail(p,pattern){
 const all=p.locator('details');
 for(let i=0;i<await all.count();i++){const s=await all.nth(i).locator(':scope > summary').innerText().catch(()=> '');if(pattern.test(s))return all.nth(i);}
 return null;
}
async function openAncestors(locator){await locator.evaluate(el=>{for(let n=el;n;n=n.parentElement)if(n.tagName==='DETAILS')n.open=true;});}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const report={updated_at:new Date().toISOString(),views:[],prints:[]};
 try{
  for(const kind of (process.argv[2]?[process.argv[2]]:['main','professor'])){
   const url='file:///'+B+'/'+(kind==='main'?'dashboard.html':'professor_dashboard.html');
   for(const width of (process.argv.includes('--print-only')?[]:[1920,1360,390])){
    const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1,isMobile:false});
    const p=await context.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
    await p.addInitScript(()=>{sessionStorage.setItem('ntnuRefresh','off');});
    await p.goto(url,{waitUntil:'load'});await p.waitForTimeout(700);
    const collapsed=await scan(p);
    await p.screenshot({path:OUT+'/'+kind+'_'+width+'_overview.png'});
    const mesh=await findDetail(p,/^mesh study/i),wave=await findDetail(p,/^wave validation/i);
    const entry={kind,width,errors,collapsed,meshFound:!!mesh,waveFound:!!wave};
    if(mesh){
     const initial=await mesh.evaluate(e=>e.open);
     const summary=mesh.locator(':scope>summary');await summary.focus();await p.keyboard.press('Enter');
     entry.keyboardToggle=await mesh.evaluate((e,b)=>e.open!==b,initial);
     await mesh.evaluate(e=>{e.open=true;});
     const sub=mesh.locator('details');
     if(await sub.count())await sub.first().evaluate(e=>e.open=true);
     await p.waitForTimeout(400);
     await summary.evaluate(e=>e.scrollIntoView({block:'start'}));await p.evaluate(()=>window.scrollBy(0,-70));await p.screenshot({path:OUT+'/'+kind+'_'+width+'_mesh.png'});
     entry.expandedMesh=await scan(p);
     const openBefore=await p.locator('details').evaluateAll(es=>es.map((e,i)=>({key:e.id||e.querySelector(':scope>summary')?.textContent||String(i),open:e.open})).filter(e=>e.open).map(e=>e.key));
     await p.reload({waitUntil:'load'});await p.waitForTimeout(500);
     const openAfter=await p.locator('details').evaluateAll(es=>es.map((e,i)=>({key:e.id||e.querySelector(':scope>summary')?.textContent||String(i),open:e.open})).filter(e=>e.open).map(e=>e.key));
     entry.expansionRetained=openBefore.every(key=>openAfter.includes(key));entry.openBefore=openBefore;entry.openAfter=openAfter;
    }
    const freshWave=await findDetail(p,/^wave validation/i);
    if(freshWave){
     await openAncestors(freshWave);
     const ss=freshWave.locator('details');
     if(await ss.count())await ss.first().evaluate(e=>e.open=true);
     await freshWave.locator(':scope>summary').evaluate(e=>e.scrollIntoView({block:'start'}));await p.evaluate(()=>window.scrollBy(0,-70));await p.waitForTimeout(200);
     await p.screenshot({path:OUT+'/'+kind+'_'+width+'_wave.png'});entry.expandedWave=await scan(p);
    }
    if(kind==='main'){
     const status=p.locator('#computer-status');entry.permanentStatus=await status.count()===1&&await status.evaluate(e=>!e.closest('details'));
     entry.statusText=await status.innerText().catch(()=> 'Missing');
    }
    entry.noJsErrors=errors.length===0;
    report.views.push(entry);await context.close();
   }
   const context=await browser.newContext({viewport:{width:1360,height:1000}});
   const p=await context.newPage();await p.addInitScript(()=>sessionStorage.setItem('ntnuRefresh','off'));
   await p.goto(url,{waitUntil:'load'});await p.waitForTimeout(300);
   await p.emulateMedia({media:'print'});await p.evaluate(()=>{window.dispatchEvent(new Event('beforeprint'));document.querySelectorAll('details').forEach(e=>e.open=true);document.querySelectorAll('img').forEach(e=>e.loading='eager');});
   await p.waitForFunction(()=>[...document.images].every(i=>i.complete),{timeout:20000}).catch(()=>{});
   const pdf=OUT+'/'+kind+'_expanded.pdf';await p.pdf({path:pdf,format:'A4',printBackground:true,preferCSSPageSize:true,margin:{top:'12mm',bottom:'12mm',left:'10mm',right:'10mm'}});
   const printCheck=await p.evaluate(()=>({details:document.querySelectorAll('details').length,closedDetails:[...document.querySelectorAll('details')].filter(e=>!e.open).length,broken:[...document.images].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden'&&e.complete&&!e.naturalWidth).length,text:document.body.innerText.slice(0,600)}));
   report.prints.push({kind,pdf,...printCheck});await context.close();
  }
 }finally{await browser.close();fs.writeFileSync(OUT+'/qa'+(process.argv[2]?'_'+process.argv[2]:'')+(process.argv.includes('--print-only')?'_print':'')+'.json',JSON.stringify(report,null,2));}
 console.log(JSON.stringify({path:OUT+'/qa'+(process.argv[2]?'_'+process.argv[2]:'')+(process.argv.includes('--print-only')?'_print':'')+'.json',views:report.views.map(x=>({kind:x.kind,width:x.width,mesh:x.meshFound,wave:x.waveFound,keyboard:x.keyboardToggle,persist:x.expansionRetained,overflow:[x.collapsed,x.expandedMesh,x.expandedWave].filter(Boolean).some(s=>!s.noPageOverflow),errors:x.errors,permanentStatus:x.permanentStatus})),prints:report.prints.map(x=>({kind:x.kind,closed:x.closedDetails,broken:x.broken}))},null,2));
})().catch(e=>{console.error(e.stack);process.exitCode=1});


const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_cycle_integrated_qa_20261030';
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const report={updated_at:new Date().toISOString(),views:[],print:[],safety:'Read-only UI; all non-GET/HEAD blocked. No simulation buttons pressed.'};
 const snapshot=page=>page.evaluate(()=>{
  const q=document.querySelector('.wave-cycle-panel');
  const visible=e=>e&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('details:not([open])');
  const graphs=q?Array.from(q.querySelectorAll('svg')).map(s=>({label:s.getAttribute('aria-label'),viewBox:s.getAttribute('viewBox'),visible:!!visible(s),paths:s.querySelectorAll('polyline').length,pointCount:[...s.querySelectorAll('polyline')].reduce((a,p)=>a+p.getAttribute('points').trim().split(/\s+/).length,0),nonfinite:/NaN|Infinity/.test(s.outerHTML)})):[];
  const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);
  return {panelCount:document.querySelectorAll('.wave-cycle-panel').length,panelVisible:!!visible(q),panelText:q?.innerText??'',graphs,documentWidth:document.documentElement.scrollWidth,viewport:innerWidth,duplicateIds:[...new Set(ids.filter((x,i)=>ids.indexOf(x)!==i))],brokenImages:[...document.images].filter(e=>visible(e)&&(!e.complete||e.naturalWidth===0)).map(e=>e.src),frozenClaim:/original meeting dashboards are frozen/i.test(document.body.innerText),copyBanner:[...document.querySelectorAll('aside,p,div')].filter(e=>e.childElementCount===0&&/WORKING COPY|meeting dashboards/i.test(e.textContent)).map(e=>e.textContent).slice(0,4)};
 });
 for(const [name,url] of [['operational','http://127.0.0.1:8771/'],['professor','http://127.0.0.1:8771/professor_dashboard.html']]){
  for(const width of [1920,1360,390]){
   const page=await browser.newPage({viewport:{width,height:1100}}), errors=[],blocked=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',r=>{if(!['GET','HEAD'].includes(r.request().method())){blocked.push(r.request().method());return r.abort();}return r.continue();});
   await page.addInitScript(()=>{sessionStorage.setItem('ntnuRefresh','off');sessionStorage.setItem('professorRefresh','off');});
   await page.goto(url,{waitUntil:'networkidle'});
   const initial=await snapshot(page);
   await page.screenshot({path:out+'/'+name+'_'+width+'_overview.png'});
   if(initial.panelCount)await page.locator('.wave-cycle-panel').first().screenshot({path:out+'/'+name+'_'+width+'_cycles.png'});
   report.views.push({name,width,errors,blocked,initial});
   if(width===1360){
    await page.emulateMedia({media:'print'});
    await page.evaluate(()=>{window.dispatchEvent(new Event('beforeprint'));document.querySelectorAll('details').forEach(e=>e.open=true);});
    const print=await snapshot(page);
    await page.pdf({path:out+'/'+name+'.pdf',printBackground:true,preferCSSPageSize:true});
    report.print.push({name,panelVisible:print.panelVisible,graphs:print.graphs});
   }
   await page.close();
  }
 }
 const check=await browser.newPage({viewport:{width:1360,height:1100}});
 await check.route('**/*',r=>!['GET','HEAD'].includes(r.request().method())?r.abort():r.continue());
 await check.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});
 report.laterSnapshot=await snapshot(check);
 await browser.close();
 fs.writeFileSync(out+'/qa.json',JSON.stringify(report,null,2));
 console.log(JSON.stringify({views:report.views.map(v=>({name:v.name,width:v.width,errors:v.errors,blocked:v.blocked,panelCount:v.initial.panelCount,panelVisible:v.initial.panelVisible,graphs:v.initial.graphs,overflow:v.initial.documentWidth>v.initial.viewport,duplicateIds:v.initial.duplicateIds,brokenImages:v.initial.brokenImages,frozenClaim:v.initial.frozenClaim})),print:report.print}));
})().catch(e=>{console.error(e);process.exit(1)});

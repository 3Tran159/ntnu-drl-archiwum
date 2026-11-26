const fs=require('fs'),path=require('path');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029',D=R+'/local_workflow_ui_qa_20261030';fs.mkdirSync(D,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']});
 const context=await browser.newContext();let blocked=[];await context.route('**/*',route=>{if(!['GET','HEAD'].includes(route.request().method())){blocked.push({method:route.request().method(),url:new URL(route.request().url()).pathname});return route.abort();}return route.continue();});
 await context.addInitScript(()=>{const interval=window.setInterval;window.setInterval=(fn,ms,...a)=>ms>=10000?0:interval(fn,ms,...a);});
 const report={at:new Date().toISOString(),scope:'Read-only live HTTP QA; no action button clicks; non-GET requests blocked',views:[],blockedMutations:blocked};
 const w=await context.request.get('http://127.0.0.1:8771/api/workflow');const workflow=await w.json();
 report.workflow={http:w.status(),readiness:workflow.readiness,jobs:workflow.jobs?.length,files:workflow.files?.length,calmReady:!!workflow.calm};
 async function shot(page,locator,name){const loc=page.locator(locator).first();if(!await loc.count())return null;await loc.evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));await page.waitForTimeout(650);await page.screenshot({path:D+'/'+name+'.png'});return name+'.png';}
 for(const surface of ['operational','professor'])for(const width of[1920,1360,390]){
  const page=await context.newPage();await page.setViewportSize({width,height:1050});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8771/'+(surface==='operational'?'dashboard.html':'professor_dashboard.html'),{waitUntil:'domcontentloaded'});await page.waitForTimeout(1300);
  if(surface==='operational')await page.waitForFunction(()=>!document.querySelector('#lc-message').textContent.includes('Connecting'),{timeout:15000});
  const row=await page.evaluate(()=>{
   const panel=[...document.querySelectorAll('.wave-cycle-panel')].find(x=>x.getBoundingClientRect().width>0);
   const payload=panel?.querySelector('.wcp-history-data');let data={};try{data=JSON.parse(payload?.textContent||'{}')}catch{}
   const catalog=[...document.querySelectorAll('.wcc-panel')].find(x=>x.getBoundingClientRect().width>0);
   const violations=[];for(const td of catalog?.querySelectorAll('.wcc-definition,.wcc-record')||[]){const r=document.createRange();r.selectNodeContents(td);const b=td.getBoundingClientRect();for(const rect of r.getClientRects())if(rect.left<b.left-.8||rect.right>b.right+.8)violations.push(td.parentElement.cells[0].textContent);}
   const m=document.querySelector('#manual-control-panel');const buttons=m?[...m.querySelectorAll('button')].map(x=>({id:x.id,text:x.textContent,disabled:x.disabled})):[];
   return {overflow:document.documentElement.scrollWidth>innerWidth+1,docWidth:document.documentElement.scrollWidth,viewWidth:innerWidth,title:panel?.querySelector('h2')?.textContent,case:data.case,start:data.start,period:data.period,keys:Object.keys(data.series||{}),latest:Object.fromEntries(Object.entries(data.series||{}).map(([k,v])=>[k,v.at(-1)])),sideview:panel?[...panel.querySelectorAll('.wcp-side-view figcaption')].map(x=>x.textContent):[],arrivalPanels:panel?.querySelectorAll('.wave-arrival-panel,.wcp-arrival').length||0,catalogViolations:violations,controls:m?{message:document.querySelector('#lc-message').textContent,offlineHidden:document.querySelector('#lc-offline').hidden,current:document.querySelector('#lc-active').textContent,buttons,fileRows:document.querySelectorAll('#lc-files .lc-file').length,resultLink:m.querySelector('a[href="local_campaign_results.html"]')?.getAttribute('href')}:null,computerText:document.querySelector('#computer-status')?.innerText||'',figures:panel?.querySelectorAll('.wcp-history-plot svg').length||0};
  });
  Object.assign(row,{surface,width,errors});row.screenshots=[];
  if(surface==='operational')row.screenshots.push(await shot(page,'#computer-status',surface+'_'+width+'_resources'));
  row.screenshots.push(await shot(page,'.wave-cycle-panel',surface+'_'+width+'_case'));
  row.screenshots.push(await shot(page,'.wave-cycle-panel .wcp-window-block',surface+'_'+width+'_rolling'));
  row.screenshots.push(await shot(page,'.wave-cycle-panel .wcp-side-view',surface+'_'+width+'_field'));
  if(surface==='operational')row.screenshots.push(await shot(page,'#manual-control-panel',surface+'_'+width+'_controls'));
  row.screenshots.push(await shot(page,'.wcc-panel',surface+'_'+width+'_catalog'));
  if(width===1360){await page.emulateMedia({media:'print'});await page.pdf({path:D+'/'+surface+'_print.pdf',format:'A4',printBackground:true,margin:{top:'12mm',bottom:'12mm',left:'10mm',right:'10mm'}});row.print=surface+'_print.pdf';}
  report.views.push(row);await page.close();
 }
 const file=await context.newPage();await file.setViewportSize({width:1360,height:1050});await file.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard_work_20261030/dashboard.html',{waitUntil:'domcontentloaded'});await file.waitForTimeout(700);
 report.fileView=await file.evaluate(()=>({message:document.querySelector('#lc-message')?.textContent,offlineHidden:document.querySelector('#lc-offline')?.hidden,buttons:[...document.querySelectorAll('#manual-control-panel button')].map(x=>({text:x.textContent,disabled:x.disabled})),overflow:document.documentElement.scrollWidth>innerWidth+1}));
 await shot(file,'#manual-control-panel','file_readonly_controls');await file.close();
 const res=await context.request.get('http://127.0.0.1:8771/local_campaign_results.html');const body=await res.text();report.resultsLink={http:res.status(),title:(body.match(/<title>(.*?)<\/title>/s)||[])[1]||''};
 const rp=await context.newPage();await rp.setViewportSize({width:1360,height:1050});await rp.goto('http://127.0.0.1:8771/local_campaign_results.html',{waitUntil:'domcontentloaded'});await rp.screenshot({path:D+'/campaign_results_1360.png'});await rp.close();
 report.initialChecks={noMutationRequests:!blocked.length,noErrors:report.views.every(x=>!x.errors.length),correctViewportWidths:report.views.every(x=>x.width===x.viewWidth),noPageOverflow:report.views.every(x=>!x.overflow),catalogTextContained:report.views.every(x=>!x.catalogViolations.length),currentC01:report.views.every(x=>x.case==='C01_W20L4_M10_calm_settle_r2'&&x.period===null),fourPlots:report.views.every(x=>x.figures===4),readOnlyFile:report.fileView.buttons.every(x=>x.disabled)&&report.fileView.message.includes('Read-only'),resultsLink:res.status()===200};
 fs.writeFileSync(D+'/raw_review.json',JSON.stringify(report,null,2));console.log(JSON.stringify({workflow:report.workflow,checks:report.initialChecks,views:report.views.map(x=>({surface:x.surface,width:x.width,overflow:x.overflow,errors:x.errors,controls:x.controls?.message}))},null,2));
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});

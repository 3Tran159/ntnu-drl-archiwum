const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_live_final_qa_20261030';
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const report={updated_at:new Date().toISOString(),views:[],interactions:[],print:[],safety:'Only wave plot navigation was activated. All non-GET/HEAD requests blocked; no simulation controls pressed.'};
 const metrics=page=>page.evaluate(()=>{
  const vis=e=>e&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('details:not([open])');
  const panels=[...document.querySelectorAll('.wave-cycle-panel')].filter(vis),q=panels[0];
  const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);
  return {panelCount:panels.length,panelText:q?.innerText??'',graphCount:q?.querySelectorAll('svg').length??0,coefficientPlotCount:q?.querySelectorAll('.wcp-history-plot svg').length??0,
   viewState:q?.querySelector('.wcp-view-state')?.textContent,
   follow:q?.querySelector('[data-wcp-action="follow"]')?.getAttribute('aria-pressed'),
   phasePanel:!!q?.querySelector('.wcp-cycle-comparison'),deviationPanel:!!q?.querySelector('.wcp-deviations'),
   sideImages:q?[...q.querySelectorAll('img')].map(e=>({src:e.src.slice(0,100),width:e.naturalWidth,height:e.naturalHeight,complete:e.complete})):[],
   graphs:q?[...q.querySelectorAll('svg')].map(e=>({label:e.getAttribute('aria-label'),finite:!(/NaN|Infinity/.test(e.outerHTML)),polylines:e.querySelectorAll('polyline').length})):[],
   duplicateIds:[...new Set(ids.filter((x,i)=>ids.indexOf(x)!==i))],
   brokenImages:[...document.images].filter(e=>vis(e)&&(!e.complete||e.naturalWidth===0)).map(e=>e.src.slice(0,100)),
   pageOverflow:document.documentElement.scrollWidth>innerWidth,
   persisted:[...Object.keys(sessionStorage)].filter(k=>k.startsWith('wcp-view-')).map(k=>({key:k,value:JSON.parse(sessionStorage.getItem(k))}))
  };
 });
 for(const [name,url] of [['operational','http://127.0.0.1:8771/'],['professor','http://127.0.0.1:8771/professor_dashboard.html']]){
  for(const width of [1920,1360,390]){
   const page=await browser.newPage({viewport:{width,height:1100}}),errors=[],blocked=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',r=>{if(!['GET','HEAD'].includes(r.request().method())){blocked.push(r.request().method());return r.abort();}return r.continue();});
   await page.addInitScript(()=>{sessionStorage.setItem('ntnuRefresh','off');sessionStorage.setItem('professorRefresh','off');});
   await page.goto(url,{waitUntil:'networkidle'});
   await page.locator('.wave-cycle-panel .wcp-cycle-comparison').first().waitFor({state:'attached',timeout:10000});
   const initial=await metrics(page);
   await page.screenshot({path:out+'/'+name+'_'+width+'_overview.png'});
   const root=page.locator('.wave-cycle-panel').first();
   await root.screenshot({path:out+'/'+name+'_'+width+'_cycle_panel.png'});
   if(width===1360||width===390){
    await root.locator('[data-wcp-action="in"]').click();
    await root.locator('[data-wcp-action="left"]').click();
    const manual=await metrics(page);
    await page.reload({waitUntil:'networkidle'});
    const reloaded=await metrics(page);
    const root2=page.locator('.wave-cycle-panel').first();
    await root2.locator('[data-wcp-action="follow"]').click();
    const followed=await metrics(page);
    await root2.locator('[data-wcp-action="in"]').click();
    const svg=root2.locator('.wcp-history-plot svg').first();
    await svg.scrollIntoViewIfNeeded();
    const box=await svg.boundingBox();
    await page.mouse.move(box.x+140,box.y+120);await page.mouse.down();await page.mouse.move(box.x+190,box.y+120,{steps:5});await page.mouse.up();
    const dragged=await metrics(page);
    await svg.focus();await page.keyboard.press('Home');
    const keyboardFollowed=await metrics(page);
    report.interactions.push({name,width,manual:manual.persisted,reloaded:reloaded.persisted,manualView:manual.viewState,reloadedView:reloaded.viewState,
      persistedExactly:JSON.stringify(manual.persisted)===JSON.stringify(reloaded.persisted),
      followButton:followed.follow,followView:followed.viewState,dragFollow:dragged.follow,dragView:dragged.viewState,keyboardHomeFollow:keyboardFollowed.follow});
    await root2.locator('.wcp-history-plot').first().scrollIntoViewIfNeeded();
    await page.screenshot({path:out+'/'+name+'_'+width+'_history_viewport.png'});
   }
   report.views.push({name,width,errors,blocked,initial,final:await metrics(page)});
   if(width===1360){
    await page.emulateMedia({media:'print'});
    await page.evaluate(()=>{window.dispatchEvent(new Event('beforeprint'));document.querySelectorAll('details').forEach(e=>e.open=true);});
    report.print.push({name,metrics:await metrics(page)});
    await page.pdf({path:out+'/'+name+'.pdf',printBackground:true,preferCSSPageSize:true});
   }
   await page.close();
  }
 }
 await browser.close();fs.writeFileSync(out+'/qa.json',JSON.stringify(report,null,2));
 console.log(JSON.stringify({views:report.views.map(v=>({name:v.name,width:v.width,errors:v.errors,blocked:v.blocked,
  panels:v.initial.panelCount,coefficientPlots:v.initial.coefficientPlotCount,phase:v.initial.phasePanel,sideImages:v.initial.sideImages,
  overflow:v.initial.pageOverflow,duplicates:v.initial.duplicateIds,broken:v.initial.brokenImages})),interactions:report.interactions,print:report.print.map(p=>({name:p.name,panels:p.metrics.panelCount,plots:p.metrics.graphCount,sideImages:p.metrics.sideImages}))}));
})().catch(e=>{console.error(e);process.exit(1)});

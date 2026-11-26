const fs=require('fs'),{chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_live_final_qa_20261030';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),result=[];
 const snap=p=>p.evaluate(()=>{const root=[...document.querySelectorAll('.wave-cycle-panel')].find(e=>e.getBoundingClientRect().width>0),q=root.querySelectorAll('.wcp-history-plot');return {follow:root.querySelector('[data-wcp-action="follow"]').getAttribute('aria-pressed'),window:root.querySelector('.wcp-view-state').textContent,headline:root.querySelector('.wcp-status').textContent,eta:root.querySelector('.wcp-eta')?.innerText,plots:[...q].map(b=>{const el=b.querySelector('.wcp-plot-scroll'),s=b.querySelector('svg'),pl=s.querySelector('polyline'),r=el.getBoundingClientRect(),sr=s.getBoundingClientRect();let latest=null;if(pl){const pt=pl.points.getItem(pl.points.numberOfItems-1);latest=sr.x+pt.x*sr.width/620;}return{key:b.dataset.key,scroll:el.scrollLeft,max:el.scrollWidth-el.clientWidth,latestVisible:latest!==null&&latest>=r.left-.5&&latest<=r.right+.5}}),saved:Object.keys(sessionStorage).filter(k=>k.startsWith('wcp-view-')).map(k=>JSON.parse(sessionStorage.getItem(k))) };});
 for(const [name,url] of [['operational','http://127.0.0.1:8771/'],['professor','http://127.0.0.1:8771/professor_dashboard.html']])for(const width of [390,1360]){
  const page=await browser.newPage({viewport:{width,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>!['GET','HEAD'].includes(r.request().method())?r.abort():r.continue());
  await page.addInitScript(()=>sessionStorage.setItem('ntnuRefresh','off'));
  await page.goto(url,{waitUntil:'networkidle'});await page.waitForTimeout(120);
  const initial=await snap(page),root=page.locator('.wave-cycle-panel').first();
  await root.locator('[data-wcp-action="in"]').click();
  await page.evaluate(()=>document.querySelectorAll('.wave-cycle-panel:first-of-type .wcp-history-plot').forEach(()=>{}));
  await root.locator('.wcp-history-plot .wcp-plot-scroll').evaluateAll(els=>els.forEach((e,i)=>e.scrollLeft=i?83:41));
  await page.waitForTimeout(150);
  const manual=await snap(page);
  await root.locator('[data-wcp-action="left"]').click();await page.waitForTimeout(100);
  const panned=await snap(page);
  await page.reload({waitUntil:'networkidle'});await page.waitForTimeout(150);
  const reloaded=await snap(page);
  const root2=page.locator('.wave-cycle-panel').first();await root2.locator('[data-wcp-action="follow"]').click();await page.waitForTimeout(150);
  const followed=await snap(page);
  await page.reload({waitUntil:'networkidle'});await page.waitForTimeout(150);
  const followReloaded=await snap(page);
  if(width===390){await page.locator('.wave-cycle-panel').first().locator('.wcp-history-plot').first().scrollIntoViewIfNeeded();await page.screenshot({path:out+'/'+name+'_390_follow_right.png'});}
  result.push({name,width,errors,initial,manual,panned,reloaded,followed,followReloaded,
   manualScrollPreserved:JSON.stringify(manual.plots.map(p=>p.scroll))===JSON.stringify(panned.plots.map(p=>p.scroll))&&JSON.stringify(panned.plots.map(p=>p.scroll))===JSON.stringify(reloaded.plots.map(p=>p.scroll)),
   allLatestVisible:[initial,followed,followReloaded].every(s=>s.plots.every(p=>p.latestVisible&&Math.abs(p.scroll-p.max)<1))});
  await page.close();
 }
 await browser.close();fs.writeFileSync(out+'/mobile_follow_edge.json',JSON.stringify(result,null,2));
 console.log(JSON.stringify(result.map(r=>({name:r.name,width:r.width,errors:r.errors,manualScrollPreserved:r.manualScrollPreserved,allLatestVisible:r.allLatestVisible,initial:r.initial.plots,reloaded:r.reloaded.plots,headline:r.initial.headline,eta:r.initial.eta}))));
})().catch(e=>{console.error(e);process.exit(1)});

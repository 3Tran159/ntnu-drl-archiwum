const fs = require('fs');
const {chromium} = require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out = 'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/manual_panel_qa_20261030';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const result={updated_at:new Date().toISOString(),views:[],safety:'Working copy only; no controls pressed; non-GET/HEAD requests blocked.'};
 for (const width of [1360,390]) {
  const page=await browser.newPage({viewport:{width,height:1100}});
  const errors=[],blocked=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>{if(!['GET','HEAD'].includes(r.request().method())){blocked.push(r.request().method());return r.abort();}return r.continue();});
  await page.addInitScript(()=>sessionStorage.setItem('ntnuRefresh','off'));
  await page.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('#computer-status')?.innerText.includes('Historical no-foil diagnostic (R14)'),{timeout:10000});
  await page.locator('#computer-status').screenshot({path:out+'/final_status_'+width+'.png'});
  const metrics=await page.evaluate(()=>({
    status:document.querySelector('#computer-status')?.innerText,
    bodyPrefix:document.body.innerText.slice(0,8000),
    disabledButtons:Array.from(document.querySelectorAll('#manual-control-panel button')).map(e=>({text:e.textContent.trim(),disabled:e.disabled})),
    pageWidth:document.documentElement.scrollWidth,
    viewport:innerWidth
  }));
  result.views.push({width,errors,blocked,metrics});
  if(width===1360){
   await page.emulateMedia({media:'print'});
   await page.evaluate(()=>window.dispatchEvent(new Event('beforeprint')));
   await page.pdf({path:out+'/final_print_first_page.pdf',printBackground:true,preferCSSPageSize:true,pageRanges:'1'});
  }
  await page.close();
 }
 fs.writeFileSync(out+'/final_label_recheck.json',JSON.stringify(result,null,2));
 await browser.close();
 console.log(JSON.stringify(result.views.map(v=>({width:v.width,errors:v.errors,blocked:v.blocked,statusHistorical:v.metrics.status.includes('Historical no-foil diagnostic (R14)'),historicalReview:v.metrics.status.includes('Review of that historical no-foil diagnostic'),pageWidth:v.metrics.pageWidth,viewport:v.metrics.viewport,currentText:v.metrics.bodyPrefix.slice(v.metrics.bodyPrefix.indexOf('Paused — computed'),v.metrics.bodyPrefix.indexOf('LOCAL SIMULATION CONTROL'))}))));
})().catch(e=>{console.error(e);process.exit(1)});

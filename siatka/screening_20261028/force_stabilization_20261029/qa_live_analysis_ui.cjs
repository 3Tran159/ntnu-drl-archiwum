const fs=require('fs'),path=require('path');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029',B=path.dirname(R),O=R+'/live_analysis_ui_qa_20261030';
fs.mkdirSync(O,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});let results=[],posts=[];
for(const name of ['dashboard','professor_dashboard']) for(const width of [1920,1360,390]){
 const page=await browser.newPage({viewport:{width,height:1000}});let errors=[];
 page.on('pageerror',e=>errors.push(String(e)));await page.route('**/*',r=>{if(!['GET','HEAD'].includes(r.request().method())){posts.push(r.request().url());return r.abort()}return r.continue()});
 await page.goto('http://127.0.0.1:8771/'+name+'.html',{waitUntil:'domcontentloaded'});await page.waitForTimeout(1100);
 await page.evaluate(()=>{document.querySelectorAll('meta[http-equiv="refresh"]').forEach(x=>x.remove());document.querySelectorAll('[data-stage]')[0].click()});
 const live=page.locator('main #live-analysis').first();await live.waitFor();
 await page.screenshot({path:O+'/'+name+'_'+width+'_top.png'});
 await live.screenshot({path:O+'/'+name+'_'+width+'_idle.png'});
 const checks=await live.evaluate(el=>({active:el.dataset.active,plots:el.querySelectorAll('.wcp-history-plot').length,images:el.querySelectorAll('img').length,text:el.innerText,buckets:el.querySelectorAll('.live-empty-grid>section').length}));
 const archive=page.locator('main #case-archive').first();
 await archive.screenshot({path:O+'/'+name+'_'+width+'_archive_closed.png'});
 const closed=await archive.locator('details').evaluateAll(ds=>ds.every(d=>!d.open));
 await page.locator('main #local-controls').evaluate(el=>el.open=true);await page.waitForTimeout(500);
 await page.locator('main #manual-control-panel').screenshot({path:O+'/'+name+'_'+width+'_controls.png'});
 const controls=await page.locator('main #manual-control-panel').evaluate(el=>({text:el.innerText,buttons:[...el.querySelectorAll('button')].map(b=>({text:b.textContent.trim(),disabled:b.disabled}))}));
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
 await page.locator('main #local-controls').evaluate(el=>el.open=false);
 await page.locator('main [data-stage="mesh"]').click();await page.waitForTimeout(700);
 const meshPresent=await page.locator('#mesh-study-current').count()>0;
 await page.locator('main [data-stage-panel="mesh"]').screenshot({path:O+'/'+name+'_'+width+'_mesh.png'});
 await page.locator('main [data-stage="waves"]').click();
 if(width===1360){await page.emulateMedia({media:'print'});await page.pdf({path:O+'/'+name+'_print.pdf',format:'A4',printBackground:true});}
 results.push({name,width,checks,closed,overflow,errors,meshPresent,controls});
 await page.close();
}
const page=await browser.newPage();let docs=[];
for(const item of ['standalone_control_guide.html','chat_rescue.html','local_campaign_results.html','archive_runs/C01_W20L4_M10_calm_settle_r2.html']){const r=await page.request.get('http://127.0.0.1:8771/'+item);docs.push({path:item,status:r.status()});}
await browser.close();
const pass=results.every(r=>r.checks.active==='false'&&r.checks.plots===0&&r.checks.images===0&&r.checks.buckets===6&&r.closed&&!r.overflow&&!r.errors.length&&r.meshPresent)&&posts.length===0;
fs.writeFileSync(O+'/review.json',JSON.stringify({generated_at:new Date().toISOString(),pass,results,docs,posts},null,2));console.log(JSON.stringify({pass,views:results.length,docs,errors:results.map(r=>({name:r.name,width:r.width,overflow:r.overflow,errors:r.errors}))}));})().catch(e=>{console.error(e);process.exit(1)});

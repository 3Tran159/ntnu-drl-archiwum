const fs=require('fs'),path=require('path');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029',B=path.dirname(R),D=path.join(R,'w01a_transition_qa_20261030');fs.mkdirSync(D,{recursive:true});
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
let results=[];
for(const surface of ['operational','professor'])for(const width of [1920,1360,390]){
 const context=await browser.newContext({viewport:{width,height:1000}});
 await context.route('**/*',r=>['GET','HEAD'].includes(r.request().method())?r.continue():r.abort());
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8771/'+(surface==='professor'?'professor_dashboard.html':''),{waitUntil:'networkidle'});
 await page.locator('.wave-cycle-panel').first().evaluate(e=>{let p=e.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}});
 await page.waitForTimeout(100);
 const data=await page.locator('.wave-cycle-panel').first().evaluate(e=>{const d=JSON.parse(e.querySelector('.wcp-history-data').textContent);return {title:e.querySelector('h2').textContent,status:e.querySelector('.wcp-status').textContent,case:d.case,period:d.period,start:d.start,points:d.series.CD.length,min_time:d.series.CD[0]?.[0],max_time:d.series.CD.at(-1)?.[0],eta:e.querySelectorAll('.wcp-eta').length,phase_panels:e.querySelectorAll('.wcp-cycle-comparison').length,old_case:e.textContent.includes('W01_W20L4_M10_FS020_cycles_r2'),old_restart:e.textContent.includes('0.168'),side_waiting:!!e.querySelector('.wcp-side-waiting'),side_caption:e.querySelector('.wcp-side-view figcaption')?.textContent||null}});
 const dom=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,broken_images:[...document.images].filter(x=>!x.complete||x.naturalWidth===0).length,duplicate_ids:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i)}));
 await page.screenshot({path:path.join(D,surface+'_'+width+'_overview.png')});
 await page.locator('.wave-cycle-panel').first().screenshot({path:path.join(D,surface+'_'+width+'_panel.png')});
 if(width===1360){await page.emulateMedia({media:'print'});await page.pdf({path:path.join(D,surface+'_print_first5.pdf'),preferCSSPageSize:true,printBackground:true,pageRanges:'1-5'});}
 results.push({surface,width,...data,...dom,errors});await context.close();
}
const context=await browser.newContext({viewport:{width:1360,height:1000}});const page=await context.newPage();
for(const width of [1360,390]){await page.setViewportSize({width,height:1000});await page.goto('file:///'+B+'/campaign_results.html',{waitUntil:'load'});await page.screenshot({path:path.join(D,'campaign_'+width+'.png'),fullPage:true});results.push({surface:'campaign',width,...await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,rows:document.querySelectorAll('tbody tr').length,unarmed:document.body.innerText.includes('UNARMED'),failure_time:document.body.innerText.includes('1.064'),table_headers:[...document.querySelectorAll('th')].map(e=>e.textContent),body_excerpt:document.body.innerText.slice(0,1400)}))});}
await page.setViewportSize({width:1360,height:1000});await page.pdf({path:path.join(D,'campaign_print.pdf'),preferCSSPageSize:true,printBackground:true});
await context.close();await browser.close();
fs.writeFileSync(path.join(D,'qa.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results.map(x=>({surface:x.surface,width:x.width,case:x.case,title:x.title,points:x.points,period:x.period,start:x.start,eta:x.eta,phase:x.phase_panels,old:x.old_case,overflow:x.overflow,errors:x.errors,unarmed:x.unarmed,rows:x.rows})),null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
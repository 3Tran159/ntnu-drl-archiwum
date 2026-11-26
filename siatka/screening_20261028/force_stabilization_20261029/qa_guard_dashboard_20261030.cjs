const fs=require('fs'),{chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_live_final_qa_20261030';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),rows=[];
 for(const [name,url] of [['operational','http://127.0.0.1:8771/'],['professor','http://127.0.0.1:8771/professor_dashboard.html']])for(const width of [1920,1360,390]){
  const page=await browser.newPage({viewport:{width,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>!['GET','HEAD'].includes(r.request().method())?r.abort():r.continue());
  await page.addInitScript(()=>sessionStorage.setItem('ntnuRefresh','off'));
  await page.goto(url,{waitUntil:'networkidle'});
  for(let i=0;i<8;i++){if(await page.locator('.wave-cycle-panel .wcp-status').first().innerText().then(t=>t.includes('Stopped by physical stability guard')))break;await page.waitForTimeout(3000);await page.reload({waitUntil:'networkidle'});}
  const m=await page.evaluate(()=>{const root=document.querySelector('.wave-cycle-panel'),vis=e=>e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0&&!e.closest('details:not([open])');return {headline:root.querySelector('.wcp-status').innerText,failure:root.querySelector('.wcp-failure')?.innerText,meta:root.querySelector('.wcp-meta')?.innerText,etaCount:root.querySelectorAll('.wcp-eta').length,sideCaption:root.querySelector('.wcp-side-view figcaption')?.innerText,topStatus:document.querySelector('#computer-status')?.innerText,overflow:document.documentElement.scrollWidth>innerWidth,broken:[...document.images].filter(e=>vis(e)&&(!e.complete||!e.naturalWidth)).length,activeClaim:root.innerText.includes('GPU calculation active')};});
  await page.screenshot({path:out+'/'+name+'_'+width+'_guard_overview.png'});
  await page.evaluate(()=>{const r=document.querySelector('.wave-cycle-panel');window.scrollTo(0,r.getBoundingClientRect().top+scrollY-65);});
  await page.screenshot({path:out+'/'+name+'_'+width+'_guard_panel.png'});
  rows.push({name,width,errors,...m});
  if(width===1360){await page.emulateMedia({media:'print'});await page.evaluate(()=>{window.dispatchEvent(new Event('beforeprint'));document.querySelectorAll('details').forEach(e=>e.open=true);});await page.pdf({path:out+'/'+name+'_guard_print_first7.pdf',printBackground:true,preferCSSPageSize:true,pageRanges:'1-7'});}
  await page.close();
 }
 await browser.close();fs.writeFileSync(out+'/guard_recheck.json',JSON.stringify(rows,null,2));console.log(JSON.stringify(rows));
})().catch(e=>{console.error(e);process.exit(1)});

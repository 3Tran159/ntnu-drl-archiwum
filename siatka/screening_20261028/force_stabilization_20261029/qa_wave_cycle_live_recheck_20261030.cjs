const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/wave_cycle_integrated_qa_20261030';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:390,height:1100}});
 await page.route('**/*',r=>!['GET','HEAD'].includes(r.request().method())?r.abort():r.continue());
 await page.goto('http://127.0.0.1:8771/',{waitUntil:'networkidle'});
 const values=await page.evaluate(()=>{
   const p=document.querySelector('.wave-cycle-panel');
   const values={time:p.querySelector('.wcp-stat b')?.textContent,pointCount:p.querySelector('polyline')?.getAttribute('points').trim().split(/\s+/).length,text:p.innerText,scrollRegions:[...p.querySelectorAll('.wcp-plot-scroll,.wcp-scroll')].map(e=>({width:e.clientWidth,content:e.scrollWidth,overflow:getComputedStyle(e).overflowX}))};
   window.scrollTo(0,p.getBoundingClientRect().top+scrollY-70);
   return values;
 });
 await page.waitForTimeout(200);
 await page.screenshot({path:out+'/live_mobile_first_fold.png'});
 await page.evaluate(()=>{const h=[...document.querySelectorAll('.wave-cycle-panel h3')].find(x=>x.textContent==='Total force history');window.scrollTo(0,h.getBoundingClientRect().top+scrollY-70);});
 await page.waitForTimeout(200);
 await page.screenshot({path:out+'/live_mobile_forces.png'});
 await page.evaluate(()=>document.querySelectorAll('.wcp-plot-scroll,.wcp-scroll').forEach(e=>e.scrollLeft=e.scrollWidth));
 await page.screenshot({path:out+'/live_mobile_forces_scrolled_right.png'});
 fs.writeFileSync(out+'/live_recheck.json',JSON.stringify(values,null,2));
 console.log(JSON.stringify(values));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});

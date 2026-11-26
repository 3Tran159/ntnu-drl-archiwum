const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const checks=[];
 for(const width of [1360,390]){
  const page=await browser.newPage({viewport:{width,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');
  await page.locator('#refreshToggle').click();
  await page.locator('#mesh-force-cost img').scrollIntoViewIfNeeded();
  await page.locator('#mesh-force-cost').screenshot({path:root+'force_cost_'+width+'.png'});
  const data=await page.evaluate(()=>{
   const plot=document.querySelector('#mesh-force-cost img');
   const rows=[...document.querySelectorAll('#mesh-cost-table tbody tr')];
   return {overflow:document.documentElement.scrollWidth>innerWidth+1,plotLoaded:plot.complete&&plot.naturalWidth>0,meshes:rows.map(r=>r.cells[0].textContent),headers:[...document.querySelectorAll('#mesh-pair-comparison th')].map(e=>e.textContent),pending:document.querySelector('#mesh-force-cost').classList.contains('pending'),downloadCount:document.querySelectorAll('#mesh-selection a[download]').length};
  });
  await page.locator('#mesh-force-cost img').click();
  data.zoomOpened=await page.locator('#imageViewer').isVisible();
  await page.locator('#closeImage').click();
  if(width===1360){
   const event=page.waitForEvent('download');
   await page.getByRole('link',{name:'Download comparison CSV',exact:true}).click();
   const download=await event;await download.saveAs(root+'force_cost_download_check.csv');
   data.csvMatches=fs.readFileSync(root+'force_cost_download_check.csv','utf8')===fs.readFileSync(root+'mesh_force_cost.csv','utf8');
  }
  checks.push({width,...data,errors});
  await page.close();
 }
 await browser.close();
 fs.writeFileSync(root+'force_cost_qa.json',JSON.stringify(checks,null,2));
 console.log(JSON.stringify(checks));
 if(checks.some(c=>c.overflow||!c.plotLoaded||c.pending||c.errors.length||!c.zoomOpened||c.downloadCount!==2||c.csvMatches===false||!c.headers.includes('Δ Fx, pressure')||!c.headers.includes('Δ Fx, viscous')))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});

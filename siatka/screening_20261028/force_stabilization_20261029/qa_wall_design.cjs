const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const checks=[];
 for(const width of [1360,390]){
  const p=await b.newPage({viewport:{width,height:1000}});const errors=[];p.on('pageerror',e=>errors.push(String(e)));
  await p.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');
  await p.evaluate(()=>sessionStorage.setItem('ntnuRefresh','off'));
  const card=p.locator('#prism-design');await card.scrollIntoViewIfNeeded();
  await card.screenshot({path:root+'prism_design_'+width+'.png'});
  const data=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,rows:[...document.querySelectorAll('#prism-design tbody tr')].map(r=>[...r.cells].map(c=>c.textContent)),costMeshes:[...document.querySelectorAll('#mesh-cost-table tbody tr')].map(r=>r.cells[0].textContent),evidence:!!JSON.parse(document.getElementById('evidence').textContent).wall_design_review}));
  await card.locator('summary').click();
  data.assumptionVisible=await card.getByText('assumed μ = 0.001 Pa·s',{exact:true}).isVisible();
  checks.push({width,...data,errors});await p.close();
 }
 await b.close();fs.writeFileSync(root+'wall_design_qa.json',JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));
 if(checks.some(c=>c.overflow||c.errors.length||!c.assumptionVisible||!c.evidence||c.rows.length!==3||!c.costMeshes.includes('M06')))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});

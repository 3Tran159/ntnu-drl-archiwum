const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const out=[];
 for(const width of [1360,390]){
  const p=await b.newPage({viewport:{width,height:1100}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
  await p.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');
  await p.locator('#refreshToggle').click();await p.locator('#mesh-parameters').scrollIntoViewIfNeeded();
  await p.locator('#mesh-parameters').screenshot({path:root+'mesh_matrix_'+width+'.png'});
  const row=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,meshes:[...document.querySelectorAll('#mesh-parameters thead th')].slice(1).map(e=>e.textContent),rows:[...document.querySelectorAll('#mesh-parameters tbody th')].map(e=>e.textContent),units:[...document.querySelectorAll('#mesh-parameters tbody tr')].find(e=>e.textContent.includes('First full layer')).textContent,insideMesh:!!document.querySelector('#mesh #mesh-parameters'),source:!!JSON.parse(document.getElementById('evidence').textContent).mesh_budget_cfl}));
  await p.locator('#mesh-optimization summary').click();const img=p.locator('#mesh-optimization img');await img.scrollIntoViewIfNeeded();
  row.budgetImageLoaded=await img.evaluate(e=>e.complete&&e.naturalWidth>0);
  out.push({width,...row,errors});await p.close();
 }
 await b.close();fs.writeFileSync(root+'mesh_matrix_qa.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out));
 if(out.some(x=>x.overflow||x.errors.length||!x.insideMesh||!x.source||!x.budgetImageLoaded||x.meshes.join(',')!=='M02,M03,M04,M05,M06,M07,M08'||!x.rows.includes('Interface convective CFL · latest')))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});

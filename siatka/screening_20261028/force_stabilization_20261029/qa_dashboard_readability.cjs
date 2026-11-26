const fs=require('fs'),{fileURLToPath}=require('url');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});const out=[];
 for(const width of [1360,390]){
  const p=await b.newPage({viewport:{width,height:1100}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
  await p.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>window.copiedSimulationPath=text},configurable:true}));
  await p.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');await p.locator('#refreshToggle').click();
  const links=await p.locator('#overview .local-sim-link').evaluateAll(els=>els.map(e=>({mesh:e.dataset.simMesh,href:e.href,title:e.title})));
  const pathsExist=links.length===7&&links.every(x=>fs.existsSync(fileURLToPath(x.href))&&x.href.endsWith('/final.sim'));
  await p.locator('#overview .copy-sim-path').first().click();const copied=await p.evaluate(()=>window.copiedSimulationPath===document.querySelector('#overview .copy-sim-path').dataset.copySim);
  await p.locator('#overview').screenshot({path:R+'overview_sim_links_'+width+'.png'});
  const matrix=await p.evaluate(()=>({sameRows:[...document.querySelectorAll('#mesh-parameters tbody tr')].filter(r=>new Set([...r.querySelectorAll('td')].map(e=>e.textContent)).size===1).map(r=>r.querySelector('th').textContent),boxRows:[...document.querySelectorAll('#mesh-parameters tbody th')].filter(e=>e.textContent.toLowerCase().includes('box')).map(e=>e.textContent),overflow:document.documentElement.scrollWidth>innerWidth+1,shared:!!document.querySelector('#shared-mesh-settings')}));
  await p.locator('#mesh-parameters').screenshot({path:R+'mesh_matrix_readability_'+width+'.png'});
  await p.locator('#shared-mesh-settings summary').click();await p.locator('#shared-mesh-settings').screenshot({path:R+'shared_settings_'+width+'.png'});
  const units=await p.locator('#mesh-definition-change').evaluate(e=>e.innerText.includes('1.531 µm')&&e.innerText.includes('48 layers'));
  out.push({width,pathsExist,copied,links,matrix,units,errors});await p.close();
 }
 await b.close();fs.writeFileSync(R+'dashboard_readability_sim_links_qa.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out.map(({links,...a})=>a)));
 if(out.some(a=>!a.pathsExist||!a.copied||a.matrix.sameRows.length||a.matrix.boxRows.length||a.matrix.overflow||!a.matrix.shared||!a.units||a.errors.length))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});

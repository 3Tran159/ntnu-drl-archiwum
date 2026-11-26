const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});const out=[];
 for(const width of [1360,390]){
  const p=await b.newPage({viewport:{width,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
  await p.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');await p.locator('#refreshToggle').click();
  const legend=p.locator('#cdChart .series-label[data-force-mesh="M08"]');await legend.hover();
  const dimmed=await p.evaluate(()=>[...document.querySelectorAll('#forceExplorer .measured-line')].every(e=>e.dataset.mesh==='M08'?+e.style.opacity===1:+e.style.opacity===.12));
  await p.locator('#cdChart').screenshot({path:R+'force_hover_'+width+'.png'});
  await p.locator('#cdChart h3').hover();
  const restored=await p.evaluate(()=>[...document.querySelectorAll('#forceExplorer .measured-line')].every(e=>+e.style.opacity===1));
  await legend.click();await p.locator('#cdChart h3').hover();
  const pinned=await p.evaluate(()=>document.querySelector('#clChart .measured-line[data-mesh="M07"]').style.opacity==='.12'||+document.querySelector('#clChart .measured-line[data-mesh="M07"]').style.opacity===.12);
  await legend.focus();await legend.press('Escape');
  await p.locator('#mesh-selection .grid2').screenshot({path:R+'convergence_labels_'+width+'.png'});
  const collision=await p.evaluate(()=>[...document.querySelectorAll('#mesh-selection .grid2 svg')].map(svg=>{
   const rr=[...svg.querySelectorAll('[data-mesh-label]')].map(e=>({id:e.dataset.meshLabel,b:e.getBoundingClientRect()}));
   const bad=[];for(let i=0;i<rr.length;i++)for(let j=i+1;j<rr.length;j++){const a=rr[i].b,b=rr[j].b;if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)bad.push([rr[i].id,rr[j].id]);}return bad;
  }).flat());
  await p.locator('#mesh-definition-change').screenshot({path:R+'mesh_definition_change_'+width+'.png'});
  const definitions=await p.evaluate(()=>({rows:[...document.querySelectorAll('#mesh-parameters tbody th')].map(e=>e.textContent),delta:document.querySelector('#mesh-definition-change').innerText,overflow:document.documentElement.scrollWidth>innerWidth+1}));
  out.push({width,dimmed,restored,pinned,collision,errors,overflow:definitions.overflow,definitionRowsPresent:definitions.rows.includes('Foil surface target [mm]')&&definitions.rows.includes('Outer base size [mm]'),deltaPresent:definitions.delta.includes('+40.0%')&&definitions.delta.includes('Unchanged')});await p.close();
 }
 await b.close();fs.writeFileSync(R+'chart_interaction_definition_qa.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out));
 if(out.some(x=>!x.dimmed||!x.restored||!x.pinned||x.collision.length||x.errors.length||x.overflow||!x.definitionRowsPresent||!x.deltaPresent))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});

const fs=require('fs');const{chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029',O=R+'/mesh_pause_controls_qa';fs.mkdirSync(O,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const results=[];
for(const name of ['dashboard','professor_dashboard'])for(const width of [1920,1360,390]){
 const page=await browser.newPage({viewport:{width,height:950}});let errors=[],posts=[],fake=null;
 page.on('pageerror',e=>errors.push(String(e)));
 await page.route('**/api/mesh-study',r=>fake?r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fake)}):r.continue());
 await page.route('**/api/mesh-study/*',async r=>{
  if(r.request().method()!=='POST')return r.continue();
  const action=r.request().url().split('/').pop();posts.push({action,payload:r.request().postDataJSON()});
  fake={status:action==='pause'?'paused':'running',can_pause:action!=='pause',can_resume:action==='pause',generation:action==='pause'?'mock-saved':'mock-running',job:'M12 test fixture',message:action==='pause'?'Paused and saved at 1.2000 s.':'Mesh study is running.',file:action==='pause'?'E:/fixture/final.sim':undefined};
  return r.fulfill({status:202,contentType:'application/json',body:JSON.stringify({message:'Mock action accepted; production calculation untouched.'})});
 });
 await page.route('**/*',r=>['GET','HEAD'].includes(r.request().method())||r.request().url().includes('/api/mesh-study/')?r.fallback():r.abort());
 await page.goto('http://127.0.0.1:8771/'+name+'.html',{waitUntil:'domcontentloaded'});
 const panel=page.locator('main #mesh-run-controls'),pause=panel.locator('[data-mesh-action=pause]'),resume=panel.locator('[data-mesh-action=resume]');
 await pause.waitFor();await page.waitForFunction(()=>!document.querySelector('main #mesh-run-controls [data-mesh-action=pause]').disabled);
 const live=await panel.innerText();const initialResumeDisabled=await resume.isDisabled();
 await panel.screenshot({path:O+'/'+name+'_'+width+'_live.png'});
 await pause.click();await page.waitForFunction(()=>!document.querySelector('main #mesh-run-controls [data-mesh-action=resume]').disabled);
 const saved=await panel.innerText();await panel.screenshot({path:O+'/'+name+'_'+width+'_paused_fixture.png'});
 await resume.click();await page.waitForFunction(()=>!document.querySelector('main #mesh-run-controls [data-mesh-action=pause]').disabled);
 const noOverflow=await panel.evaluate(e=>e.scrollWidth<=e.clientWidth+1);
 if(width===1360){await page.emulateMedia({media:'print'});await page.pdf({path:O+'/'+name+'_print.pdf',format:'A4'});}
 results.push({name,width,live:live.includes('Mesh study is running'),initialResumeDisabled,saved:saved.includes('Paused and saved'),noOverflow,posts:posts.map(p=>({action:p.action,hasGeneration:!!p.payload.generation})),errors});
 await page.close();
}
await browser.close();const pass=results.every(x=>x.live&&x.initialResumeDisabled&&x.saved&&x.noOverflow&&!x.errors.length&&x.posts.length===2&&x.posts.every(p=>p.hasGeneration));
fs.writeFileSync(O+'/review.json',JSON.stringify({pass,results,liveSolverActions:0,scope:'Actual GET status; intercepted mock POST pause/resume and saved-state responses; live CFD untouched.'},null,2));
console.log(JSON.stringify({pass,views:results.length,liveSolverActions:0,results}));
if(!pass)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});

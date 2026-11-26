const fs=require('fs'),assert=require('assert');
const {fileURLToPath}=require('url');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),out=[];
for(const width of [1360,390]){
 const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
 await p.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');await p.locator('#refreshToggle').click();await p.addStyleTag({content:'html{scroll-behavior:auto!important}'});
 const before=await p.evaluate(()=>({meshes:forceMeshes,lines:[...document.querySelectorAll('#forceExplorer .measured-line')].map(e=>e.dataset.mesh),hasM09:!!document.querySelector('[data-sim-mesh="M09"]'),link:document.querySelector('[data-sim-mesh="M09"]')?.href,overflow:document.documentElement.scrollWidth>innerWidth+1,panel:document.querySelector('#configured-mesh-live').innerText}));
 const lab=p.locator('#cdChart .series-label[data-force-mesh="M04"]');await lab.hover();
 const hover=await p.locator('#forceExplorer .measured-line').evaluateAll(els=>els.map(e=>({mesh:e.dataset.mesh,opacity:e.style.opacity})));
 assert(hover.filter(x=>x.mesh!=='M04').every(x=>x.opacity==='0.12'));assert(hover.filter(x=>x.mesh==='M04').every(x=>x.opacity==='1'));
 await lab.focus();await p.keyboard.press('Enter');await p.mouse.move(0,0);
 const pin=await lab.getAttribute('aria-pressed');assert.equal(pin,'true');await lab.focus();await p.keyboard.press('Escape');
 const restored=await p.locator('#forceExplorer .measured-line').evaluateAll(els=>els.every(e=>e.style.opacity==='1'));assert(restored);
 for(const range of ['startup','recent','continuation']){await p.locator('[data-force-range="'+range+'"]').click();assert(await p.locator('#forceExplorer .measured-line').count());}
 assert(!before.overflow);assert(before.hasM09);assert(before.link.startsWith('file:'));assert(fs.existsSync(fileURLToPath(before.link)));assert(!before.lines.includes('M09'));assert(!errors.length);
 out.push({width,...before,hoverPass:true,pinPass:pin==='true',escapePass:restored,errors});await p.close();
}
await b.close();fs.writeFileSync(R+'main_configured_force_qa.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out.map(x=>({width:x.width,meshes:x.meshes,lines:x.lines.length,m09SourceLinkExists:x.hasM09,noM09HistoricalCurve:!x.lines.includes('M09'),hoverPass:x.hoverPass,pinPass:x.pinPass,escapePass:x.escapePass,errors:x.errors,overflow:x.overflow}))));
})().catch(e=>{console.error(e);process.exitCode=1;});

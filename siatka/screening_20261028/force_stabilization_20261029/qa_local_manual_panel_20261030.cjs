const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029',O=R+'/manual_panel_qa_20261030';
fs.mkdirSync(O,{recursive:true});
function snapshot(){
 const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden',ids=[...document.querySelectorAll('[id]')].map(e=>e.id);
 const panel=document.querySelector('#manual-control-panel'),status=document.querySelector('#computer-status');
 const buttonInfo=e=>({text:e.innerText||e.getAttribute('aria-label')||e.type,disabled:e.disabled,bounds:{w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}});
 const overflow=[...document.querySelectorAll('body *')].filter(e=>{if(!visible(e)||e.closest('svg,.table-wrap,.table-scroll,.wave-data-table,.figure-scroll,.wave-pilot-scroll'))return false;const r=e.getBoundingClientRect();return r.right>innerWidth+2&&r.width>5}).map(e=>({tag:e.tagName,id:e.id,cls:String(e.className).slice(0,80),right:e.getBoundingClientRect().right,text:(e.innerText||'').slice(0,120)})).slice(0,15);
 return{title:document.title,viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,noPageOverflow:document.documentElement.scrollWidth<=innerWidth+2,overflow,duplicateIds:[...new Set(ids.filter((v,i)=>ids.indexOf(v)!==i))],buttons:[...document.querySelectorAll('button')].filter(visible).map(buttonInfo),panelButtons:panel?[...panel.querySelectorAll('button,input[type=button],input[type=submit]')].filter(visible).map(buttonInfo):[],panelText:panel?.innerText,statusText:status?.innerText,fields:panel?[...panel.querySelectorAll('input,select')].filter(e=>visible(e)&&e.type!=='hidden'&&e.type!=='password').map(e=>({type:e.type,disabled:e.disabled,label:e.labels?.[0]?.innerText||e.getAttribute('aria-label')||e.id})):[],brokenVisibleImages:[...document.images].filter(e=>visible(e)&&e.complete&&!e.naturalWidth).map(e=>e.alt),schematics:document.querySelectorAll('svg[viewBox="0 0 510 335"]').length,bodyText:document.body.innerText.slice(0,11000)};
}
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),report={updated_at:new Date().toISOString(),views:[],prints:[],safety:'Only working copies served on port8771. Read-only UI. All non-GET/HEAD requests blocked; no run controls pressed.'};
try{
 for(const surface of ['operational','professor']){
  const url='http://127.0.0.1:8771/'+(surface==='professor'?'professor_dashboard.html':'');
  for(const width of [1920,1360,390]){
   const c=await b.newContext({viewport:{width,height:1100},deviceScaleFactor:1}),p=await c.newPage(),errors=[],blocked=[];
   await c.route('**/*',route=>{const q=route.request();if(!['GET','HEAD'].includes(q.method())){blocked.push({method:q.method(),url:q.url().split('?')[0]});return route.abort('blockedbyclient');}return route.continue();});
   p.on('pageerror',e=>errors.push(e.message));await p.addInitScript(()=>sessionStorage.setItem('ntnuRefresh','off'));
   await p.goto(url,{waitUntil:'load'});await p.waitForTimeout(1500);
   await p.screenshot({path:O+'/'+surface+'_'+width+'_overview.png'});
   const panel=p.locator('#manual-control-panel');
   if(await panel.count()){await panel.evaluate(e=>{for(let x=e.parentElement;x;x=x.parentElement)if(x.tagName==='DETAILS')x.open=true;e.scrollIntoView({block:'start'});});await p.evaluate(()=>scrollBy(0,-75));}
   await p.waitForTimeout(300);const metrics=await p.evaluate(snapshot);
   await p.screenshot({path:O+'/'+surface+'_'+width+'_controls.png'});
   report.views.push({surface,width,errors,blocked,metrics});await c.close();
  }
  const c=await b.newContext({viewport:{width:1360,height:1100}}),p=await c.newPage();
  await c.route('**/*',r=>['GET','HEAD'].includes(r.request().method())?r.continue():r.abort('blockedbyclient'));
  await p.addInitScript(()=>sessionStorage.setItem('ntnuRefresh','off'));await p.goto(url,{waitUntil:'load'});await p.waitForTimeout(1000);
  await p.emulateMedia({media:'print'});await p.evaluate(()=>{window.dispatchEvent(new Event('beforeprint'));document.querySelectorAll('details').forEach(e=>e.open=true);document.querySelectorAll('img').forEach(e=>e.loading='eager');});
  const pdf=O+'/'+surface+'.pdf';await p.pdf({path:pdf,format:'A4',printBackground:true,preferCSSPageSize:true,margin:{top:'12mm',bottom:'12mm',left:'10mm',right:'10mm'}});
  report.prints.push({surface,pdf,metrics:await p.evaluate(snapshot)});await c.close();
 }
}finally{await b.close();fs.writeFileSync(O+'/qa.json',JSON.stringify(report,null,2));}
console.log(JSON.stringify({path:O+'/qa.json',views:report.views.map(x=>({surface:x.surface,width:x.width,errors:x.errors,blocked:x.blocked,overflow:!x.metrics.noPageOverflow,panelButtons:x.metrics.panelButtons,status:x.metrics.statusText?.slice(0,150)})),prints:report.prints.map(p=>({surface:p.surface,pdf:p.pdf}))},null,2));
})().catch(e=>{console.error(e.stack);process.exitCode=1});

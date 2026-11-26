const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
const url='file:///F:/ntnu/mesh_screening_20261028/professor_dashboard.html';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']});
 const out=[];
 for(const width of [1360,1920,390]){
  const p=await b.newPage({viewport:{width,height:1080}}),errors=[];
  p.on('pageerror',e=>errors.push(String(e)));
  await p.goto(url,{waitUntil:'load'});
  await p.addStyleTag({content:'html{scroll-behavior:auto!important}*{animation:none!important;transition:none!important}'});
  await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
  await p.screenshot({path:R+'prof_review_'+width+'_overview.png'});
  const info=await p.evaluate(()=>{
   const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
   return {title:document.title,width:innerWidth,documentWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,
    sections:[...document.querySelectorAll('section')].map(e=>({id:e.id,title:(e.querySelector('h2,h3')||e).textContent.slice(0,150),rect:rect(e)})),
    images:[...document.images].map(e=>({alt:e.alt,complete:e.complete,naturalWidth:e.naturalWidth,rect:rect(e)})),
    tables:[...document.querySelectorAll('table')].map(e=>({title:e.closest('section')?.querySelector('h2,h3')?.textContent,columns:e.querySelectorAll('thead tr:first-child th').length,rect:rect(e),parentWidth:e.parentElement.clientWidth,scroll:e.parentElement.scrollWidth>e.parentElement.clientWidth+1,font:getComputedStyle(e).fontSize})),
    smallText:[...document.querySelectorAll('td,th,p,li,figcaption,svg text')].filter(e=>parseFloat(getComputedStyle(e).fontSize)<12).slice(0,20).map(e=>({text:e.textContent.slice(0,70),font:getComputedStyle(e).fontSize})),
    invalidText:document.body.innerText.match(/\bNaN\b|\bundefined\b|@@\w+@@/g)||[],
    text:document.body.innerText.slice(0,22000)};
  });
  info.anchorPositions=[];
  for(const s of info.sections){if(!s.id)continue;const link=p.locator('nav a[href="#'+s.id+'"]');if(await link.count()){await link.click();await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));info.anchorPositions.push(await p.evaluate(id=>({id,top:document.getElementById(id).getBoundingClientRect().top,navBottom:document.querySelector('nav').getBoundingClientRect().bottom}),s.id));}}
  const hideNav=await p.addStyleTag({content:'nav{visibility:hidden!important}'});
  for(const s of info.sections){
   if(!s.id)continue;
   const el=p.locator('#'+s.id);
   await el.scrollIntoViewIfNeeded();await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   await el.screenshot({path:R+'prof_review_'+width+'_'+s.id.replace(/[^a-z0-9_-]/gi,'_')+'.png'});
  }
  if(width===390){
   const expand=p.getByRole('button',{name:/Expand figure/i}).first();
   info.modal={available:await expand.count()};
   if(info.modal.available){await expand.click();await p.screenshot({path:R+'prof_review_390_field_modal.png'});info.modal.open=await p.evaluate(()=>!!document.querySelector('dialog[open]'));await p.keyboard.press('Escape');info.modal.escapeClosed=await p.evaluate(()=>!document.querySelector('dialog[open]'));await expand.click();await p.getByRole('button',{name:/^Close/}).last().click();info.modal.closeButtonWorks=await p.evaluate(()=>!document.querySelector('dialog[open]'));}
   info.fieldWidths=await p.locator('#fields img').evaluateAll(els=>els.map(e=>({width:e.getBoundingClientRect().width,parentWidth:e.parentElement.clientWidth,parentScroll:e.parentElement.scrollWidth})));
  }
  out.push({...info,errors});
  if(width===1360){
   await p.emulateMedia({media:'print'});
   const printed=await p.evaluate(()=>({width:document.documentElement.scrollWidth,body:document.body.clientWidth,sections:[...document.querySelectorAll('section')].map(e=>({id:e.id,breakBefore:getComputedStyle(e).breakBefore,breakInside:getComputedStyle(e).breakInside})),tables:[...document.querySelectorAll('table')].map(e=>({width:e.getBoundingClientRect().width,parent:e.parentElement.clientWidth,overflow:e.parentElement.scrollWidth>e.parentElement.clientWidth+1}))}));
   await p.pdf({path:R+'professor_review_qa_final.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
   fs.writeFileSync(R+'professor_print_qa.json',JSON.stringify(printed,null,2));
  }
  await p.close();
 }
 const main=[];
 for(const width of [1360,390]){const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));await p.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');if(await p.locator('#refreshToggle').count())await p.locator('#refreshToggle').click();await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});await p.locator('#configured-mesh-live').scrollIntoViewIfNeeded();await p.locator('#configured-mesh-live').screenshot({path:R+'prof_review_main_'+width+'_configured.png'});main.push(await p.evaluate(()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,text:document.querySelector('#configured-mesh-live').innerText,rect:document.querySelector('#configured-mesh-live').getBoundingClientRect().toJSON()})));main[main.length-1].errors=errors;await p.close();}
 fs.writeFileSync(R+'main_configured_panel_qa.json',JSON.stringify(main,null,2));
 await b.close();fs.writeFileSync(R+'professor_readability_review.json',JSON.stringify(out,null,2));
 console.log(JSON.stringify(out.map(x=>({width:x.width,overflow:x.overflow,sections:x.sections.map(s=>s.id),tables:x.tables.map(t=>({section:t.title,scroll:t.scroll,font:t.font})),images:x.images.length,errors:x.errors,invalidText:x.invalidText,smallText:x.smallText}))));
})().catch(e=>{console.error(e);process.exitCode=1;});

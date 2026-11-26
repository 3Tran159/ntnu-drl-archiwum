const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),report=[];
for(const kind of ['main','professor'])for(const width of [1920,1360,390]){
 const p=await b.newPage({viewport:{width,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
 await p.goto('file:///F:/ntnu/mesh_screening_20261028/'+(kind==='main'?'dashboard.html':'professor_dashboard.html'));
 await p.addStyleTag({content:'html{scroll-behavior:auto!important}nav{visibility:hidden!important}'});
 await p.evaluate(()=>document.fonts.ready);
 const sel=kind==='main'?'#matched-endpoint-live':'#matched-endpoint-review';
 const panel=p.locator(sel);assert.equal(await panel.count(),1);
 await panel.scrollIntoViewIfNeeded();await panel.screenshot({path:R+'matched_endpoint_ui_'+kind+'_'+width+'.png'});
 const info=await panel.evaluate(e=>({text:e.innerText,overflow:document.documentElement.scrollWidth>innerWidth+1,duplicateIds:[...document.querySelectorAll('[id]')].map(x=>x.id).filter((x,i,a)=>a.indexOf(x)!==i),tables:[...e.querySelectorAll('table')].map(t=>({rows:t.rows.length,width:t.clientWidth,containerWidth:t.parentElement.clientWidth,headers:[...t.querySelectorAll('th')].map(x=>x.innerText)})),originalConfiguredPresent:!!document.querySelector('#configured-mesh-live')||document.querySelector('#meshes')?.innerText.includes('first passing pair')}));
 assert(!info.overflow);assert(!info.duplicateIds.length);assert(info.text.includes('residual time drift'));assert(info.text.includes('All three meshes are compared over 1.840–2.040 s at identical solver settings.'));assert(info.text.includes('1.840–2.040 s'));assert(info.text.includes('Second-order time · 1.000 ms · 10 inner iterations'));assert(info.originalConfiguredPresent);assert(!errors.length);
 if(width===390){assert(info.tables.length);assert(info.tables.every(t=>t.width>t.containerWidth));}
 const source=JSON.parse(fs.readFileSync(R+'matched_endpoint_results.json','utf8'));
 info.renderedPairRows=await panel.locator('.endpoint-table').last().locator('tbody tr').evaluateAll(rows=>rows.map(r=>[...r.cells].map(c=>c.innerText)));
 const fmtDelta=x=>(x>=0?'+':'')+x.toFixed(4)+'%';
 assert.equal(info.renderedPairRows.length,3);assert.equal(source.pairs.length,3);
 for(const pair of source.pairs){const row=info.renderedPairRows.find(r=>r[0]===pair.candidate+' / '+pair.reference);assert(row);assert.deepEqual(row.slice(1,5),['CD','CL_total','pressure_drag_N','viscous_drag_N'].map(k=>fmtDelta(pair.difference_pct[k])));assert.equal(row[5],pair.both_force_coefficients_within_1pct?'Within 1%':'Outside 1%');}
 info.commonWindowValuesMatchSource=true;
 if(kind==='professor'){info.headline=await p.locator('main>.decision').innerText();assert(info.headline.includes('M09: CD and CL are within 1% of M07, M08.'));if(!fs.existsSync(R+'selected_mesh_decision.json'))assert(info.headline.includes('Calm-template decision pending.'));if(width===1920)await p.locator('main>.decision').screenshot({path:R+'matched_endpoint_assessment_1920.png'});}
 const next=p.locator(kind==='main'?'#selected-mesh-time-live':'#selected-mesh-time-review');assert.equal(await next.count(),1);
 info.nextStageText=await next.innerText();const decisionPath=R+'selected_mesh_decision.json',decision=fs.existsSync(decisionPath)?JSON.parse(fs.readFileSync(decisionPath,'utf8')):{};
 if(decision.status!=='supported_calm_mesh_template')assert(info.nextStageText.includes('Time-step acceptance pending.'));
 await next.screenshot({path:R+'selected_time_ui_'+kind+'_'+width+'.png'});
 const wave=p.locator(kind==='main'?'#wave-preparation-live':'#waves .wave-preparation-status');
 const detail=wave.locator('.wave-pilot-details');assert.equal(await detail.count(),1);await detail.locator('summary').click();
 await detail.locator('img').evaluate(async i=>{i.loading='eager';await i.decode()});
 info.waveCaption=await detail.locator('img').getAttribute('alt');assert(info.waveCaption.includes('partial gauge traces'));assert(info.waveCaption.includes('not yet validated'));
 await detail.screenshot({path:R+'wave_gauge_ui_'+kind+'_'+width+'.png'});
 if(kind==='main'){await detail.locator('img').click();assert(await p.locator('#imageViewer').evaluate(e=>e.open));await p.locator('#closeImage').click();}
 else{await detail.locator('.expand-field').click();assert(await p.locator('#field-dialog').evaluate(e=>e.open));await p.keyboard.press('Escape');}
 assert(!(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)));
 if(kind==='professor'&&width===1360){
  await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));});
  await p.emulateMedia({media:'print'});info.intentionalPrintPages=await p.locator('.print-report .print-page').count();
  assert.equal(await p.locator('.print-report .matched-endpoint').count(),1);
  info.printEndpointPage=await p.locator('.print-report .print-page').evaluateAll(es=>1+es.findIndex(e=>e.querySelector('.matched-endpoint')));
  await p.pdf({path:R+'matched_endpoint_professor_qa.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
 }
 report.push({kind,width,...info,errors});await p.close();
}
await b.close();fs.writeFileSync(R+'matched_endpoint_dashboard_qa.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report.map(({kind,width,overflow,duplicateIds,tables,intentionalPrintPages,printEndpointPage,errors})=>({kind,width,overflow,duplicateIds,tables,intentionalPrintPages,printEndpointPage,errors}))));
})().catch(e=>{console.error(e);process.exit(1);});
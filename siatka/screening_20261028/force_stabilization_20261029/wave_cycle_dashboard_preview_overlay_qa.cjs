const fs=require('fs'),{chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029';
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']});
const result={updated_at:new Date().toISOString(),views:[],synthetic_fixtures_are_UI_only:true};
try{
for(const name of ['real','two','four','phase_drift']){
for(const width of [1920,1360,390]){
 const p=await browser.newPage({viewport:{width,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 const file=name==='real'?'wave_cycle_dashboard_preview.html':'wave_cycle_dashboard_preview_overlay_'+name+'.html';
 await p.goto('file:///'+R+'/'+file,{waitUntil:'load'});
 const box=p.locator('.wcp-cycle-comparison'),text=await box.innerText(),info=await p.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));
 const axes=await box.locator('.wcp-phase-plots svg').allTextContents();
 const legends=await box.locator('.wcp-legend span').allTextContents();
 const metrics=await box.locator('.wcp-deviation-table tbody tr').allTextContents();
 const checks={noJsErrors:!errors.length,noPageOverflow:info.scroll<=width+1,twoSeparatePhaseAxes:axes.length===2&&axes[0].includes('CD')&&axes[1].includes('CL, total'),fixedPhase:axes.every(x=>x.includes('0.00')&&x.includes('1.00')&&x.includes('Wave phase [0–1]')),noRealignment:text.includes('peaks are not realigned'),incompleteExcluded:text.includes('excluded from every deviation'),incompleteDashed:await box.locator('.wcp-phase-plots polyline[stroke-dasharray="7 5"]').count()===2,primaryFollowPreserved:(await p.locator('.wcp-view-state').innerText()).startsWith('Following latest')};
 if(name!=='real'){checks.rawDifferenceAxes=await box.locator('.wcp-delta-plots svg').count()===2;checks.exactUnits=text.includes('RMS ΔCD [–]')&&text.includes('Max |ΔCL| [–]');checks.expectedRows=metrics.length===(name==='four'?3:1);checks.originalNumbers=legends[0].startsWith('Cycle 2')&&legends.at(-1).includes('incomplete');}
 const screenshot=R+'/wave_cycle_dashboard_preview_overlay_'+name+'_'+width+'.png';
 await box.screenshot({path:screenshot});
 result.views.push({name,width,checks,legends,metricRows:metrics,screenshot,errors});
 if(name==='four'&&width===1360){
  await p.emulateMedia({media:'print'});
  const print={sectionBreak:await box.evaluate(e=>getComputedStyle(e).breakBefore),tableAvoid:await box.locator('.wcp-deviation-table').evaluate(e=>getComputedStyle(e).breakInside),deltaAvoid:await box.locator('.wcp-deviations').evaluate(e=>getComputedStyle(e).breakInside),controlsHidden:await p.locator('.wcp-nav').evaluate(e=>getComputedStyle(e).display==='none')};
  await box.screenshot({path:R+'/wave_cycle_dashboard_preview_overlay_print.png'});
  await p.pdf({path:R+'/wave_cycle_dashboard_preview_overlay_print.pdf',format:'A4',printBackground:true,margin:{top:'12mm',bottom:'12mm',left:'12mm',right:'12mm'}});
  result.print=print;
 }
 await p.close();
}}
result.pass=result.views.every(v=>Object.values(v.checks).every(Boolean))&&result.print.sectionBreak==='page'&&result.print.tableAvoid==='avoid'&&result.print.deltaAvoid==='avoid'&&result.print.controlsHidden;
fs.writeFileSync(R+'/wave_cycle_dashboard_preview_overlay_qa.json',JSON.stringify(result,null,2));console.log(JSON.stringify({pass:result.pass,failed:result.views.filter(v=>!Object.values(v.checks).every(Boolean)),print:result.print}));
}finally{await browser.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
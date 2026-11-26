const fs=require('fs');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029';
const source=fs.readFileSync(R+'/wave_case_catalog_preview.html','utf8');
const css='<style>.wave-cycle-panel td:not(:first-child){white-space:nowrap}.wave-cycle-panel th,.wave-cycle-panel td{font-size:13px}.wave-cycle-panel table{width:100%}</style>';
const fixture=source.replace('<main style="max-width:1500px;margin:auto">','<main class="wave-cycle-panel" style="max-width:1500px;margin:auto">').replace('</body>',css+'</body>');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']});
 const result={at:new Date().toISOString(),fixture:'Nested in .wave-cycle-panel with inherited nowrap rule after catalog styles',views:[]};
 async function inspect(page){return page.evaluate(()=>{
   const cells=[...document.querySelectorAll('.wcc-panel td.wcc-definition,.wcc-panel td.wcc-record')];
   const checks=cells.map(td=>{
    const r=document.createRange();r.selectNodeContents(td);const box=td.getBoundingClientRect();
    const rects=[...r.getClientRects()];const overflow=rects.filter(x=>x.left<box.left-.5||x.right>box.right+.5||x.top<box.top-.5||x.bottom>box.bottom+.5);
    return {case:td.parentElement.cells[0].innerText,column:td.className,whiteSpace:getComputedStyle(td).whiteSpace,width:box.width,lines:rects.length,overflow:overflow.length};
   });
   return {noPageOverflow:document.documentElement.scrollWidth<=innerWidth+1,textInsideCells:checks.every(x=>x.overflow===0),textWraps:checks.every(x=>x.whiteSpace==='normal'),checks,
    noRampCopy:document.body.innerText.includes('no height ramp or calm-force wait'),
    colCount:document.querySelectorAll('.wcc-panel col').length};
  });}
 for(const width of[1920,1360,390]){
  const page=await browser.newPage({viewport:{width,height:1100},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',x=>errors.push(x.message));await page.setContent(fixture);
  const data=await inspect(page);data.width=width;data.jsErrors=errors;
  data.screenshot=R+'/wave_case_catalog_wrapping_'+width+'.png';
  if(width===390){await page.locator('.wcc-scroll').evaluate(e=>{e.scrollLeft=e.scrollWidth});}
  await page.screenshot({path:data.screenshot,fullPage:true});result.views.push(data);await page.close();
 }
 const page=await browser.newPage({viewport:{width:794,height:1123}});await page.setContent(fixture);await page.emulateMedia({media:'print'});
 result.print=await inspect(page);await page.screenshot({path:R+'/wave_case_catalog_wrapping_print.png',fullPage:true});
 await page.pdf({path:R+'/wave_case_catalog_wrapping_print.pdf',format:'A4',margin:{top:'12mm',bottom:'12mm',left:'12mm',right:'12mm'},printBackground:true});
 result.pass=[...result.views,result.print].every(x=>x.noPageOverflow&&x.textInsideCells&&x.textWraps&&x.colCount===7&&x.noRampCopy)&&result.views.every(x=>!x.jsErrors.length);
 fs.writeFileSync(R+'/wave_case_catalog_wrapping_qa.json',JSON.stringify(result,null,2));
 console.log(JSON.stringify({pass:result.pass,views:result.views.map(x=>({width:x.width,noPageOverflow:x.noPageOverflow,textInsideCells:x.textInsideCells,textWraps:x.textWraps})),print:{noPageOverflow:result.print.noPageOverflow,textInsideCells:result.print.textInsideCells,textWraps:result.print.textWraps}},null,2));
 await browser.close();if(!result.pass)process.exitCode=1;
})();
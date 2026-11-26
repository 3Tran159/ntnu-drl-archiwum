const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{
const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--disable-gpu']}),p=await b.newPage({viewport:{width:1360,height:1080}}),errors=[];
p.on('pageerror',e=>errors.push(String(e)));
await p.goto('file:///F:/ntnu/mesh_screening_20261028/professor_dashboard.html');
await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;});
const screen=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,printReportDisplay:getComputedStyle(document.querySelector('.print-report')).display,duplicateIds:[...document.querySelectorAll('[id]')].map(e=>e.id).filter((v,i,a)=>a.indexOf(v)!==i)}));
await p.screenshot({path:R+'prof_release_overview.png'});
await p.emulateMedia({media:'print'});
const print=await p.evaluate(()=>({mainDisplay:getComputedStyle(document.querySelector('main')).display,navDisplay:getComputedStyle(document.querySelector('nav')).display,reportDisplay:getComputedStyle(document.querySelector('.print-report')).display,pages:[...document.querySelectorAll('.print-page')].map(e=>({heading:e.querySelector('h1,h2,h3')?.textContent,breakAfter:getComputedStyle(e).breakAfter,rect:e.getBoundingClientRect().toJSON(),overflow:e.scrollWidth>e.clientWidth+1})),images:[...document.querySelectorAll('.print-report img')].map(e=>({alt:e.alt,loaded:e.complete&&e.naturalWidth>0}))}));
assert(!screen.overflow);assert(!screen.duplicateIds.length);assert.equal(screen.printReportDisplay,'none');assert.equal(print.mainDisplay,'none');assert.equal(print.navDisplay,'none');assert.equal(print.pages.length,13);assert(print.images.every(x=>x.loaded));assert(!errors.length);
await p.pdf({path:R+'professor_review_qa_release.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
await b.close();
fs.writeFileSync(R+'professor_print_release_qa.json',JSON.stringify({screen,print,errors},null,2));
console.log(JSON.stringify({screen,printPages:print.pages.length,printHeadings:print.pages.map(x=>x.heading),images:print.images,errors}));
})().catch(e=>{console.error(e);process.exitCode=1;});

const fs=require('fs'),assert=require('assert');
const {chromium}=require('C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const R='F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/';
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),out=[];
for(const width of [1360,390]){const p=await b.newPage({viewport:{width,height:1100}}),errors=[];p.on('pageerror',e=>errors.push(String(e)));
await p.goto('file:///F:/ntnu/mesh_screening_20261028/dashboard.html');await p.locator('#refreshToggle').click();
await p.locator('#temporal-validation').screenshot({path:R+'temporal_original_reference_'+width+'.png'});
const state=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,rows:[...document.querySelectorAll('.temporal-reference-table tbody tr')].map(x=>x.innerText),live:document.querySelector('.temporal-baseline-note').innerText,data:JSON.parse(document.querySelector('#evidence').textContent).active_tests.original_comparison,headings:[...document.querySelectorAll('.temporal-reference-table thead th')].map(x=>x.innerText)}));
assert.equal(state.rows.length,5);assert(state.rows[0].includes('0.007308')&&state.rows[0].includes('0.317901'));
assert(state.rows[1].includes('-0.726')&&state.rows[1].includes('0.336'));assert(state.live.includes('Original M04'));
assert(state.headings.includes('CD vs original [%]')&&state.headings.includes('CL vs original [%]'));
assert(!state.overflow);assert(!errors.length);
const a=state.data.cases[0],base=state.data.baseline;
for(const k of ['CD','CL_total'])assert(Math.abs(a.difference_pct_vs_original[k]-100*(a.means[k]-base.means[k])/Math.abs(base.means[k]))<1e-12);
out.push({width,errors,overflow:state.overflow,rows:state.rows.length,baselineVisible:true,differencesCorrect:true,liveSummaryVisible:true});
await p.close();}
await b.close();fs.writeFileSync(R+'temporal_original_reference_qa.json',JSON.stringify(out,null,2));console.log(JSON.stringify(out));})().catch(e=>{console.error(e);process.exitCode=1});

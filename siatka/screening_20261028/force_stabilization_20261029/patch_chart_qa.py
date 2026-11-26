from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'force_explorer.js';s=p.read_text()
s=s.replace("const forceColours={M03:'#14796f',M02:'#c65928'};","const forceColours={M03:'#14796f',M02:'#c65928',M04:'#5267ad'};\nconst forceMeshes=Object.keys(evidence.histories).filter(m=>evidence.histories[m].length);")
s=s.replace("['M03','M02'].map(","forceMeshes.map(")
s=s.replace("let forceRange='continuation';","let forceRange='continuation';\ndocument.querySelector('[data-force-range=\"recent\"]').disabled=Math.min(...Object.values(forceRows).map(a=>a.at(-1).physical_time_s))<.6;")
p.write_text(s)
p=R/'dashboard_qa.cjs';s=p.read_text().replace('for(const i of document.images)','for(const i of document.querySelectorAll("figure img"))').replace('[...document.images]','[...document.querySelectorAll("figure img")]')
s=s.replace("const download=page.waitForEvent('download');","""const defaultStart=await page.locator('#cdChart path.measured-line').first().getAttribute('data-first-time');
 if(Number(defaultStart)<.199999)throw new Error('Startup spike not excluded from default view');
 const axisEnd=await page.locator('#cdChart path.measured-line').first().getAttribute('data-count');
 await page.locator('#forceExplorer').screenshot({path:path.join(r,'dashboard_forces_readable.png')});
 await page.getByRole('button',{name:'Full startup',exact:true}).click();
 const startupStart=await page.locator('#cdChart path.measured-line').first().getAttribute('data-first-time');
 if(Number(startupStart)>.002)throw new Error('Startup history missing');
 await page.getByRole('button',{name:'Continuation · from 0.2 s',exact:true}).click();
 await page.locator('#flow figure img').click();
 if(!(await page.locator('#imageViewer').evaluate(e=>e.open)))throw new Error('Image enlargement failed');
 await page.getByRole('button',{name:'Close ×',exact:true}).click();
 const download=page.waitForEvent('download');""")
s=s.replace("await narrow.screenshot","await narrow.locator('#forceExplorer').screenshot({path:path.join(r,'dashboard_forces_mobile.png')});\n await narrow.screenshot")
p.write_text(s)
print('Chart modes, M04 support and visual QA updated.')

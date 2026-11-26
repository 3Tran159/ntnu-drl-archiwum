from pathlib import Path
import json,re
R=Path(__file__).resolve().parent
p=R/'campaign_registry.json';d=json.loads(p.read_text());d['cases']=[x for x in d['cases'] if x['id'] in ['M02','M03','M04','M05']];p.write_text(json.dumps(d,indent=2))
p=R/'build_dashboard_en.py';s=p.read_text()
s=s.replace("for m in ['M03','M02','M04']:","for m in ['M03','M02','M04','M05']:")
s=s.replace("if m=='M04' and not j:status=","if m in ['M04','M05'] and not j:status=")
s=s.replace("(Q/'M04/measurement.json')","(Q/m/'measurement.json')").replace("read(Q/'M04/measurement.json',{})","read(Q/m/'measurement.json',{})")
s=s.replace("else 'Mesh ready')","else 'Ready for GPU')")
s=s.replace("templates={","from campaign_dashboard import sections\nmesh_section,settled_table=sections(live)\ntemplates={\n'@@CAMPAIGN_MESH@@':mesh_section,'@@SETTLED_TABLE@@':settled_table,")
old=re.search(r'<section id="mesh">.*?</section>',s,re.S)
if old:s=s[:old.start()]+s[old.end():]
s=s.replace('<section id="forces">','@@CAMPAIGN_MESH@@\n<section id="forces">')
s=s.replace('<div id="forceExplorer">','@@SETTLED_TABLE@@\n<div id="forceExplorer">')
s=s.replace('<a href="#overview">Overview</a><a href="#forces">Forces</a>','<a href="#overview">Overview</a><a href="#mesh">Mesh campaign</a><a href="#forces">Forces</a>')
s=s.replace('<a href="#mesh">Mesh evidence</a>','')
s=s.replace('<h2>Run status</h2><p>Completed snapshots and live continuation are kept separate to avoid comparing different physical times.</p>','<h2>Campaign status</h2><p>M02 and M03 are settled. M04 and M05 are prepared for the next GPU runs.</p>')
s=s.replace('<div class="card"><h3>Live continuation</h3>','<div class="callout"><b>Paused for transport.</b> M02/M03 solutions and flow fields are saved. Resume at home: M04 first, then M05. No new GPU calculation is running.</div>\n<div class="card"><h3>Run state and force settling</h3>')
s=s.replace('M03/M02 resume saved solutions; M04 starts on its new mesh.','M04/M05 start on their verified meshes.')
s=s.replace('M02 and M03 are kept','M02 and M03 are kept')
s=s.replace('<button class="btn" onclick="downloadHistory(\'M02\')">Download M02 history</button>','<button class="btn" onclick="downloadHistory(\'M02\')">Download M02 history</button>')
# Keep startup-only material out of the main comparison.
s=s.replace('<div class="card" style="margin-top:18px"><h3>Archived startup comparison · t = 0.2 s</h3>','<details><summary>Archived startup comparison · t = 0.2 s</summary><div class="card" style="margin-top:18px">')
s=s.replace('They are completed startup tests, not converged reference cases.</p></div>','They are completed startup tests, not converged reference cases.</p></div></details>')
p.write_text(s)
p=R/'collect_status.py';s=p.read_text().replace("['M03','M02','M04']","['M03','M02','M04','M05']");p.write_text(s)
p=R/'select_snapshots.py';s=p.read_text().replace("['M03','M02','M04']","['M03','M02','M04','M05']").replace("m!='M04'","m in ['M03','M02']");p.write_text(s)
p=R/'force_explorer.js';s=p.read_text().replace("M04:'#5267ad'","M04:'#5267ad',M05:'#6d7136'");p.write_text(s)
for name in ['plot_flow_fields.py','localize_pressure.py','yplus_diagnostic.py']:
 p=R/name;s=p.read_text().replace("'M04':'#5267ad'","'M04':'#5267ad','M05':'#6d7136'");p.write_text(s)
p=R/'analyze_forces.py';s=p.read_text().replace("[('M03','#187b73'),('M02','#bf5a28')]","[('M03','#187b73'),('M02','#bf5a28'),('M04','#5267ad'),('M05','#6d7136')]")
s=s.replace(" force=(pilot/'Fx_pressure_shear.txt').read_text()"," if not (pilot/'Fx_pressure_shear.txt').exists():continue\n force=(pilot/'Fx_pressure_shear.txt').read_text()")
p.write_text(s)
print('Dashboard rebuilt for M02/M03 results and M04/M05 continuation.')

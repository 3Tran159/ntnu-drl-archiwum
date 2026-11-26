from pathlib import Path
import json,shutil
R=Path(r'F:\ntnu\mesh_screening_20261028\force_stabilization_20261029')
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','mesh_optimization_plan.json']:
 p=R/name;s=p.read_text(encoding='utf-8');s=s.replace('M10','M15')
 a=json.loads(s)
 if name=='mesh_selection_plan.json':a['maximum_mesh_number']=15;a['latest_user_authorization']='User explicitly raised the ceiling from M10 to M15 on 29 October, after the LE/TE refinement proposal.'
 p.write_text(json.dumps(a,indent=2,ensure_ascii=False),encoding='utf-8')
for name in ['mesh_selection_queue.py','mesh_convergence.py','campaign_dashboard.py']:
 p=R/name;s=p.read_text(encoding='utf-8');s=s.replace('M10','M15')
 if name=='mesh_selection_queue.py':
  assert r'M(0[2-9]|10)_until_settled' in s
  s=s.replace(r'M(0[2-9]|10)_until_settled',r'M(0[2-9]|1[0-5])_until_settled')
 p.write_text(s,encoding='utf-8')
p=R/'build_dashboard_en.py';s=p.read_text(encoding='utf-8')
s=s.replace("from campaign_dashboard import sections","from live_tests_panel import snapshot as test_snapshot, panel as test_panel\nactive_tests=test_snapshot()\nfrom campaign_dashboard import sections")
s=s.replace("templates={","templates={\n'@@LIVE_TESTS@@':test_panel(active_tests),")
s=s.replace("'@@DATA@@':json.dumps({","'@@DATA@@':json.dumps({'active_tests':active_tests,")
s=s.replace('@@PAUSE_NOTE@@\n<div class="card">','@@PAUSE_NOTE@@\n@@LIVE_TESTS@@\n<div class="card">')
s=s.replace('<a href="#overview">Overview</a>','<a href="#overview">Overview</a><a href="#live-tests">Live tests</a>')
p.write_text(s,encoding='utf-8')
p=R/'force_explorer.js';s=p.read_text(encoding='utf-8');s=s.replace("M10:'#805f9c'","M10:'#805f9c',M11:'#a63603',M12:'#1b9e77',M13:'#7570b3',M14:'#e7298a',M15:'#a6761d'");p.write_text(s,encoding='utf-8')
# Shared controls are visible once; let a larger future matrix scroll inside its own container.
p=R/'mesh_parameter_table.py';s=p.read_text(encoding='utf-8');s=s.replace(" s=css+'<div class=\"card\""," css+='<style>#mesh-parameters table{min-width:'+str(max(1050,205+110*len(columns)))+'px}</style>'\n s=css+'<div class=\"card\"");p.write_text(s,encoding='utf-8')
with (R/'RESUME_AT_HOME.txt').open('a',encoding='utf-8') as f:f.write('\nUSER LIMIT OVERRIDE ~20:33 CET: maximum mesh number is now M15, explicitly increased by the user. This supersedes EVERY historical M10 ceiling. Thresholds remain0.5% temporal settling and1%bothcoefficients. Queue ID validation, dashboard and active plans updated. User also proposed LE/TE local refinement with coarser mid-chord, to investigate as the next targeted family; do not alter running M09. Live tests panel added at the top with temporal GPU progress and CPU mesh status. Continue readability QA and avoid identical-value matrix rows.\n')
print('M15 limit and prominent live-test progress integrated.')

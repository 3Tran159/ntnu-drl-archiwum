from pathlib import Path
import json
R=Path(__file__).resolve().parent
p=R/'build_professor_dashboard.py';s=p.read_text(encoding='utf-8')
s=s.replace("'configuration':'calculation_configuration_decision.json','configured_mesh':'configured_mesh_screen_results.json'","'configuration':'calm_solver_configuration_decision.json','configured_mesh':'configured_mesh_results.json'")
s=s.replace("'configured_state':'configured_mesh_screen_state.json'","'configured_state':'configured_mesh_state.json'")
s=s.replace("lineage=render_lineage(data)","data['configdecision']=data['configuration'];lineage=render_lineage(data)")
s=s.replace("configuration_label=esc(config.get('status','Conservation review in progress').replace('_',' '))","configuration_label='SO / 1 ms / 10 inner supported for calm mesh screening' if config.get('status')=='supported_for_calm_mesh_screen' else 'Conservation review in progress'")
s=s.replace("c['id'].split('_')[2]","c['id'].split('_')[2].replace('inner','')")
s=s.replace("num(r.get('median_wall_s_per_step'),3),tag(","num(r.get('median_wall_s_per_step'),3)+' / '+num(r.get('median_wall_s_per_step',0)/c['dt_s'],0),tag(")
s=s.replace("'s / step¹'","'s / step · s / physical s¹'")
start=s.index("if configured:\n mc+=");end=s.index("# Drag and actual timing.",start)
s=s[:start]+'''from configured_mesh_panel import snapshot as configured_snapshot
cs=configured_snapshot()
mc+='<h3>Matched second-order cohort · current work</h3>'
if cs.get('jobs'):
 mr2=[]
 for j in cs['jobs']:
  if 'startup' in j['id']:continue
  r=j.get('result',{});mean=r.get('means',{});p=j.get('progress',{})
  label=local_link(r['source_sim'],j['mesh']) if r.get('source_sim') else j['mesh']
  mr2.append([label,j['status'],num(j['cells'],0),num(mean.get('CD'),7),num(mean.get('CL_total'),7),num(p.get('time_s'),3)])
 mc+=table(['Mesh / simulation','State','Cells','Settled mean CD','Settled mean CL','Time [s]'],mr2)
 mc+='<p class="note">Second-order time, 1 ms, 10 inner iterations. Blank means indicate no accepted force result yet. Each result stops at its first passing pair of new-setting 0.2 s windows; compare residual drift before accepting a near-threshold mesh difference.</p>'
 cp=configured.get('pairs',[])
 if cp:mc+=table(['Candidate / reference','Δ CD','Δ CL','Force comparison'],[[p['candidate']+' / '+p['reference'],pct(p['difference_pct']['CD']),pct(p['difference_pct']['CL_total']),tag('Within 1%' if p['both_force_coefficients_within_1pct'] else 'Outside 1%')] for p in cp])
else:
 mc+='<p>M09 geometry and topology audit passed. Force calculation has not started.</p>'
''' + s[end:]
start=s.index("fields=''\nmanifest=");end=s.index("# Explicit future wave",start)
s=s[:start]+'''fields=''
manifest=data['fields']
for ident in ('M04','M07','M08'):
 item=manifest.get('meshes',{}).get(ident)
 if item:
  caption=ident+' · t = '+num(item['time_s'],3)+' s · historical first-order accepted snapshot. Streamlines show instantaneous velocity; Cp subtracts nominal hydrostatic pressure ρg(2−z). Shared limits: speed 0–23 m/s and Cp −0.8…2.5.'
  fields+=image('professor_fields_'+ident+'.png',caption)
if not fields:fields='<p>Accepted field figures are being rendered.</p>'
fields+='<p class="note">These are instantaneous snapshots at each accepted stopping time, not time-averaged fields or particle trajectories. New second-order results will be shown as a separate cohort after acceptance.</p>'
''' +s[end:]
s=s.replace("body=decision_html","body=decision_html")
p.write_text(s,encoding='utf-8')
p=R/'build_dashboard_en.py';s=p.read_text(encoding='utf-8')
b=R/'build_dashboard_before_professor_review.py'
if not b.exists():b.write_text(s,encoding='utf-8')
old="'@@LIVE_TESTS@@':test_panel(active_tests),"
new="'@@LIVE_TESTS@@':__import__('configured_mesh_panel').panel()+('<details><summary>Completed M04 calculation-setting tests</summary>'+test_panel(active_tests)+'</details>' if (R/'calm_solver_configuration_decision.json').exists() else test_panel(active_tests)),"
assert s.count(old)==1;s=s.replace(old,new)
# One review link in the main navigation, with no separate publishing path.
old='<div class="nav-inner">'
assert s.count(old)==1
s=s.replace(old,old+'<a href="professor_dashboard.html">Research review ↗</a>')
p.write_text(s,encoding='utf-8')
p=R/'update_status.py';s=p.read_text(encoding='utf-8')
b=R/'update_status_before_professor_review.py'
if not b.exists():b.write_text(s,encoding='utf-8')
assert "run('build_professor_dashboard.py')" not in s
s+="\nrun('build_professor_dashboard.py')\n";p.write_text(s,encoding='utf-8')
print('Both dashboard builders integrated; original controls and result cohorts retained')

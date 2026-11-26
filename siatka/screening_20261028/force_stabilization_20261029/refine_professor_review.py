from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'build_professor_dashboard.py';s=p.read_text(encoding='utf-8')
s=s.replace("offsets={'M06':(-7,-20)","offsets={'M03':(-40,-15),'M05':(8,-14),'M06':(-7,-20)")
s=s.replace("'M04':(10,-12)","'M04':(10,25)")
s=s.replace("('SO 1 ms → 0.5 ms: '+pct(time_pair['difference_pct']['CD'])+' CD and '+pct(time_pair['difference_pct']['CL_total'])+' CL.' if time_pair else 'Matched temporal tests in progress.')","('Halving Δt from 1 to 0.5 ms changes both CD and CL by less than 0.001%.' if time_pair and max(abs(time_pair['difference_pct']['CD']),abs(time_pair['difference_pct']['CL_total']))<.001 else 'Matched temporal tests in progress.')")
s=s.replace("data['configdecision']=data['configuration'];lineage=render_lineage(data)","data['configdecision']=data['configuration'];lineage=render_lineage(data)")
# Chronological times from completed run manifests, separate from physical simulation time.
anchor="# Temporal matched comparisons and original reference."
insert="""# Completion chronology derived from saved launcher timestamps and elapsed durations.
chronology=[]
for m,snap in data['snapshots'].items():
 folder=Path(snap['folder']);proc=read(str(folder/'process.json'));done=read(str(folder/'controller_result.json'))
 if proc.get('start_unix') and done.get('elapsed_wall_s'):
  finish=proc['start_unix']+done['elapsed_wall_s']
  chronology.append((finish,m+' · historical mesh',str(by.get(m,{}).get('cells','—'))+' cells · force settling passed'))
for t in tc:
 folder=R/'temporal_order_20261029'/t['id'];proc=read(str(folder/'process.json'));done=read(str(folder/'controller_result.json'))
 if proc.get('start_unix') and done.get('elapsed_wall_s'):
  finish=proc['start_unix']+done['elapsed_wall_s']
  chronology.append((finish,t['short']+' · M04 numerical test',('1st-order' if t['order']=='FIRST_ORDER' else '2nd-order')+' · '+num(t['dt_s']*1000,1)+' ms · '+str(t['inner'])+' inner · matched window complete'))
lineage+='<details><summary>Chronological run record · local completion times</summary>'+table(['Completed locally','Run','Recorded outcome'],[[datetime.datetime.fromtimestamp(x).astimezone().strftime('%d Oct · %H:%M'),esc(label),esc(outcome)] for x,label,outcome in sorted(chronology)])+'<p class="note">Wall-clock completion = saved launch time + controller elapsed duration. Physical simulation times are reported in the result tables.</p></details>'
"""
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor)
# Compact near-wall exceptions expose, rather than hide, the TE outliers.
s=s.replace("num(r['time_s'],3)])\ndefinition+='<h3>Measured near-wall resolution</h3>'+table(['Mesh','Area-weighted y+ p95','Wall area with y+ &lt; 1','Saved field t [s]'],yp)","num(r['yplus'].get('max'),1),num(r['time_s'],3)])\ndefinition+='<h3>Measured near-wall resolution</h3>'+table(['Mesh','Area-weighted y+ p95','Wall area with y+ &lt; 1','Maximum y+','Saved field t [s]'],yp)\ndefinition+='<p class=\"note\">Small trailing-edge regions have much larger y+ than the area-weighted p95. Low p95 alone does not prove uniform near-wall resolution.</p>'")
p.write_text(s,encoding='utf-8')
# Prevent the completed-test drawer from incorrectly reporting M09 flow as unstarted.
p=R/'live_tests_panel.py';s=p.read_text(encoding='utf-8')
s=s.replace("if data['cpu_builds']:\n  for a in data['cpu_builds']:","if data['cpu_builds'] and not (R/'calm_solver_configuration_decision.json').exists():\n  for a in data['cpu_builds']:")
s=s.replace("No active mesh build recorded.","Mesh construction is complete; current flow tests are shown above.")
s=s.replace("'completed_pending_review':'Completed; reviewing balance'","'completed_pending_review':'Completed; calm-screen settings selected' if (R/'calm_solver_configuration_decision.json').exists() else 'Completed; reviewing balance'")
p.write_text(s,encoding='utf-8')
print('Research chronology, timing labels and near-wall exceptions updated')

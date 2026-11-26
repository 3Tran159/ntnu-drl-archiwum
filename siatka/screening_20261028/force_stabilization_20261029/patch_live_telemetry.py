from pathlib import Path
import datetime,shutil
p=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/collect_control_status.py');s=p.read_text(encoding='utf8');shutil.copy2(p,p.with_name('collect_control_status_before_live_archive_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.py'))
a="campaign=[bool]($_.CommandLine -match 'quasi2d_waves_20261029|force_stabilization_20261029')"
b="campaign=[bool]($_.CommandLine -and ($_.CommandLine.Replace([char]92,[char]47) -match 'E:/ntnu/quasi2d_waves_20261029/|F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/'))"
assert s.count(a)==1;s=s.replace(a,b)
a="out['stop_requested']=(R/'STOP_ALL').exists()";b="hold=read(R/'campaign_hold.json');out['campaign_hold']=hold\n out['stop_requested']=(R/'STOP_ALL').exists() or (R/'local_control/PAUSE').exists() or hold.get('active',False)"
assert s.count(a)==1;s=s.replace(a,b)
a="  costs=[]\n  for a,b in zip(rows,rows[1:]):";b="  costs=[]\n  nominal_dt=finite(s.get('dt_s')) or finite(read(folder/'setup.json').get('dt_s')) or (.001 if len(rows)<2 else (rows[-1].get('time_s',0)-rows[-2].get('time_s',0)))\n  for a,b in zip(rows,rows[1:]):"
assert s.count(a)==1;s=s.replace(a,b)
s=s.replace("if .00099<dt<.00101 and wa","if nominal_dt*.99<dt<nominal_dt*1.01 and wa")
s=s.replace("performance_note='Latest50 regular1ms steps; mean includes checkpoint/export overhead'","performance_note='Latest50 regular steps at selected dt='+str(nominal_dt)+'s; mean includes checkpoint/export overhead'")
a=" last=read(R/'wave_propagation_state.json');"
b=" if hold.get('active') and out['activity'].get('state') in ('idle','paused'):\n  out['activity'].update(state='paused',description='No active campaign calculation',stage='Waiting for mesh convergence and optimization review')\n last=read(R/'wave_propagation_state.json');"
assert s.count(a)==1;s=s.replace(a,b);compile(s,str(p),'exec');p.write_text(s,encoding='utf8');print('Telemetry ownership uses absolute roots; selected timestep costs and campaign hold reflected')

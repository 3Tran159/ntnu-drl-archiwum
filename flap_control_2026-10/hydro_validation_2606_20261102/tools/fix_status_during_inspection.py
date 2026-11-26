from pathlib import Path
import json,datetime,os,py_compile,shutil
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8');assert 'def last_flow_snapshot(' not in s
method=r'''
def last_flow_snapshot(st,metrics):
 active=st.get('active')
 if active and not active['macro'].startswith('Inspect') and metrics.get('history_rows',0)>0:
  return {k:v for k,v in metrics.items() if k!='owned_active_pids'}
 jobs=[j for j in st['jobs'].values() if j.get('macro') and not j['macro'].startswith('Inspect') and j.get('output') and (Path(j['output'])/'history.csv').exists()]
 jobs.sort(key=lambda j:j.get('ended_at',''),reverse=True)
 for rec in jobs:
  with (Path(rec['output'])/'history.csv').open(encoding='utf8') as f:rows=list(csv.DictReader(f))
  if not rows:continue
  row=rows[-1];v=dict(job_id=rec['id'],physical_time_s=float(row['time_s']),history_rows=len(rows))
  for key in ['time_s','CL_hydro','CD','Mh_Nm','p_absolute_min_Pa','mass_imbalance_relative','omega_floor_cells','k_floor_cells','max_turbulent_viscosity_ratio','overset_error_cells','difficult_interpolation_cells']:
   if row.get(key):v[key]=float(row[key])
  cp=Path(rec['output'])/'checkpoint.sim'
  if cp.exists():
   v['last_output_sim']=str(cp)
   if str(cp) in st.get('checkpoint_integrity',{}):v['checkpoint_integrity']=st['checkpoint_integrity'][str(cp)]
  log=Path(rec['log'])
  if log.exists():
   with log.open('rb') as f:f.seek(max(0,log.stat().st_size-160000));tail=f.read().decode('utf8','replace')
   ts=re.findall(r'TimeStep\s+(\d+):\s+Time\s+([+\d.eE-]+)',tail);it=re.findall(r'^\s*(\d+)\s+[+\d.eE-]+\s+[+\d.eE-]+',tail,re.M)
   if ts:v['timestep']=int(ts[-1][0])
   if it:v['iteration']=int(it[-1])
  return v
 return metrics or st.get('last_metrics',{})
'''
s=s.replace('def publish(st,cfg,metrics,rs):',method+'\ndef publish(st,cfg,metrics,rs):',1)
old=" atomic(H/'NIGHT_DASHBOARD.json',view)"
new=" view['flow_metrics']=last_flow_snapshot(st,view['metrics'])\n"+old
assert old in s;s=s.replace(old,new,1)
needle=" base['current_obstacle']='C0 force bias and turbulence clipping unresolved; no deflections approved'"
new=""" if not active or active['macro'].startswith('Inspect'):
  flow=view['flow_metrics']
  if flow.get('physical_time_s') is not None:base['physical_time_s']=flow['physical_time_s']
  if flow.get('last_output_sim'):base['last_checkpoint']=flow['last_output_sim']
  for key in ['timestep','iteration']:
   if key in flow:base[key]=flow[key]
   else:base.pop(key,None)
  if flow.get('checkpoint_integrity'):base['last_checkpoint_integrity']=flow['checkpoint_integrity']
  if active:base['inspection_input_time_s']=active.get('initial_time_s')
 base['current_obstacle']='C0 force bias and turbulence clipping unresolved; no deflections approved'"""
assert needle in s;s=s.replace(needle,new,1)
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp/p.name;backup.parent.mkdir(parents=True);shutil.copy2(p,backup);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8')
s=s.replace("m=view.get('metrics',{});a=view.get('active');e=html.escape","m=view.get('flow_metrics',view.get('metrics',{}));a=view.get('active');e=html.escape")
s=s.replace("checkpoint=base.get('last_checkpoint','');","if a and a['macro'].startswith('Inspect'):case='Audyt ustawień tylko do odczytu — poniżej ostatnie dane przepływu C0'\n checkpoint=base.get('last_checkpoint','');")
s=s.replace("('RAM wolny',str(view['resources']['ram_available_GiB'])+' GiB')","('RAM wolny',str(view['resources']['ram_available_GiB'])+' GiB'),('Komórki z ω na ograniczeniu',n('omega_floor_cells','.0f')),('Maks. μt/μ',n('max_turbulent_viscosity_ratio','.5g'))")
s=s.replace('Test interpolacji odległościowej oceni związek między interpolacją, ograniczeniami turbulencji i błędem sił. Samo zbliżenie CL/CD nie oznacza akceptacji.','Test odległościowy zatrzymano po73 krokach: anomalie pól pozostały. Trwa audyt ustawień i ruchu ścian przed wyborem dalszej naprawy. Samo zbliżenie CL/CD nie oznacza akceptacji.')
s=s.replace('<details><summary>Wykres ciśnienia B/C</summary>','<details><summary>Porównanie pól po zmianie interpolacji</summary><img src="reports/C0_distance_fields_step_25.png" alt="Pola B, kontrola C0 i test interpolacji"></details><details><summary>Wykres ciśnienia B/C</summary>')
shutil.copy2(p,backup.parent/p.name);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));cfg['controller_exit_requested']=True;tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
print('Prepared display fix: read-only inspection cannot roll back last solved physical time/checkpoint. Controller handover requested; STAR remains untouched.')

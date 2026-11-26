from pathlib import Path
import json,datetime,shutil,py_compile
h=Path(__file__).resolve().parents[1]
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_queue.py','night_native.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8')
s=s.replace("'C0DistanceInterpolationTest.java':8}","'C0DistanceInterpolationTest.java':8,'FreshC0DistanceInit.java':8}")
assert "'FreshC0DistanceInit.java':8" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
s=s.replace("'C0DistanceInterpolationTest.java'}","'C0DistanceInterpolationTest.java','FreshC0DistanceInit.java'}")
s=s.replace("'C0InnerIterationTest.java':'c0_inner40_',","'FreshC0DistanceInit.java':'c0_distance_fresh_','C0InnerIterationTest.java':'c0_inner40_',")
s=s.replace("rows=[];hp=out/'history.csv'","rows=[];steady=rec['macro']=='FreshC0DistanceInit.java';hp=out/('steady_iterations.csv' if steady else 'history.csv')")
s=s.replace("metrics['physical_time_s']=float(row['time_s'])","metrics['physical_time_s']=0.0 if steady else float(row['time_s'])\n    if steady:metrics['iteration']=int(row['iteration']);metrics['steady_initialization']=True")
s=s.replace("metrics['operation']='READ_ONLY_AUDIT' if rec['macro'].startswith('Inspect') else", "metrics['operation']='STEADY_INITIALIZATION' if steady else 'READ_ONLY_AUDIT' if rec['macro'].startswith('Inspect') else")
s=s.replace("status.get('status')=='inspection_complete' or", "status.get('status') in ['inspection_complete','steady_diagnostic_ready'] or")
a=s.index("def last_flow_snapshot(");b=s.index("\ndef publish(",a)
s=s[:a]+'''def last_flow_snapshot(st,metrics):
 active=st.get('active')
 if active and not active['macro'].startswith('Inspect') and metrics.get('history_rows',0)>0:
  return {k:v for k,v in metrics.items() if k!='owned_active_pids'}
 jobs=[j for j in st['jobs'].values() if j.get('macro') and not j['macro'].startswith('Inspect') and j.get('output')]
 jobs.sort(key=lambda j:j.get('ended_at',''),reverse=True)
 for rec in jobs:
  steady=rec['macro']=='FreshC0DistanceInit.java'
  hp=Path(rec['output'])/('steady_iterations.csv' if steady else 'history.csv')
  if not hp.exists():continue
  with hp.open(encoding='utf8') as f:rows=list(csv.DictReader(f))
  if not rows:continue
  row=rows[-1];v=dict(job_id=rec['id'],physical_time_s=0.0 if steady else float(row['time_s']),history_rows=len(rows))
  if steady:v.update(iteration=int(row['iteration']),steady_initialization=True,operation='STEADY_INITIALIZATION')
  for key in ['time_s','CL_hydro','CD','Mh_Nm','p_absolute_min_Pa','mass_imbalance_relative','omega_floor_cells','k_floor_cells','max_turbulent_viscosity_ratio','overset_error_cells','difficult_interpolation_cells']:
   if row.get(key):v[key]=float(row[key])
  cp=Path(rec['output'])/('steady_checkpoint.sim' if steady else 'checkpoint.sim')
  if cp.exists():
   v['last_output_sim']=str(cp)
   if str(cp) in st.get('checkpoint_integrity',{}):v['checkpoint_integrity']=st['checkpoint_integrity'][str(cp)]
  log=Path(rec['log'])
  if log.exists() and not steady:
   with log.open('rb') as f:f.seek(max(0,log.stat().st_size-160000));tail=f.read().decode('utf8','replace')
   ts=re.findall(r'TimeStep\\s+(\\d+):\\s+Time\\s+([+\\d.eE-]+)',tail);it=re.findall(r'^\\s*(\\d+)\\s+[+\\d.eE-]+\\s+[+\\d.eE-]+',tail,re.M)
   if ts:v['timestep']=int(ts[-1][0])
   if it:v['iteration']=int(it[-1])
  return v
 return metrics or st.get('last_metrics',{})
''' +s[b:]
s=s.replace("moving=view['metrics'].get('physical_time_s',0)>active.get('initial_time_s',0) and bool(view['metrics'].get('owned_active_pids'))","moving=(view['metrics'].get('physical_time_s',0)>active.get('initial_time_s',0) or (view['metrics'].get('steady_initialization') and view['metrics'].get('iteration',0)>0)) and bool(view['metrics'].get('owned_active_pids'))")
s=s.replace("base['current_obstacle']='C0 force bias", "if view['flow_metrics'].get('steady_initialization'):\n  base['dt_s']=None;base.pop('timestep',None);base['last_solved_case']='C0 fresh DISTANCE initialization, 361532 cells';base['time_note']='Steady numerical initialization: physical time does not advance'\n base['current_obstacle']='C0 force bias")
assert "'FreshC0DistanceInit.java'" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8')
s=s.replace("case={'C0InnerIterationTest.java'","case={'FreshC0DistanceInit.java':'C0 — czysta inicjalizacja na tej samej siatce','C0InnerIterationTest.java'")
s=s.replace("cards=[('Solver',state),","cards=[('Solver',state),('Iteracja',n('iteration','.0f')),")
s=s.replace("Checkpoint co 25 kroków. Aktualny krok Δt = 0,002 s. Siatka i czas fizyczny są zachowywane; wynik testu wymaga oceny Work.","W przebiegu transient zapis co 25 kroków, Δt = 0,002 s. W osobnym teście czystej inicjalizacji zapis co 250 iteracji; czas fizyczny pozostaje 0 s. Każdy wynik wymaga oceny Work.")
s=s.replace("Trwa audyt ustawień i ruchu ścian przed wyborem dalszej naprawy.","Audyt wykluczył zamrożone solvery, ruch ścian i dezaktywację powierzchni płata. Następny test: czysta inicjalizacja 0° na zapisanej siatce sprzed testu ruchu, bez przebudowy geometrii.")
p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_distance_fresh_initialization',macro='FreshC0DistanceInit.java',input=str(h/'cases/SP_C_split0_overset/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='Separate inherited solution from same-mesh Overset error. Fresh initialization only; no nonzero deflection; no scientific acceptance.')
assert all(j['id']!=job['id'] for j in cfg['jobs'])
cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf8');tmp.replace(cfgp)
event=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_approved_diagnostic',job=job['id'],reason=job['purpose'],same_mesh=True,source_sha256='8d4692832503adba9a8dca8b1583c56ea57a6f5979c2887b3dca1a70bb8f8eb6',gate_C0=False,backup=str(backup))
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(event)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+event['at']+' Fresh C0 DISTANCE initialization approved on protected pre-motion mesh, same physical conditions and geometry. Native setup audit shows all foil walls active, zero grid velocity, flow and turbulence solvers not frozen. No acceptance or deflections. Steady time=0 is a separate new diagnostic, not a reset of the previous checkpoint.\n')
print(json.dumps(event,indent=2))

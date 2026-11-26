from pathlib import Path
import csv,json,re,os,datetime
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_urans_pressure_urf01_20261103_043547'
rows=list(csv.DictReader((run/'history.csv').open(encoding='utf8')));assert rows
last=rows[-1];proof=(run/'checkpoint_readback.txt').read_text(encoding='utf8')
assert 'native_iteration=7560' in proof and 'time=0.45000000000000034' in proof
assert abs(float(re.search(r'HF_CL_hydro=([-+0-9.eE]+)',proof).group(1))-.3252877400620151)<1e-10
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));at=datetime.datetime.now().astimezone().isoformat()
for k in ['reviewed_recovery_checkpoint','last_verified_transient_checkpoint']:
 v[k]['native_reopen_verified']=True;v[k]['native_reopen_evidence']=str(run/'checkpoint_readback.txt')
v['at']=at;v['decision']='RUNNING:0degree pressure-relaxation diagnostic. Native time has advanced from retained0.450s checkpoint; no reset. All nonzero angles remain blocked.'
v['live_work_evidence']=dict(run=str(run),observed_time_s=float(last['time_s']),native_iteration=int(last['native_iteration']),CL=float(last['CL_hydro']),CD=float(last['CD']),Mh_Nm=float(last['Mh_Nm']),pabs_min_Pa=float(last['p_absolute_min_Pa']),mass_imbalance_relative=float(last['mass_imbalance_relative']),mesh_cells=333939,pressure_urf=.1,velocity_urf=.8,inner_iterations=40)
tmp=p.with_suffix('.work_tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,p)
cfgpath=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgpath.read_text(encoding='utf8'))
assert cfg['scientific_gates']['C0_bias_explained_and_approved'] is False
cfg['scientific_gates']['reason']='Original C0 rejected for near-wall Overset artifacts. Corrected C0 passes strict field/mesh and force-window guards; pressure/continuity convergence audit remains pending. Only0degree numerical diagnostic authorized; no nonzero angles.'
tmp=cfgpath.with_suffix('.work_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,cfgpath)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(dict(at=at,kind='work_pressure_native_progress_confirmed',evidence=v['live_work_evidence'],source_native_reopen_verified=True,scientific_approved=False))+'\n')
print(json.dumps(v['live_work_evidence'],indent=2))

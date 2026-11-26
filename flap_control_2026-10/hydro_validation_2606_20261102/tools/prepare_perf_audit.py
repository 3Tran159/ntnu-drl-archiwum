from pathlib import Path
import sys,json,shutil,hashlib,datetime,subprocess,socket,csv
import night_queue as q
from benchmark_telemetry import topology
H=q.H;E='RECOVERED_PERF_20261103';D=H/'cases'/E;D.mkdir(exist_ok=False)
st=q.read(q.STATE);cfg=q.read(q.CFG);assert st.get('active') is None and not q.LOCK.exists();assert not any(x['ownedBatch'] for x in q.processes())
rec=st['jobs']['RECOVERED_FIXED_PLUS2_SWEEP_20261103_RUN'];assert rec['macro_status']['status']=='bounded_sweep_paused';P=Path(rec['output']);meta=q.read(P/'latest_checkpoint.json');src=Path(meta['path']);assert src.name=='paused_checkpoint.sim'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha(src)==meta['sha256'];dest=D/'production_source.sim';shutil.copy2(src,dest);assert sha(dest)==meta['sha256']
arch=D/'preserved';arch.mkdir();manifest=[]
for p in P.iterdir():
 if p.is_file():
  manifest.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
  if p.suffix in ['.json','.jsonl','.txt'] or p.name in ['history.csv','pressure_zones.csv','residual_history.csv','static_results.csv','static_pressures.csv']:shutil.copy2(p,arch/p.name)
for name in ['NIGHT_QUEUE.json','NIGHT_QUEUE_STATE.json','NIGHT_STATUS.json','WORK_CURRENT_REVIEW.json']:shutil.copy2(H/name,arch/name)
shutil.copy2(rec['redacted_log'],arch/'production_redacted.log')
q.atomic(D/'PRODUCTION_ARCHIVE.json',dict(at=q.now(),source=meta,input_copy=str(dest),manifest=manifest,source_job=rec['id'],source_run=str(P),owned_solver_stopped=True,fields_reset=False))
topo=topology();Pcores=[x['logical_cpu'] for x in topo if x['efficiency_class']==1];Ecores=[x['logical_cpu'] for x in topo if x['efficiency_class']==0]
assert len(Pcores)==8 and len(Ecores)==16
reserve=[0,1];available=[x for x in Pcores if x not in reserve]+Ecores
profiles={str(n):available[:n] for n in [8,12,16,18,20]};masks={n:sum(1<<x for x in slots) for n,slots in profiles.items()}
history=list(csv.DictReader((P/'history.csv').open()));last=history[-1]
W=Path(r'E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W04_20261103_113831_5d98c0')
wrows=list(csv.DictReader((W/'history.csv').open()));elapsed=[float(b['wall_s'])-float(a['wall_s']) for a,b in zip(wrows[-61:-1],wrows[-60:])]
import statistics
plan=dict(at=q.now(),experiment_id=E,host=socket.gethostname(),source_checkpoint=str(dest),production_checkpoint=meta,input_sha256=meta['sha256'],initial_reports={k:float(last[k]) for k in ['CL_hydro','CD','Mh_Nm','Fx_N','Fz_N','p_absolute_min_Pa']},topology=topo,CPU_profiles=profiles,affinity_masks=masks,reserved_P_cores=reserve,W04=dict(local=True,solver_pid=5588,client_pid=3336,mpi_ranks=1,affinity_mask=12598275,affinity_cpus=Pcores,history=str(W/'history.csv'),baseline_last60_median_step_s=statistics.median(elapsed),affinity_will_not_change=True),window_physical_s=.036,warmup_physical_s=.012,dt_candidates=[.002,.003,.004],inner_iterations=50,pressure_threshold_Pa=12339.214766776897,mass_threshold=1e-4,residual_ratio_threshold=.01,reference_residual_omega=.02152224952396808,reference_is_diagnostic_not_validated=True,MPI_equivalence_relative_tolerance=.001,timestep_force_relative_tolerance=.005,timestep_pressure_relative_tolerance=.01,CFL_over_dt_relative_tolerance=.02,W04_sustained_slowdown_fraction=.15,W04_slowdown_windows_required=2,maximum_CPU=20,GPU=False,legacy_global_queue_limit=16,scope_limit_override_only=True,minimum_improvement_fraction=.03,full_campaign_resume_authorized=True,production_resumes_from=meta['path'])
q.atomic(D/'PLAN.json',plan);print(json.dumps({k:plan[k] for k in ['source_checkpoint','production_checkpoint','CPU_profiles','W04','window_physical_s','warmup_physical_s']},indent=2))

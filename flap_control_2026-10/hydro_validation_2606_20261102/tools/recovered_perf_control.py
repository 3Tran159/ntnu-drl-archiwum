from pathlib import Path
import sys,json,hashlib,datetime,shutil
import night_queue as q
H=q.H;E='RECOVERED_PERF_20261103';D=H/'cases'/E
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def prepare(cpu,dt):
 plan=q.read(D/'PLAN.json');cfg=q.read(q.CFG);st=q.read(q.STATE)
 assert not st.get('active') and not any(p['ownedBatch'] for p in q.processes())
 assert cpu in [8,12,16,18,20] and dt in [.002,.003,.004]
 assert cpu in plan.get("resource_revision",{}).get("eligible_cpu_counts",[8,12,16,18,20]),"CPU configuration excluded by measured W04 impact"
 jid=E+'_MPI'+str(cpu)+'_DT'+str(round(dt*1000))+(sys.argv[3] if len(sys.argv)>3 else '')
 assert jid not in st['jobs'] and not any(j['id']==jid for j in cfg['jobs']),'Never replay completed benchmark'
 assert not any(j['id'] not in st['jobs'] and not j.get('disabled') for j in cfg['jobs'])
 if dt==.004:
  previous=q.read(D/'BENCHMARK_RESULTS.json',[]);assert any(x['dt_s']==.003 and x.get('timestep_accepted') for x in previous),'dt.003 must pass before dt.004'
 source=Path(plan['source_checkpoint']);assert sha(source)==plan['input_sha256'];meta=plan['production_checkpoint'];reports=plan['initial_reports']
 props=H/'audit/RECOVERED_PERF_RUNTIME.properties';props.write_text(f'input={source.as_posix()}\ntime_s={meta["time_s"]}\niteration={meta["iteration"]}\nstage=0\nstage_start_s=0.65\ndt={dt}\nCL={reports["CL_hydro"]}\nCD={reports["CD"]}\nMh={reports["Mh_Nm"]}\n',encoding='utf8')
 macro=H/'macros/RecoveredPerfBench.java'
 j=dict(id=jid,kind='recovered_perf',experiment_id=E,approved=True,macro=macro.name,macro_sha256=sha(macro),input=str(source),input_sha256=plan['input_sha256'],initial_time_s=meta['time_s'],cpu_processes=cpu,dt_s=dt,angle_deg=0,affinity_mask=plan['affinity_masks'][str(cpu)],runtime_properties_sha256=sha(props),progress_timeout_s=900,maximum_runtime_s=1800,runtime_guards=dict(minimum_absolute_pressure_Pa=plan['pressure_threshold_Pa'],maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_overset_error_cells=0,maximum_turbulent_viscosity_ratio=99999))
 import csv,statistics,time
 rows=list(csv.DictReader(Path(plan['W04']['history']).open()));steps=[float(b['wall_s'])-float(a['wall_s']) for a,b in zip(rows[-61:-1],rows[-60:])]
 j['W04_baseline_median_step_s']=statistics.median(steps);j['W04_baseline_epoch_s']=time.time();j['W04_baseline_last_step']=int(rows[-1]['step']);j['W04_baseline_no_owned_solver_verified']=True
 ap=D/(jid+'_APPROVAL.json');approval=dict(at=q.now(),approved_by_user=True,experiment_id=E,previous_blocked_job=st['failure_hold'],previous_case_remains_failed=True,approved_job_ids=[jid],source='Explicit SAFE CHECKPOINT + CPU/TIMESTEP BENCHMARK + AUTONOMOUS RESUME, including8/12/16/18/20MPI; current clarification W04 uses1MPI+1GPU',job=j,scope='Same protected production checkpoint; onlyMPI,own affinity anddt differ; no W04 changes; no threshold reductions')
 q.atomic(ap,approval);cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=st['failure_hold'],evidence=str(ap));cfg['jobs'].append(j)
 marker=H.parent/'STOP_OWNED_CFD.json'
 if marker.exists():
  m=q.read(marker);assert m.get('source')=='cfd_control' and m.get('reason')=='manual_stop','Non-manual stop requires explicit benchmark review';marker.replace(D/('production_manual_stop_'+datetime.datetime.now().strftime('%H%M%S')+'.json'))
 assert not (H.parent/'PAUSED_FOR_HOME.json').exists()
 cfg.update(accept_new_jobs=True,controller_exit_requested=False);q.atomic(q.CFG,cfg)
 review=q.read(H/'WORK_CURRENT_REVIEW.json');review.update(at=q.now(),current_job_kind='recovered_perf',status='BENCHMARK_RUNNING_OR_PREPARING',last_decision=f'Benchmark{cpu}MPI dt{dt}: same production source, no reset;2P cores outside own affinity; W04 unchanged. Residual omega baselineFAIL remains diagnostic.',obstacle='Select equivalent faster configuration; do not validate transient data',next='Sequential CPU benchmarks, then gated dt test, production resume from protected source');q.atomic(H/'WORK_CURRENT_REVIEW.json',review)
 q.event('scoped_perf_job_prepared',job=j);print(json.dumps(j,indent=2))
if __name__=='__main__':prepare(int(sys.argv[1]),float(sys.argv[2]))

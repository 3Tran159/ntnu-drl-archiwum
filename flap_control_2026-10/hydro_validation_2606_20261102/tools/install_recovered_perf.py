from pathlib import Path
import json,shutil,datetime,py_compile
import night_queue as q
H=q.H;E='RECOVERED_PERF_20261103';D=H/'cases'/E
st=q.read(q.STATE);cfg=q.read(q.CFG);assert st.get('active') is None and not q.LOCK.exists()
backup=D/'infrastructure_backup';backup.mkdir()
names=['night_queue.py','night_native.py','ramp_authorization.py','queue_safety.py','benchmark_telemetry.py','bounded_sweep_auth.py','bounded_sweep_dashboard.py','cfd_control.py']
for name in names:shutil.copy2(H/'tools'/name,backup/name)
def patch(name,a,b):
 p=H/'tools'/name;t=p.read_text();assert t.count(a)==1,(name,a);p.write_text(t.replace(a,b),encoding='utf8')
patch('ramp_authorization.py',"'RECOVERED_FIXED_PLUS2_SWEEP_20261103']","'RECOVERED_FIXED_PLUS2_SWEEP_20261103','RECOVERED_PERF_20261103']")
patch('queue_safety.py',"cpu=job.get('cpu_processes',8);assert 1<=cpu<=16", "cpu=job.get('cpu_processes',8);cap=20 if job.get('experiment_id')=='RECOVERED_PERF_20261103' and job.get('kind') in ['recovered_perf','perf_production'] else 16;assert 1<=cpu<=cap")
patch('night_native.py','name=sys.argv[1];',"allowed['RecoveredPerfBench.java']=20\nname=sys.argv[1];")
patch('night_native.py','assert 1<=cpu<=16',"assert 1<=cpu<=(20 if name=='RecoveredPerfBench.java' else 16)")
patch('night_native.py',"if name=='InletPressureRecovery.java':", "if name=='RecoveredPerfBench.java':\n from recovered_perf_auth import authorize_environment\n env.update(authorize_environment(h,name,sim,cpu))\nif name=='InletPressureRecovery.java':")
patch('night_queue.py','from ramp_authorization import blocks',"ALLOWED.add('RecoveredPerfBench.java')\nfrom ramp_authorization import blocks")
patch('night_queue.py',"  elif j.get('kind')=='pressure_recovery':","  elif j.get('kind')=='recovered_perf':\n   assert j['macro']=='RecoveredPerfBench.java' and j.get('experiment_id')=='RECOVERED_PERF_20261103'\n   assert j['cpu_processes'] in [8,12,16,18,20] and j['dt_s'] in [.002,.003,.004] and j.get('angle_deg')==0\n  elif j.get('kind')=='pressure_recovery':")
patch('night_queue.py','def output_path(receipt):',"def output_path(receipt):\n if receipt['macro']=='RecoveredPerfBench.java':return H/'cases/RECOVERED_PERF_20261103'/('run_'+receipt['run_id'])")
patch('night_queue.py',"['pressure_recovery_complete'","['recovered_perf_complete','recovered_perf_paused','pressure_recovery_complete'")
patch('night_queue.py','  start_telemetry(H)','  start_telemetry(H)\n  from recovered_perf_telemetry import start_perf_telemetry\n  start_perf_telemetry(H)')
patch('night_queue.py'," if review.get('current_job_kind')=='pressure_recovery':"," if review.get('current_job_kind')=='recovered_perf':\n  from recovered_perf_dashboard import publish\n  publish(H,view,base,st,review)\n  atomic(H/'NIGHT_DASHBOARD.json',view)\n if review.get('current_job_kind')=='pressure_recovery':")
patch('night_dashboard.py'," if review0.get('current_job_kind')=='pressure_recovery':"," if review0.get('current_job_kind')=='recovered_perf':\n  from recovered_perf_dashboard import render\n  return render(h,view,base,review0)\n if review0.get('current_job_kind')=='pressure_recovery':")
for name in names+['night_dashboard.py']:py_compile.compile(str(H/'tools'/name),doraise=True)
cfg['benchmark_cpu_policy']=dict(experiment_id=E,max_cpu=20,legacy_limit_unchanged=16,rollback=str(backup),reserved_P_cores=[0,1],W04_affinity_unchanged=True)
q.atomic(q.CFG,cfg);print('Scoped benchmark limit20 installed; ordinary limit16 unchanged. No solver launched.')

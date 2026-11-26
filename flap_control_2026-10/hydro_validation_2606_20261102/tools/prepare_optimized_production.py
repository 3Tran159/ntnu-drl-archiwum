"""Apply reviewed performance settings to the existing production solution only."""
from pathlib import Path
import sys,json,hashlib,shutil,datetime,subprocess,py_compile
import night_queue as q
H=q.H;E='RECOVERED_PERF_20261103';D=H/'cases'/E
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
selected=q.read(D/'SELECTED_CONFIG.json');plan=q.read(D/'PLAN.json');assert selected['dt_s']==.002
st=q.read(q.STATE);cfg=q.read(q.CFG);assert not st.get('active') and not q.LOCK.exists();assert not any(p['ownedBatch'] for p in q.processes())
src=Path(plan['production_checkpoint']['path']);assert sha(src)==plan['input_sha256'];meta=plan['production_checkpoint']
backup=D/'before_production_config';backup.mkdir()
for name in ['night_queue.py','night_native.py','cfd_control.py','bounded_sweep_dashboard.py']:shutil.copy2(H/'tools'/name,backup/name)
shutil.copy2(H/'NIGHT_QUEUE.json',backup/'NIGHT_QUEUE.json')
t=(H/'macros/RecoveredFixedFlapSweep.java').read_text().replace('class RecoveredFixedFlapSweep','class OptimizedRecoveredSweep').replace('RECOVERED_SWEEP_RUNTIME.properties','OPTIMIZED_RECOVERED_RUNTIME.properties').replace('NTNU_BOUNDED_SWEEP_ALLOWED','NTNU_OPTIMIZED_PRODUCTION_ALLOWED')
t=t.replace('cases/RECOVERED_FIXED_PLUS2_SWEEP_20261103/run_','cases/RECOVERED_FIXED_PLUS2_SWEEP_20261103/optimized_run_')
needle='Properties auth=new Properties();';assert t.count(needle)==1
t=t.replace(needle,r'''Process binding=new ProcessBuilder("C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe","-X","utf8",root.resolve("tools/perf_bind_workers.py").toString(),out.toString()).redirectErrorStream(true).start();String bindingOutput=new String(binding.getInputStream().readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);if(binding.waitFor()!=0)throw new IllegalStateException("Owned MPI affinity initialization failed: "+bindingOutput);Files.writeString(out.resolve("affinity_initialization.txt"),bindingOutput);Properties auth=new Properties();''')
macro=H/'macros/OptimizedRecoveredSweep.java';assert not macro.exists();macro.write_text(t,encoding='utf8')
r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(macro)],capture_output=True,text=True)
(D/'PRODUCTION_COMPILE.txt').write_text(r.stderr);assert r.returncode==0,r.stderr
def patch(name,a,b):
 p=H/'tools'/name;t=p.read_text();assert t.count(a)==1,(name,a);p.write_text(t.replace(a,b),encoding='utf8')
patch('night_native.py','name=sys.argv[1];',"allowed['OptimizedRecoveredSweep.java']=20\nname=sys.argv[1];")
patch('night_native.py',"20 if name=='RecoveredPerfBench.java' else 16","20 if name in ['RecoveredPerfBench.java','OptimizedRecoveredSweep.java'] else 16")
patch('night_native.py',"if name=='RecoveredPerfBench.java':","if name=='OptimizedRecoveredSweep.java':\n from optimized_recovered_auth import authorize_environment\n env.update(authorize_environment(h,name,sim,cpu))\nif name=='RecoveredPerfBench.java':")
patch('night_queue.py','from ramp_authorization import blocks',"ALLOWED.add('OptimizedRecoveredSweep.java')\nfrom ramp_authorization import blocks")
patch('night_queue.py',"  elif j.get('kind')=='recovered_perf':","  elif j.get('kind')=='perf_production':\n   assert j['macro']=='OptimizedRecoveredSweep.java' and j.get('experiment_id')=='RECOVERED_PERF_20261103'\n   assert j['cpu_processes'] in [8,12,16,18,20] and j['dt_s']==.002 and j['source_role']=='production_checkpoint'\n  elif j.get('kind')=='recovered_perf':")
patch('night_queue.py','def output_path(receipt):',"def output_path(receipt):\n if receipt['macro']=='OptimizedRecoveredSweep.java':return H/'cases/RECOVERED_FIXED_PLUS2_SWEEP_20261103'/('optimized_run_'+receipt['run_id'])")
props=H/'audit/OPTIMIZED_RECOVERED_RUNTIME.properties';props.write_text(f'input={src.as_posix()}\ntime_s={meta["time_s"]}\niteration={meta["iteration"]}\nstage={meta["stage"]}\nstage_start_s={meta["stage_start_s"]}\n',encoding='utf8')
base=next(x for x in cfg['jobs'] if x['id']=='RECOVERED_FIXED_PLUS2_SWEEP_20261103_RUN');cpu=selected['cpu_processes']
j={**base,'id':'RECOVERED_FIXED_PLUS2_SWEEP_20261103_OPTIMIZED_RESUME','kind':'perf_production','experiment_id':E,'macro':macro.name,'macro_sha256':sha(macro),'input':str(src),'input_sha256':plan['input_sha256'],'initial_time_s':meta['time_s'],'cpu_processes':cpu,'dt_s':.002,'source_role':'production_checkpoint','affinity_mask':plan['affinity_masks'][str(cpu)],'runtime_properties_sha256':sha(props),'selection_sha256':sha(D/'SELECTED_CONFIG.json')}
j['W04_baseline_median_step_s']=selected['W04_baseline_median_step_s'];j['W04_baseline_source_job']=selected['job'];j['W04_baseline_no_owned_solver_verified']=True
ap=D/'PRODUCTION_RESUME_APPROVAL.json';q.atomic(ap,dict(at=q.now(),approved_by_user=True,experiment_id=E,previous_blocked_job=st['failure_hold'],previous_case_remains_failed=True,approved_job_ids=[j['id']],source='Explicit safe stop,benchmark,and autonomous resume authorization; continue original production source, not benchmark branches',job=j,selected_configuration=str(D/'SELECTED_CONFIG.json')))
cfg['jobs'].append(j);cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=st['failure_hold'],evidence=str(ap));cfg.update(accept_new_jobs=True,controller_exit_requested=False)
for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:assert not (H.parent/name).exists(),'Safety marker requires reviewed resolution'
q.atomic(q.CFG,cfg)
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(at=q.now(),current_job_kind='bounded_sweep',experiment_id=E,status='OPTIMIZED_PRODUCTION_RESUME_AUTHORIZED',last_decision=f'Resume original t1.212 production checkpoint using{cpu}MPI,dt.002,inner50. MPI equivalence verified;omega convergence remains diagnostic until original steady gates pass. W04 unchanged.',obstacle='No settled10m/s/+2 point yet; unchanged force/residual gates apply.',next='Continue existing smooth U(t)to10,settle0,ramp+2,settle,sweep12/14/16/18; no replay',parameters={**work.get('parameters',{}),'CPU':cpu,'CPU_max':cpu,'dt':.002,'inner':50,'U':meta['U_m_s']},performance_comparison=str(D/'BENCHMARK_REPORT.html'));q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
patch('bounded_sweep_dashboard.py',"base.update(operation=base['solver_state'],current_case_label='Bounded fixed+2 velocity sweep',max_cpu_processes=8,mesh_cells=333939,flow_frozen=False)","base.update(operation=base['solver_state'],current_case_label='Recovered fixed+2 velocity sweep',max_cpu_processes=(st.get('active') or {}).get('cpu_processes',review.get('parameters',{}).get('CPU',8)),mesh_cells=333939,flow_frozen=False)\n data['CPU']=base['max_cpu_processes'];base['performance_comparison']=review.get('performance_comparison')")
patch('bounded_sweep_dashboard.py'," (h/'NIGHT_DASHBOARD.html').write_text(text,encoding='utf8')"," if review.get('performance_comparison'):\n  text=text.replace('</html>','<p><a href=\"cases/RECOVERED_PERF_20261103/BENCHMARK_REPORT.html\">Benchmark MPI/dt i wybór konfiguracji</a></p></html>')\n text=text.replace('8CPU,bez GPU',str(base.get('max_cpu_processes',8))+'CPU,bez GPU')\n (h/'NIGHT_DASHBOARD.html').write_text(text,encoding='utf8')")
for name in ['night_queue.py','night_native.py','bounded_sweep_dashboard.py']:py_compile.compile(str(H/'tools'/name),doraise=True)
q.event('optimized_production_resume_prepared',job=j,selected=selected,source_is_production=True)
print(json.dumps(dict(job=j['id'],CPU=cpu,dt=.002,production_source=str(src),time_s=meta['time_s'],prepared=True,started=False),indent=2))

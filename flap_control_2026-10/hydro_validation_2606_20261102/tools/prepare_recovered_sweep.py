"""Prepare, but never run, continuation after a passed single recovery test."""
from pathlib import Path
import sys,json,hashlib,shutil,datetime,subprocess,py_compile
import night_queue as q
H=q.H;R=H.parent;E='RECOVERED_FIXED_PLUS2_SWEEP_20261103';OLD='BOUNDED_FIXED_PLUS2_SWEEP_20261103'
D=R/'independent_cfd_diagnostics/INLET_PRESSURE_AUDIT_20261103'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
result=q.read(D/'RECOVERY_RESULT.json');assert result['status']=='PASS' and all(result['checks'].values())
assert not q.LOCK.exists();st=q.read(q.STATE);cfg=q.read(q.CFG)
assert st.get('active') is None and not any(p['ownedBatch'] for p in q.processes())
assert st['failure_hold']==OLD+'_RUN'
source=Path(result['checkpoint']['path']);assert sha(source)==result['checkpoint']['sha256']
record=st['jobs']['INLET_PRESSURE_RECOVERY_20261103_TEST'];assert record['state']=='completed'
assert any(c['sha256']==result['checkpoint']['sha256'] for c in record['checkpoints'])
backup=H/'audit'/('before_recovered_sweep_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
for rel in ['tools/night_queue.py','tools/night_native.py','tools/ramp_authorization.py','tools/bounded_sweep_auth.py','tools/bounded_sweep_dashboard.py','tools/cfd_control.py','NIGHT_QUEUE.json']:shutil.copy2(H/rel,backup/Path(rel).name)
t=(H/'macros/BoundedFixedFlapSweep.java').read_text().replace('class BoundedFixedFlapSweep','class RecoveredFixedFlapSweep').replace(OLD,E).replace('BOUNDED_SWEEP_RUNTIME.properties','RECOVERED_SWEEP_RUNTIME.properties')
r=(H/'macros/InletPressureRecovery.java').read_text();laws=r[r.index('// C2 time reparameterization:'):r.index('double angleAt(')]
laws=laws.replace('double speedAt(int k,double start,double t){return 18-8*smooth(phaseX(t));}','double speedAt(int k,double start,double t){return k==0?18-8*smooth(phaseX(t)):k<4?10:targetU(k)-2+2*smooth((t-start)/.2);}')
a=t.index('double speedAt(');b=t.index('double angleAt(',a);t=t[:a]+laws+t[b:]
assert t.count('if(stage==0&&t>=1.05-1e-9)')==1;t=t.replace('if(stage==0&&t>=1.05-1e-9)','if(stage==0&&t>=4.2-1e-9)')
macro=H/'macros/RecoveredFixedFlapSweep.java';assert not macro.exists();macro.write_text(t,encoding='utf8')
compiled=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(macro)],capture_output=True,text=True)
(H/'audit/RECOVERED_SWEEP_COMPILE.txt').write_text(compiled.stderr);assert compiled.returncode==0,compiled.stderr
def patch(name,a,b):
 p=H/'tools'/name;t=p.read_text();assert t.count(a)==1,(name,a);p.write_text(t.replace(a,b),encoding='utf8')
patch('ramp_authorization.py',"'INLET_PRESSURE_RECOVERY_20261103']","'INLET_PRESSURE_RECOVERY_20261103','RECOVERED_FIXED_PLUS2_SWEEP_20261103']")
patch('night_native.py','name=sys.argv[1];',"allowed['RecoveredFixedFlapSweep.java']=8\nname=sys.argv[1];")
patch('night_native.py',"if name=='BoundedFixedFlapSweep.java':","if name in ['BoundedFixedFlapSweep.java','RecoveredFixedFlapSweep.java']:")
patch('bounded_sweep_auth.py',"j=jobs[0];assert j.get('experiment_id')==E", "j=jobs[0];expected={'BoundedFixedFlapSweep.java':E,'RecoveredFixedFlapSweep.java':'RECOVERED_FIXED_PLUS2_SWEEP_20261103'}[name];assert j.get('experiment_id')==expected")
patch('bounded_sweep_auth.py',"(h/'audit/BOUNDED_SWEEP_RUNTIME.properties').read_bytes()", "(h/'audit'/('RECOVERED_SWEEP_RUNTIME.properties' if name=='RecoveredFixedFlapSweep.java' else 'BOUNDED_SWEEP_RUNTIME.properties')).read_bytes()")
patch('night_queue.py','from ramp_authorization import blocks',"ALLOWED.add('RecoveredFixedFlapSweep.java')\nfrom ramp_authorization import blocks")
patch('night_queue.py',"assert j['macro']=='BoundedFixedFlapSweep.java' and j.get('cpu_processes')==8", "assert j['macro'] in ['BoundedFixedFlapSweep.java','RecoveredFixedFlapSweep.java'] and j.get('cpu_processes')==8")
patch('night_queue.py',"assert j.get('experiment_id')=='BOUNDED_FIXED_PLUS2_SWEEP_20261103' and", "assert j.get('experiment_id')=={'BoundedFixedFlapSweep.java':'BOUNDED_FIXED_PLUS2_SWEEP_20261103','RecoveredFixedFlapSweep.java':'RECOVERED_FIXED_PLUS2_SWEEP_20261103'}[j['macro']] and")
patch('night_queue.py','def output_path(receipt):',"def output_path(receipt):\n if receipt['macro']=='RecoveredFixedFlapSweep.java':return H/'cases/RECOVERED_FIXED_PLUS2_SWEEP_20261103'/('run_'+receipt['run_id'])")
patch('bounded_sweep_dashboard.py','def publish(h,view,base,st,review):','def publish(h,view,base,st,review):\n E=review.get("experiment_id","BOUNDED_FIXED_PLUS2_SWEEP_20261103")')
patch('cfd_control.py',"'INLET_PRESSURE_RECOVERY_20261103']","'INLET_PRESSURE_RECOVERY_20261103','RECOVERED_FIXED_PLUS2_SWEEP_20261103']")
props=H/'audit/RECOVERED_SWEEP_RUNTIME.properties';cp=result['checkpoint'];props.write_text(f'input={source.as_posix()}\ntime_s={cp["time_s"]}\niteration={cp["iteration"]}\nstage=0\nstage_start_s=0.65\n',encoding='utf8')
original=next(j for j in cfg['jobs'] if j['id']==OLD+'_RUN')
job={**original,'id':E+'_RUN','experiment_id':E,'macro':macro.name,'macro_sha256':sha(macro),'input':str(source),'input_sha256':cp['sha256'],'initial_time_s':cp['time_s'],'runtime_properties_sha256':sha(props)}
ap=H/'audit/RECOVERED_SWEEP_APPROVAL_20261103.json';approval=dict(at=q.now(),approved_by_user=True,experiment_id=E,previous_blocked_job=st['failure_hold'],previous_case_remains_failed=True,approved_job_ids=[job['id']],source='Earlier explicit bounded-campaign authorization plus current conditional authorization to prepare safe continuation after a passed pressure-recovery verification',prepared_only=True,execution_requires_manual_start=True,recovery_review=str(D/'RECOVERY_RESULT.json'),review_sha256=sha(D/'RECOVERY_RESULT.json'),macro_sha256=job['macro_sha256'],job=job)
q.atomic(ap,approval);cfg['jobs'].append(job);cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=st['failure_hold'],evidence=str(ap));cfg.update(accept_new_jobs=False,controller_exit_requested=False);q.atomic(q.CFG,cfg)
control=(H/'tools/bounded_sweep_control.py').read_text().replace(OLD,E).replace('BoundedFixedFlapSweep.java','RecoveredFixedFlapSweep.java').replace('BOUNDED_SWEEP_APPROVAL_20261103.json','RECOVERED_SWEEP_APPROVAL_20261103.json').replace('BOUNDED_SWEEP_RUNTIME.properties','RECOVERED_SWEEP_RUNTIME.properties')
needle="def checks():\n st=q.read(q.STATE);cfg=q.read(q.CFG);q.validate(cfg)"
assert control.count(needle)==1
control=control.replace(needle,needle+"\n review=q.read(H.parent/'independent_cfd_diagnostics/INLET_PRESSURE_AUDIT_20261103/RECOVERY_RESULT.json');assert review.get('status')=='PASS','Pressure repair review is not PASS'")
needle="cfg.update(accept_new_jobs=True,controller_exit_requested=False);q.atomic(q.CFG,cfg);"
control=control.replace(needle,"work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(current_job_kind='bounded_sweep',experiment_id=E,current_case_label='Recovered C0 -> fixed+2 speed sweep',last_decision='Manual launch after passed pressure repair; unchanged guards; static acceptance requires stabilization.');q.atomic(H/'WORK_CURRENT_REVIEW.json',work)\n "+needle)
(H/'tools/recovered_sweep_control.py').write_text(control,encoding='utf8')
launcher=R/'START_RECOVERED_FLAP_SWEEP.cmd';assert not launcher.exists()
py=r'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
launcher.write_text('@echo off\r\n"'+py+'" -X utf8 "'+str(H/'tools/recovered_sweep_control.py')+'" --check\r\nif errorlevel 1 exit /b 2\r\npowershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath \''+py+'\' -ArgumentList \'-X\',\'utf8\',\'-u\',\''+str(H/'tools/recovered_sweep_control.py')+'\',\'start\'"\r\n',encoding='ascii')
for p in [H/'tools'/n for n in ['night_queue.py','night_native.py','ramp_authorization.py','bounded_sweep_auth.py','bounded_sweep_dashboard.py','recovered_sweep_control.py']]:py_compile.compile(str(p),doraise=True)
q.event('recovered_sweep_prepared_NOT_STARTED',job=job,review=str(D/'RECOVERY_RESULT.json'),backup=str(backup))
print(json.dumps(dict(prepared=True,started=False,launcher=str(launcher),checkpoint=str(source),resources=q.resources()),indent=2))

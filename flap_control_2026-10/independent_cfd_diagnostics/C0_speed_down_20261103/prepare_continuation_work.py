"""Prepare only after the native20-step review passes. Never launches STAR."""
from pathlib import Path
import sys,subprocess,hashlib,shutil,json
D=Path(__file__).resolve().parent;H=D.parents[1]/'hydro_validation_2606_20261102'
sys.path.insert(0,str(H/'tools'));import night_queue as q
E='C0_SPEED_DOWN_20261103';J=E+'_CONTINUE_TO10'
review=q.read(D/'WORK_RESULT.json');assert review['passed'] is True
st=q.read(q.STATE);cfg=q.read(q.CFG);assert st.get('active') is None and not (H/'audit/night_queue.lock').exists()
assert st['failure_hold']=='SPEED_SWEEP_PLUS2_20261103_SMOKE'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
cp=Path(review['checkpoint']['path']);assert sha(cp)==review['checkpoint']['sha256']
destdir=H/'cases/C0_speed_down_approved_20261103';destdir.mkdir(exist_ok=True)
dest=destdir/'C0_speed_down_t0690.sim';assert not dest.exists();shutil.copy2(cp,dest);assert sha(dest)==sha(cp)
meta=dict(input=dest.as_posix(),time_s=review['time_s'],iteration=review['iteration'],sha256=sha(dest),source=str(cp))
q.atomic(D/'CONTINUATION_INPUT.json',meta)
(D/'CONTINUATION_RUNTIME.properties').write_text(''.join(f'{k}={meta[k]}\n' for k in ['input','time_s','iteration','sha256']),encoding='utf8')
source=(H/'macros/C0SpeedDownSmoke.java').read_text();text=source.replace('class C0SpeedDownSmoke','class C0SpeedDownContinue')
text=text.replace('C0_speed_down_20261103/run_','C0_speed_down_20261103/continue_')
a=text.index('// Independent diagnostic:');b=text.index('for(Region r:',a)
text=text[:a]+r'''
if(!"YES".equals(System.getenv("NTNU_C0_SPEEDDOWN_ALLOWED")))throw new IllegalStateException("Scoped continuation authorization required");
Properties auth=new Properties();try(Reader r=Files.newBufferedReader(Paths.get("F:/ntnu/flap_control/independent_cfd_diagnostics/C0_speed_down_20261103/CONTINUATION_RUNTIME.properties"))){auth.load(r);}
if(!input.equals(Paths.get(auth.getProperty("input")))||Math.abs(t0-Double.parseDouble(auth.getProperty("time_s")))>1e-9||s.getSimulationIterator().getCurrentIteration()!=Integer.parseInt(auth.getProperty("iteration")))throw new IllegalStateException("Continuation checkpoint mismatch");
if(t0<.69-1e-9||t0>=1.05-1e-9)throw new IllegalStateException("Outside approved continuation interval");
''' +text[b:]
text=text.replace('for(int i=1;i<=20;i++)','for(int i=1;i<=(int)Math.round((1.05-t0)/.002);i++)')
a=text.index('if(t>=.85-1e-9)');b=text.index('if(globalStep%50==0)',a)
text=text[:a]+r'''
int globalStep=(int)Math.round((t-.65)/.002);
if(globalStep%25==0){boolean residualOk=residualGate();Files.writeString(out.resolve("convergence_latest.json"),"{\"time\":"+t+",\"residual_gate\":"+residualOk+",\"steady_validation\":false}");if(!residualOk)throw new IllegalStateException("Inner residual gate failed during speed-down");}
''' +text[b:]
text=text.replace('String status="speed_down_smoke_passed_not_scientific_validation";','if(Math.abs(s.getSolution().getPhysicalTime()-1.05)>1e-9)throw new IllegalStateException("Endpoint mismatch");String status="speed_down_to10_completed_not_steady";')
macro=H/'macros/C0SpeedDownContinue.java';assert not macro.exists();macro.write_text(text,encoding='utf8')
r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(macro)],capture_output=True,text=True,check=True);(D/'CONTINUATION_COMPILE.txt').write_text(r.stderr)
def patch(name,a,b):
 p=H/'tools'/name;t=p.read_text();assert t.count(a)==1,(name,a);shutil.copy2(p,D/('before_continuation_'+name));p.write_text(t.replace(a,b),encoding='utf8')
patch('night_native.py',"allowed['C0SpeedDownSmoke.java']=8","allowed['C0SpeedDownSmoke.java']=8\nallowed['C0SpeedDownContinue.java']=8")
patch('night_native.py',"if name=='C0SpeedDownSmoke.java':","if name in ['C0SpeedDownSmoke.java','C0SpeedDownContinue.java']:")
patch('night_queue.py',"ALLOWED.add('C0SpeedDownSmoke.java')","ALLOWED.update(['C0SpeedDownSmoke.java','C0SpeedDownContinue.java'])")
patch('night_queue.py',"j['macro']=='C0SpeedDownSmoke.java' and", "j['macro'] in ['C0SpeedDownSmoke.java','C0SpeedDownContinue.java'] and")
patch('night_queue.py',"def output_path(receipt):", "def output_path(receipt):\n if receipt['macro']=='C0SpeedDownContinue.java':return H.parent/'independent_cfd_diagnostics/C0_speed_down_20261103'/('continue_'+receipt['run_id'])")
patch('night_queue.py',"['speed_down_smoke_passed_not_scientific_validation'", "['speed_down_to10_completed_not_steady','speed_down_smoke_passed_not_scientific_validation'")
assert J not in st['jobs'] and not any(j['id']==J for j in cfg['jobs'])
job=dict(id=J,kind='c0_speeddown',experiment_id=E,approved=True,macro=macro.name,macro_sha256=sha(macro),input=str(dest),input_sha256=sha(dest),initial_time_s=review['time_s'],cpu_processes=8,angle_deg=0,progress_timeout_s=900,maximum_runtime_s=7200)
ap=H/'audit/C0_SPEED_DOWN_EXPLICIT_APPROVAL_20261103.json';approval=q.read(ap);approval['approved_job_ids'].append(J);approval.update(conditional_continuation_gate_passed=True,continuation_scope='Manual launcher only: continue same0deg speed law to t1.05/U10; then stop/save. No settling,+2/full sweep,or automatic launch now.',continuation_job=job);q.atomic(ap,approval)
cfg['jobs'].append(job);cfg.update(accept_new_jobs=False,controller_exit_requested=False);q.atomic(q.CFG,cfg)
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(last_decision='20-step C0 smoke passed. Same-law continuation to U10 prepared; NOT launched. All prior failures/full sweep remain blocked.',next='Manual START_C0_SPEED_DOWN.cmd; continuation ends at t1.05 or earlier if any guard fails. No steady10m/s acceptance.',obstacle='Full deceleration to10m/s remains untested');q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
q.atomic(D/'CONTINUATION_PREPARED.json',dict(at=q.now(),job=job,manual_start_required=True,launched=False,smoke_review=str(D/'WORK_RESULT.json'),source_copy=meta));q.event('c0_speeddown_continuation_prepared_not_launched',job=job)
print(json.dumps(dict(prepared=True,job=J,input=str(dest),end_time_s=1.05,launched=False),indent=2))

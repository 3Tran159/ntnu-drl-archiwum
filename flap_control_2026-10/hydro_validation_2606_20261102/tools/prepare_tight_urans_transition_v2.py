from pathlib import Path
import json,datetime,hashlib,subprocess,shutil,py_compile,difflib
h=Path(__file__).resolve().parents[1];state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));assert not state.get('active')
failed=h/'cases/SP_C_split0_overset/c0_tight_urans_20261103_035229'
st=json.loads((failed/'status.json').read_text(encoding='utf8'));assert st['status']=='urans_error' and st['steps']==0 and st['saved_time_s']==0
assert 'Unexpected warm relaxation' in (failed/'error.txt').read_text(encoding='utf8')
assert not (failed/'history.csv').exists()
source=h/'cases/SP_C_split0_overset/c0_tight_turbulence_second_20261103_034119/steady_checkpoint.sim'
sha=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert sha=='3575fad827e54ce942afada6d6c58a1c5cb5cd580e1da0f6065ff05f43b7fe6b'
assert (failed/'forces_failure.txt').read_text(encoding='utf8')==(source.parent/'forces_final.txt').read_text(encoding='utf8')
assert not (h.parent/'STOP_OWNED_CFD.json').exists(),'Review marker independently'
old=(h/'macros/C0TightURANS.java').read_text(encoding='utf8');s=old.replace('class C0TightURANS','class C0TightURANSV2').replace('c0_tight_urans_','c0_tight_urans_v2_')
needle='pc.disableModel(pc.getModelManager().getModel(SteadyModel.class));pc.enable(ImplicitUnsteadyModel.class);'
before='''SegregatedFlowSolver sourceFlow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);
double sourceVUrf=sourceFlow.getVelocitySolver().getUrf(),sourcePUrf=sourceFlow.getPressureSolver().getUrf();boolean sourceDynamic=sourceFlow.getVelocitySolver().getUseDynamicLocalUrf();
Files.writeString(out.resolve("pre_conversion_relaxation.txt"),"velocity="+sourceVUrf+" pressure="+sourcePUrf+" dynamic="+sourceDynamic+"\\n");
if(Math.abs(sourceVUrf-.3)>1e-12||Math.abs(sourcePUrf-.1)>1e-12||sourceDynamic)throw new IllegalStateException("Unexpected source steady relaxation: "+sourceVUrf+"/"+sourcePUrf+"/"+sourceDynamic);
'''
assert s.count(needle)==1;s=s.replace(needle,before+needle,1)
needle='SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);double oldVUrf=flow.getVelocitySolver().getUrf(),oldPUrf=flow.getPressureSolver().getUrf();if(Math.abs(oldVUrf-.3)>1e-12||Math.abs(oldPUrf-.1)>1e-12||flow.getVelocitySolver().getUseDynamicLocalUrf())throw new IllegalStateException("Unexpected warm relaxation");'
replacement='''SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);double convertedVUrf=flow.getVelocitySolver().getUrf(),convertedPUrf=flow.getPressureSolver().getUrf();boolean convertedDynamic=flow.getVelocitySolver().getUseDynamicLocalUrf();
Files.writeString(out.resolve("post_conversion_defaults.txt"),"velocity="+convertedVUrf+" pressure="+convertedPUrf+" dynamic="+convertedDynamic+"\\n");
flow.getVelocitySolver().setUseDynamicLocalUrf(false);
'''
assert s.count(needle)==1;s=s.replace(needle,replacement,1)
needle='flow.getVelocitySolver().setUrf(0.8);flow.getPressureSolver().setUrf(0.2);flow.setContinuityInitialization(false);'
s=s.replace(needle,needle+'\nif(Math.abs(flow.getVelocitySolver().getUrf()-.8)>1e-12||Math.abs(flow.getPressureSolver().getUrf()-.2)>1e-12||flow.getVelocitySolver().getUseDynamicLocalUrf())throw new IllegalStateException("Matching B relaxation failed");\nFiles.writeString(out.resolve("matched_relaxation.txt"),"velocity=0.8 pressure=0.2 dynamic=false; exact B native settings; no solution reset");',1)
macro=h/'macros/C0TightURANSV2.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
res=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert res.returncode==0,res.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
for file,needle,replacement in [('night_native.py','allowed={',"allowed={'C0TightURANSV2.java':8,"),('night_queue.py','ALLOWED={',"ALLOWED={'C0TightURANSV2.java',"),('night_dashboard.py','case={',"case={'C0TightURANSV2.java':'C0 — URANS, kontrolowane przejscie v2',")]:
 p=h/'tools'/file;t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace(needle,replacement,1)
 if file=='night_queue.py':t=t.replace('prefix={',"prefix={'C0TightURANSV2.java':'c0_tight_urans_v2_',",1)
 p.write_text(t,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=json.loads(p.read_text(encoding='utf8'));job=dict(next(j for j in cfg['jobs'] if j['id']=='c0_tight_urans_matching'))
job.update(id='c0_tight_urans_transition_v2',macro=macro.name,purpose=job['purpose']+' Transition implementation correction: validate source URFs BEFORE changing time model, record new solver defaults AFTER conversion, then explicitly match B. Prior attempt stopped with zero PDE steps, unchanged forces, time0; all strict physical guards unchanged.')
assert not any(j['id']==job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['release_failure_hold']['c0_tight_urans_matching']='Reviewed zero-step transition guard failure; exact source preserved, failure forces identical, no runtime physical limit violated. Separate v2 corrects check ordering and records both solver settings.'
cfg['controller_exit_requested']=True;tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_urans_transition_correction',failed_run=str(failed),zero_PDE_steps=True,force_exports_identical=True,source_sha256=sha,job=job,scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
(h/'audit/urans_transition_v1_v2.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='v1',tofile='v2')),encoding='utf8')
print(json.dumps(ev,indent=2))

from pathlib import Path
import json,datetime,subprocess,shutil,py_compile,hashlib,sys,re
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve()
assert run.is_relative_to(h/'cases/SP_C_split0_overset')
review=json.loads((run/'work_mapping_review.json').read_text(encoding='utf8'));assert review['technical_mapping_review_pass']
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));assert not state.get('active')
source=run/'warm_mapped_candidate.sim';digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();cache=state['checkpoint_integrity'][str(source)];assert cache['sha256']==digest and cache['native_save_complete']
s=(h/'macros/FreshC0TightInit.java').read_text(encoding='utf8').replace('class FreshC0TightInit','class ContinueC0TightWarm').replace('c0_tight_firstorder_','c0_tight_warm_')
s=s.replace('cases/SP_C_split0_overset/c0_tight_cage_v2_20261103_025110/SP_C_mesh_ready.sim',source.relative_to(h).as_posix()).replace('0db9b6252019fff169432f902f37ecdb9d4e071724b396e3c0d55cda51819643',digest)
s=s.replace('steadyResume=input.getFileName().toString().equals("steady_checkpoint.sim");','steadyResume=true;')
s=s.replace('if(!Files.readString(base.resolve("initialization_status.json")).contains("steady_initialization_incomplete"))throw new IllegalStateException("Only incomplete steady initializer may be continued");','')
s=s.replace('Only protected pre-motion mesh source allowed','Only reviewed mapped-field candidate allowed').replace('Fresh uninitialized mesh required; solved checkpoints protected','Mapped time0 must be preserved').replace('Source mesh fingerprint changed','Mapped checkpoint fingerprint changed')
assert s.count('s.getSolution().initializeSolution();')==1;s=s.replace('s.getSolution().initializeSolution();','// Preserve native stored mapped fields; no initializeSolution, clearSolution, or remeshing.')
# Preserve a concrete native readback before any numerical step.
expected=review['mapped_metrics']['pabs_min_Pa']
needle='captureComparison("fresh_initialized");verifyInitialVolumeContainment(base);'
assert needle in s
s=s.replace(needle,needle+f'''
double readP=Double.POSITIVE_INFINITY;for(String z:zones)readP=Math.min(readP,rv("HF_pabs_"+z));
if(!Double.isFinite(readP)||Math.abs(readP-({expected:.17g}))>.1)throw new IllegalStateException("Mapped pressure readback changed");
Files.writeString(out.resolve("checkpoint_readback.txt"),"native_iteration="+s.getSimulationIterator().getCurrentIteration()+" time="+s.getSolution().getPhysicalTime()+" pabs_min="+readP+" mapped_source_iteration1850; no reset");
Files.copy(base.resolve("mapping_source.json"),out.resolve("mapping_source.json"));
''')
i=s.index('Files.writeString(out.resolve("numerical_change.txt"),');j=s.index('\n',i)
description='Continue reviewed stored mapped fields on unchanged333939-cell tight-cage mesh. Source physicaltime0/nativeiteration0; its field lineage is healthy original iteration1850. No initializeSolution,clearing,remeshing,or boundary changes. Preserve FIRST_ORDER flow/SST,DISTANCE,FLUX_CORRECTION,URF.3/.1,CIoff,U18. Native mapped pressure readback and full mesh/solid containment before first step. Strict pressure12339.2148Pa,mass1e-4,zero k/omega floors and Overset errors from first block. No hydrodynamic approval until second-order URANS comparison.'
s=s[:i]+'Files.writeString(out.resolve("numerical_change.txt"),"'+description+'");'+s[j:]
macro=h/'macros/ContinueC0TightWarm.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':8,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_tight_warm_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — kontynuacja przeniesionego rozwiązania, bez resetu pól',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0)
job=dict(id='c0_tight_warm_continuation',macro=macro.name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose=description,runtime_guards=guards)
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_approved_mapped_warm_continuation',job=job,input_sha256=digest,technical_mapping_review=review['mapped_metrics'],scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v.update(at=ev['at'],obstacle='Przeniesienie pól przeszło kontrolę,pabs33,39kPa,Umax21,81m/s,masa7,66e-5,zero błędów Overset i ograniczania k/omega. Nadal trzeba ocenić stabilizację rzeczywistego przepływu i drugi rząd dokładności; różnica CL/CD niezatwierdzona.',next='Kontynuacja zachowanych przeniesionych pól na nowej siatce,8CPU,bez ponownej inicjalizacji. Oceniać siły,ciśnienie,turbulencję i łączność przed przejściem do drugiego rzędu.')
v['latest_mapped_checkpoint']=dict(path=str(source),sha256=digest,physical_time_s=0,native_iteration=0,source_field_iteration=1850,technical_mapping_pass=True,scientific_approved=False)
p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(ev,indent=2))

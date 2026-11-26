from pathlib import Path
import json,csv,sys,hashlib,datetime,re,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve();b=Path(sys.argv[2]).resolve()
assert run.is_relative_to(h/'cases/SP_C_split0_overset') and b.is_relative_to(h/'audit')
read=lambda p:json.loads(p.read_text(encoding='utf8'))
state=read(h/'NIGHT_QUEUE_STATE.json');assert not state.get('active')
status=read(run/'status.json');assert status['status'] in ['steady_diagnostic_ready','steady_initialization_incomplete']
review=read(run/'work_stage_decision.json');assert review['scientific_approved'] is False and 'URANS' in review['next']
assert read(b/'status.json')['status']=='inspection_complete'
data={}
for line in (b/'matching_numerics.txt').read_text(encoding='utf8').splitlines():
 if '=' in line:
  key,val=line.split('=',1);data[key]=val
assert data['flow_convection']==data['flow_SECOND_ORDER'] and data['SST_convection']==data['SST_SECOND_ORDER'] and data['time_discretization']==data['time_SECOND_ORDER']
assert float(data['dt_s'])==.002 and data['dynamic_velocity_urf']=='false'
vurf=float(data['velocity_urf']);purf=float(data['pressure_urf']);inner=int(data['inner_iterations'].split()[0])
assert 0<vurf<=1 and 0<purf<=1 and inner==15
source=run/'steady_checkpoint.sim';cache=state['checkpoint_integrity'][str(source)]
assert cache['native_save_complete']
sha=hashlib.file_digest(source.open('rb'),'sha256').hexdigest();assert sha==cache['sha256']
rows=list(csv.DictReader((run/'steady_iterations.csv').open()));last=rows[-1];native=int(float(last.get('native_iteration') or last['iteration']))
assert float(last['p_absolute_min_Pa'])>12339.214766776897 and float(last['mass_imbalance_relative'])<1e-4
assert all(float(last[x])==0 for x in ['omega_floor_cells','k_floor_cells','overset_error_cells']) and float(last['max_turbulent_viscosity_ratio'])<99999
audit=(run/'full_audit_final.txt').read_text(encoding='utf8');assert 'total=333939' in audit and 'errors=0' in audit and 'difficult_interpolation=0' in audit
name='C0TightURANS.java';macro=h/'macros'/name;assert not macro.exists()
header=(h/'macros/ContinueC0TightTurbulenceSecond.java').read_text(encoding='utf8').split('public void execute(){',1)[0].replace('class ContinueC0TightTurbulenceSecond','class C0TightURANS')
body=(h/'tools/tight_urans_execute.template.txt').read_text(encoding='utf8')
body='\n'.join('Files.copy(base.resolve("normalization.json"),out.resolve("normalization.json"));double buoyancy=@BUOYANCY@;' if 'java.util.regex.Matcher bm=' in line else line for line in body.splitlines())+'\n'
rb='Map<String,Double> sourceReports=new LinkedHashMap<>();StringBuilder loaded=new StringBuilder("time="+t0+" native_iteration="+s.getSimulationIterator().getCurrentIteration()+"\\n");\n'
for key,report in [('Fx_N','HF_Fx_N'),('Fz_N','HF_Fz_N'),('Mh_Nm','HF_Mh_Nm'),('CL_hydro','HF_CL_hydro'),('CD','HF_CD')]:
 value=float(last[key]);rb+=f'sourceReports.put("{report}",{value:.17g});\n'
rb+='for(Map.Entry<String,Double> e:sourceReports.entrySet()){double value=rv(e.getKey());if(!Double.isFinite(value)||Math.abs(value-e.getValue())>1e-6*Math.max(1,Math.abs(e.getValue())))throw new IllegalStateException("Source report mismatch "+e.getKey());loaded.append(e.getKey()+"="+value+"\\n");}Files.writeString(out.resolve("checkpoint_readback.txt"),loaded.toString());\n'
replacements={'SOURCE_REL':source.relative_to(h).as_posix(),'SOURCE_SHA':sha,'SOURCE_NATIVE':str(native),'READBACK_CODE':rb,'B_VURF':str(vurf),'B_PURF':str(purf),'B_INNER':str(inner),'BUOYANCY':str(read(run/'normalization.json')['buoyancy_N'])}
for key,value in replacements.items():body=body.replace('@'+key+'@',value)
assert not re.search(r'@[A-Z_]+@',body)
code=header+body;execute=code.split('public void execute(){',1)[1]
assert 'initializeSolution' not in execute and 'clearSolution' not in execute and 'generateVolumeMesh' not in execute and 'restoreMotionForUnsteady()' not in execute
macro.write_text(code,encoding='utf8')
res=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert res.returncode==0,res.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8');assert name not in s;s=s.replace('allowed={',"allowed={'"+name+"':8,",1);p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8');assert name not in s;s=s.replace('ALLOWED={',"ALLOWED={'"+name+"',",1).replace('prefix={',"prefix={'"+name+"':'c0_tight_urans_',",1)
s=s.replace("['inspection_complete','steady_diagnostic_ready','mesh_connectivity_prepared']","['inspection_complete','steady_diagnostic_ready','mesh_connectivity_prepared','urans_diagnostic_ready']")
p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8');s=s.replace('case={',"case={'"+name+"':'C0 — URANS, drugi rzad, dt0.002s',",1);p.write_text(s,encoding='utf8')
for f in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/f),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=read(p);job=dict(id='c0_tight_urans_matching',macro=name,input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='0degree URANS diagnostic from exact native'+str(native)+' fields, no initialize/reset/remesh. Match B native dt0.002s,15inner,SECOND_ORDER time/momentum/SST,URF'+str(vurf)+'/'+str(purf)+'. Restore prescribed zero motion. Strict runtime guards; every50stepcheckpoint; minimum150steps,maximum500. Force pass remains unapproved until Work residual/field/B-C review.',runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999,maximum_overset_error_cells=0))
assert not any(j['id']==job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_tight_matched_urans_prepared',job=job,source_sha256=sha,B_matching_audit=str(b),scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
print(json.dumps(ev,indent=2))

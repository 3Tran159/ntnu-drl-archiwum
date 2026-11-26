from pathlib import Path
import json,datetime,subprocess,hashlib,shutil,py_compile
h=Path(__file__).resolve().parents[1]
oldrun=h/'cases/SP_C_split0_overset/c0_refined_init_20261103_004626'
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'))
assert not state.get('active'), 'Existing owned job still active'
review=json.loads((oldrun/'work_review.json').read_text(encoding='utf8'))
assert review['last_iteration']==40 and review['field_exports']['failure']['speed_max_near_m_s']>1000
mesh=h/'cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim'
assert hashlib.file_digest(mesh.open('rb'),'sha256').hexdigest()=='35b44cb5cd54d35cf7e7b849140524b9f2be5d4ffc8b583da44495db5ba88865'
s=(h/'macros/FreshC0RefinedInit.java').read_text(encoding='utf8')
s=s.replace('class FreshC0RefinedInit','class FreshC0RelaxedInit').replace('c0_refined_init_','c0_relaxed_init_')
needle='flow.setContinuityInitTolerance(1e-6);'
assert s.count(needle)==1
s=s.replace(needle,needle+r'''
double oldVelocityUrf=flow.getVelocitySolver().getUrf(),oldPressureUrf=flow.getPressureSolver().getUrf();
boolean dynamicUrf=flow.getVelocitySolver().getUseDynamicLocalUrf();
if(dynamicUrf)throw new IllegalStateException("Unexpected dynamic velocity relaxation; review before changing");
flow.getVelocitySolver().setUrf(.3);flow.getPressureSolver().setUrf(.1);
Files.writeString(out.resolve("relaxation_change.json"),"{\"velocity_before\":"+oldVelocityUrf+",\"pressure_before\":"+oldPressureUrf+",\"velocity_after\":"+flow.getVelocitySolver().getUrf()+",\"pressure_after\":"+flow.getPressureSolver().getUrf()+",\"dynamic_velocity_relaxation\":"+dynamicUrf+",\"physical_conditions_changed\":false}");
''')
s=s.replace('Divergence guard100MPa, absCD2, absFz/qS3; final pressure gate remains12339.2148Pa.',
'Numerical remedy relative to preceding refined-mesh startup: velocity URF0.3 and pressure URF0.1, old native values recorded. No other governing settings changed. Added speed ceiling180m/s and pressure-maximum ceiling100MPa to avoid wasting work on divergence. absCD2, absFz/qS3; final pressure gate remains12339.2148Pa.')
needle='List<double[]> samples=new ArrayList<>();'
assert s.count(needle)==1
s=s.replace(needle,r'''MaxReport speedMax=s.getReportManager().createReport(MaxReport.class);speedMax.getParts().setObjects(regions);speedMax.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());
MaxReport pressureMax=s.getReportManager().createReport(MaxReport.class);pressureMax.getParts().setObjects(regions);pressureMax.setFieldFunction(s.getFieldFunctionManager().getFunction("AbsolutePressure"));
'''+needle)
s=s.replace('max_turbulent_viscosity_ratio,overset_error_cells\\n','max_turbulent_viscosity_ratio,overset_error_cells,max_speed_m_s,max_absolute_pressure_Pa\\n')
needle='w.write(","+omega+","+kfloor+","+visc+","+oe+"\\n");'
assert needle in s
s=s.replace(needle,'double umax=speedMax.getReportMonitorValue(),pmax=pressureMax.getReportMonitorValue();w.write(","+omega+","+kfloor+","+visc+","+oe+","+umax+","+pmax+"\\n");')
s=s.replace('if(!Double.isFinite(fx+fz+mh+p)||','if(!Double.isFinite(fx+fz+mh+p+umax+pmax)||umax>180||Math.abs(pmax)>1e8||')
s=s.replace('if(k%250==0){captureComparison','if(k==50){captureComparison("iter_50");}\nif(k%250==0){captureComparison')
macro=h/'macros/FreshC0RelaxedInit.java';macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8');needle="'FreshC0RefinedInit.java':8}";assert needle in s
p.write_text(s.replace(needle,"'FreshC0RefinedInit.java':8,'FreshC0RelaxedInit.java':8}"),encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8');needle="'FreshC0RefinedInit.java'}";assert needle in s
s=s.replace(needle,"'FreshC0RefinedInit.java','FreshC0RelaxedInit.java'}")
needle="'FreshC0RefinedInit.java':'c0_refined_init_',";assert needle in s
s=s.replace(needle,"'FreshC0RelaxedInit.java':'c0_relaxed_init_',"+needle);p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8');needle="case={'FreshC0RefinedInit.java'";assert needle in s
s=s.replace(needle,"case={'FreshC0RelaxedInit.java':'C0 â€” 579468 komÃ³rek, ostroÅ¼niejszy rozruch prÄ™dkoÅ›ci i ciÅ›nienia','FreshC0RefinedInit.java'");p.write_text(s,encoding='utf8')
for name in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
now=datetime.datetime.now().astimezone().isoformat()
conclusion=dict(at=now,status='rejected_startup_divergence',iterations=40,physical_time_s=0,peak_speed_m_s=1512.0220584863562,peak_speed_location='Background leading edge x.0017237,z-.00356951',native_overset_errors=0,turbulence_floor_cells=0,scientific_approved=False,checkpoint=str(oldrun/'initialization_error.sim'),next_change='Same positive mesh and physical conditions; velocity URF0.3 and pressure URF0.1, default old native values captured at execution. No failed-field reuse.')
(oldrun/'work_conclusion.json').write_text(json.dumps(conclusion,indent=2),encoding='utf8')
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_relaxed_initialization',macro=macro.name,input=str(mesh),initial_time_s=0,angle_deg=0,approved=True,purpose=conclusion['next_change']+' Bounded1500steady iterations; full fields/checkpoints; no scientific acceptance or deflections.')
assert all(j['id']!=job['id'] for j in cfg['jobs'])
cfg['jobs'].append(job);cfg['release_failure_hold']['c0_refined_initialization']='Documented failure at40: gross startup divergence at unchanged main-foil leading edge, no native Overset errors or SST floors. Preserve failed state; controlled lower-relaxation startup on same zero-step mesh.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=now,kind='work_approved_relaxed_C0_startup',job=job,previous_conclusion=conclusion,scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+now+' Refined C0 startup rejected at40iterations: Umax1512m/s at main leading edge, pmax543MPa, CD4.323. Full failure fields/checkpoint saved; no native Overset errors and no k/omega clipping. Approved separately recorded velocity/pressure URF0.3/0.1 on same mesh/physics; strict scientific gate remains. No deflections.\n')
print(json.dumps(ev,indent=2))

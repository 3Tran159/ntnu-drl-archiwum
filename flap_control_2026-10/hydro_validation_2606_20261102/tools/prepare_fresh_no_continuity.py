from pathlib import Path
import subprocess,py_compile,json,datetime,shutil
h=Path(__file__).resolve().parents[1]
s=(h/'macros/FreshC0DistanceInit.java').read_text(encoding='utf8')
s=s.replace('class FreshC0DistanceInit','class FreshC0NoContinuityInit').replace('c0_distance_fresh_','c0_fresh_noci_')
s=s.replace('flow.setContinuityInitialization(true);','flow.setContinuityInitialization(false);')
s=s.replace('Fresh initialization on protected pre-motion mesh;','Fresh initialization on protected pre-motion mesh; continuity initialization DISABLED; all other numerical settings unchanged from fresh diagnostic;')
s=s.replace('Files.writeString(out.resolve("initialization_error.txt"),e.toString());',r'''Files.writeString(out.resolve("initialization_error.txt"),e.toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"initialization_error\",\"iterations\":"+iterations+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"scientific_approved\":false,\"training_approved\":false}");''')
p=h/'macros/FreshC0NoContinuityInit.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'FreshC0DistanceInit.java':8}","'FreshC0DistanceInit.java':8,'FreshC0NoContinuityInit.java':8}");assert "'FreshC0NoContinuityInit.java':8" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'FreshC0DistanceInit.java'}","'FreshC0DistanceInit.java','FreshC0NoContinuityInit.java'}")
s=s.replace("'FreshC0DistanceInit.java':'c0_distance_fresh_',","'FreshC0NoContinuityInit.java':'c0_fresh_noci_','FreshC0DistanceInit.java':'c0_distance_fresh_',")
s=s.replace("rec['macro']=='FreshC0DistanceInit.java'","rec['macro'].startswith('FreshC0')")
s=s.replace("active['macro']=='FreshC0DistanceInit.java'","active['macro'].startswith('FreshC0')")
p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'FreshC0DistanceInit.java'","case={'FreshC0NoContinuityInit.java':'C0 — czysty start bez wstępnej inicjalizacji ciągłości','FreshC0DistanceInit.java'")
s=s.replace('Następny test: czysta inicjalizacja 0° na zapisanej siatce sprzed testu ruchu, bez przebudowy geometrii.','Czysta inicjalizacja z procedurą ciągłości rozbiegła się po40 iteracjach. Następny test wyłącza wyłącznie tę procedurę; ta sama zapisana siatka sprzed testu ruchu.')
p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_fresh_no_continuity_init',macro='FreshC0NoContinuityInit.java',input=str(h/'cases/SP_C_split0_overset/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='Diagnose divergent continuity initialization: disable only continuity pre-initialization on same protected uninitialized mesh; no inherited failed fields.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg.setdefault('release_failure_hold',{})['c0_distance_fresh_initialization']='Work observed initialization divergence at40 iterations; failed output preserved. New fresh diagnostic disables continuity initialization only, never restarts failed fields.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_scientific_decision',previous_job='c0_distance_fresh_initialization',conclusion='rejected_initialization_diverged_40_iterations',next_job=job,scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' Fresh DISTANCE startup diverged after40 iterations; native guard saved initialization_error.sim and exited. Initial continuity procedure alone generated pabs approximately -2.37 MPa to13.6 MPa. Next controlled diagnostic: disable continuity initialization, same source hash, physics and mesh. No accepted data.\n')
print(json.dumps(ev,indent=2))

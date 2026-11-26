from pathlib import Path
import subprocess,json,datetime,py_compile,shutil,hashlib
h=Path(__file__).resolve().parents[1];folder=h/'cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837'
review=json.loads((folder/'work_mesh_review.json').read_text(encoding='utf8'));status=json.loads((folder/'status.json').read_text(encoding='utf8'))
assert review['mesh_review_pass'] and review['background']['identity_pass']
assert status['status']=='mesh_connectivity_prepared' and status['solver_steps']==0 and status['cells']==579468
assert all(r['error_cells']==0 and r['difficult_cells']==0 for r in review['regions'].values())
source=folder/'SP_C_mesh_ready.sim';digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
s=(h/'macros/FreshC0DistanceInit.java').read_text(encoding='utf8').replace('class FreshC0DistanceInit','class FreshC0RefinedInit').replace('c0_distance_fresh_','c0_refined_init_')
s=s.replace('cases/SP_C_split0_overset/SP_C_mesh_ready.sim','cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim')
s=s.replace('8d4692832503adba9a8dca8b1583c56ea57a6f5979c2887b3dca1a70bb8f8eb6',digest).replace('361532','579468')
old='if(conservation.getOversetConservationOption().getSelected()==OversetConservationOption.Type.NONE.getValue())conservation.getOversetConservationOption().setSelected(OversetConservationOption.Type.FLUX_CORRECTION);'
assert old in s;s=s.replace(old,'conservation.getOversetConservationOption().setSelected(OversetConservationOption.Type.NONE);')
s=s.replace('Fresh initialization on protected pre-motion mesh; static 0 degrees; DISTANCE interpolation and flux correction. Same geometry and physical boundary conditions. Steady initialization only; no time reset of a solved checkpoint; no mesh regeneration. All results diagnostic, not training.','Fresh initialization on native-audited579468-cell overlap-refined mesh; static0. DISTANCE retained. Conservation NONE during initial steady warmup, as in historical C startup; continuity initialization=true100 iterations. Before any comparison approval, restore FLUX_CORRECTION and run URANS at matched settings. Same geometry/physical conditions; no mesh regeneration. Initial pseudo-iterations may have unphysical pressure and are never training data. Divergence guard100MPa, absCD2, absFz/qS3; final pressure gate remains12339.2148Pa.')
s=s.replace('Math.abs(fx)>1e7||Math.abs(fz)>1e7||Math.abs(p)>1e9','Math.abs(fx)>7711.2||Math.abs(fz)>11566.8||Math.abs(p)>1e8')
s=s.replace('if(safe&&Math.max(Math.abs(c1-c0)', 'double m1=mean(samples,n-10,n,4),m0=mean(samples,n-20,n-10,4),mm=mean(samples,n-30,n-20,4);boolean mhStable=Math.max(Math.abs(m1-m0),Math.abs(m0-mm))<.01*Math.max(.01,Math.abs(m1));\nif(safe&&mhStable&&Math.max(Math.abs(c1-c0)')
s=s.replace('Files.writeString(out.resolve("initialization_error.txt"),e.toString());s.saveState',
r'''Files.writeString(out.resolve("initialization_error.txt"),e.toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"initialization_error\",\"iterations\":"+iterations+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"scientific_approved\":false,\"training_approved\":false}");try{captureFields("failure");captureComparison("failure");}catch(Exception ex){Files.writeString(out.resolve("failure_export_error.txt"),ex.toString());}s.saveState''')
p=h/'macros/FreshC0RefinedInit.java';p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'PrepareC0OverlapBand.java':8}","'PrepareC0OverlapBand.java':8,'FreshC0RefinedInit.java':8}");assert "'FreshC0RefinedInit.java':8" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'PrepareC0OverlapBand.java'}","'PrepareC0OverlapBand.java','FreshC0RefinedInit.java'}").replace("'PrepareC0OverlapBand.java':'c0_overlap_band05mm_',","'FreshC0RefinedInit.java':'c0_refined_init_','PrepareC0OverlapBand.java':'c0_overlap_band05mm_',")
s=s.replace("'C0 fresh DISTANCE initialization, 361532 cells'","'C0 steady initialization; mesh size recorded in the source mesh review'")
p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'PrepareC0OverlapBand.java'","case={'FreshC0RefinedInit.java':'C0 — rozruch na sprawdzonej siatce579468 komórek','PrepareC0OverlapBand.java'")
s=s.replace('Następny etap: lokalna siatka1mm w obszarze nakładania przed zawiasem, przy oryginalnej interpolacji LinearQuasi2D. Najpierw pełna kontrola łączności i tożsamości siatki tła.','Siatka z wewnętrzną strefą0,5mm przeszła pełny audyt:579468 komórek,0 błędów i trudnych interpolacji,3444 akceptory DISTANCE. Wszystkie304810 komórek tła zgodne z kontrolą. Trwa diagnostyczny rozruch; korekta strumieni NONE tylko w tej fazie. Przed akceptacją konieczny powrót do zgodnych ustawień URANS i FLUX_CORRECTION.')
p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
job=dict(id='c0_refined_initialization',macro='FreshC0RefinedInit.java',input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='Positive native/Work mesh audit on579468 cells; steady numerical warmup only with DISTANCE, conservation NONE and continuity initialization enabled. Same geometry/U18/rho1000/mu.001/SST. Restore FLUX_CORRECTION and matched URANS before scientific acceptance. No deflections.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_approved_refined_C0_startup',job=job,input_sha256=digest,mesh_review=str(folder/'work_mesh_review.json'),native_cells=579468,background_identity=True,native_errors=0,difficult_cells=0,scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' Inner0.5mm overlap mesh PASSED:579468 cells,3444 DISTANCE acceptors,error0,difficult0,positive volumes/Q,background304810 identical. Approved bounded steady initialization on8CPU; conservation NONE during startup and continuity initialization on, matching historical startup strategy. This does not approve forces; requires subsequent FLUX_CORRECTION/URANS comparison plus full fields/residuals/pressure review. Checkpoints250iter,cap1500,convergenceCL/CD/Mh and pressure/mass windows.\n')
print(json.dumps(ev,indent=2))

from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active')
s=(h/'macros/PrepareC0WallLayersCold.java').read_text(encoding='utf8').replace('class PrepareC0WallLayersCold','class PrepareC0WallLayersZeroStorage').replace('c0_layers36_cold_','c0_layers36_zero_storage_')
needle='s.getSolution().initializeSolution();';assert s.count(needle)==1
s=s.replace(needle,'if(s.getSimulationIterator().getCurrentIteration()!=0||Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Never clear any progressed checkpoint");s.getSolution().clearSolution(Solution.Clear.History,Solution.Clear.Fields,Solution.Clear.Mesh);'+needle)
s=s.replace('Source zero-iteration uniform-field mesh only;','Source zero-iteration uniform-field mesh only; explicitly clear initial storage and reset zero-time mesh position before initialization to force native reassembly;')
s=s.replace('\\\"field_storage_initial_only\\\":true','\\\"field_storage_initial_only\\\":true,\\\"zero_iteration_storage_rebuilt\\\":true')
macro=h/'macros/PrepareC0WallLayersZeroStorage.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_layers36_zero_storage_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — pełna inicjalizacja łączności na kopii zerowej',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
job=dict(id='c0_wall_layers36_zero_storage',macro=macro.name,input=str(h/'cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='1CPU zero-PDE-step connectivity test on exact zero-iteration mesh source only. Explicitly clear uniform initial fields/history/zero-time mesh storage and initialize with36protected main-wall layers. Repeated initialize alone retained old assembly. No progressed hydro checkpoint can pass source/time/iteration guards. Native geometry/cell identity and connectivity checked before any reuse.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_initial_storage_connectivity_control',job=job,scientific_approved=False,documentation='Installed2606 GUID-9FBDF4AF-B3A3-4F93-A55D-A585CECD1346: reinitialization requires clearing solution storage. This copy is strictly iteration0/time0; the source1850 solution is untouched.',prior_outcome='Calling initializeSolution on already initialized zero-step storage retained exact old statuses. Previous test did not prove fresh assembly.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['documentation']+' '+ev['prior_outcome']+'\n')
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=ev['at'];v['next']='Pełne odbudowanie początkowej łączności na kopii siatki z zerową iteracją,1CPU,bez kroków przepływu. Poprzednia inicjalizacja nie usuwała istniejących danych łączności. Zapisane rozwiązanie1850 pozostaje punktem powrotu.';p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(ev,indent=2))

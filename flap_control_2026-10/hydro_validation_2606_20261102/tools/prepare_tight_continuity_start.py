from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1]
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));assert not state.get('active')
s=(h/'macros/FreshC0TightInit.java').read_text(encoding='utf8')
s=s.replace('class FreshC0TightInit','class FreshC0TightContinuityInit').replace('c0_tight_firstorder_','c0_tight_continuity_')
assert s.count('flow.setContinuityInitialization(false);')==1
s=s.replace('flow.setContinuityInitialization(false);','flow.setContinuityInitialization(true);')
assert s.count('s.getSolution().initializeSolution();')==1
s=s.replace('s.getSolution().initializeSolution();','''if(s.getSimulationIterator().getCurrentIteration()!=0||Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Never clear a progressed flow checkpoint");
s.getSolution().clearSolution(Solution.Clear.History,Solution.Clear.Fields,Solution.Clear.Mesh);
note("Actual zero-step field-storage reinitialization with continuity initialization100, tolerance1e-6. No resolved checkpoint reset.");
s.getSolution().initializeSolution();''')
s=s.replace('continuity preinitialization disabled','continuity initialization100 enabled; initial uniform zero-step field storage explicitly cleared to activate native initialization')
s=s.replace('True active volume-cell containment checked before first PDE step','True active volume-cell containment checked before first PDE step. Exact mesh source iteration0 only. Prior uniform-start attempt failed strict pressure guard at10iterations with high-pressure/velocity anomalies at leading edge x~0, away from Overset. This diagnostic changes initialization only; installed2606 docs GUID-E7FF479A-2CDC-43B6-AC75-34C44E761591 and GUID-3034290A-4D64-46D4-9750-B027F39D4E6F')
macro=h/'macros/FreshC0TightContinuityInit.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':8,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_tight_continuity_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — kontrola rozruchu z inicjalizacją ciągłości',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'));previous=next(j for j in cfg['jobs'] if j['id']=='c0_tight_firstorder_initialization')
job=dict(previous,id='c0_tight_continuity_initialization',macro=macro.name,purpose='Initialization-only numerical remedy: true clear of initial uniform storage on exact zero-iteration mesh source; steady continuity initialization100,tolerance1e-6 enabled. Same333939-cell mesh and physical conditions,first-order flow/SST,DISTANCE,flux correction,URF.3/.1. Native counters,solid containment and full mesh audited before PDE. Strict pressure/mass/turbulence/Overset guards unchanged. Failure at10 of prior uniform start located at leading edge, not the former overlap zone.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg['release_failure_hold'][previous['id']]='Preserved pressure-failed uniform-start fields; do not resume them. Separate original zero-step source and documented continuity-initialization diagnostic. Strict guards unchanged.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_tight_continuity_initialization',job=job,scientific_approved=False,source_is_zero_iteration=True)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v.update(at=ev['at'],obstacle='Rozruch z jednorodnego pola prędkości przekroczył próg ciśnienia po10 iteracjach:pabs−1,309MPa,Umax43,13m/s przy krawędzi natarcia,x≈0. Zero błędów Overset i ograniczania k/omega. Próba odrzucona; to odrębny problem inicjalizacji,nie dowód wadliwej nowej łączności.',next='Kontrola rzeczywistej inicjalizacji ciągłości na oryginalnej kopii siatki zerowej. Ta sama fizyka i siatka,te same ścisłe progi. Zachowany checkpoint1850 nadal nietknięty.')
p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(ev,indent=2))

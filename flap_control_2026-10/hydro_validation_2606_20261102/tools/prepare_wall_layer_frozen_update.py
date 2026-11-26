from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active')
previous=h/'cases/SP_C_split0_overset/c0_layers36_recut_20261103_015428'
assert not json.loads((previous/'work_wall_layer_audit.json').read_text())['connectivity_changed']
assert json.loads((previous/'work_native_wall_containment.json').read_text())['active_centers_outside_native_solids']
s=(h/'macros/PrepareC0WallLayersRecut.java').read_text(encoding='utf8').replace('class PrepareC0WallLayersRecut','class PrepareC0WallLayersFrozen').replace('c0_layers36_recut_','c0_layers36_frozen_')
needle='checkPose("after_layer_protection");';assert s.count(needle)==1
update=r'''
if(s.getSimulationIterator().getCurrentIteration()!=1850)throw new IllegalStateException("Unexpected saved native iteration");
List<Solver> frozenForConnectivity=new ArrayList<>();
try{
for(Solver sol:s.getSolverManager().getObjects())if(sol instanceof SegregatedFlowSolver||sol.getClass().getName().toLowerCase(Locale.ROOT).contains("turb")){if(sol.getFrozen())throw new IllegalStateException("Source solver unexpectedly frozen");sol.setFrozen(true);frozenForConnectivity.add(sol);}
if(frozenForConnectivity.size()<2)throw new IllegalStateException("Flow and turbulence freeze not verified");
for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())c.setIsUsed(false);
s.getSimulationIterator().step(1);
}finally{for(Solver sol:frozenForConnectivity)sol.setFrozen(false);}
if(s.getSimulationIterator().getCurrentIteration()!=1851||Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Frozen step must increment iteration once without advancing physical time");
Files.writeString(out.resolve("frozen_connectivity_update.json"),"{\"native_iteration_before\":1850,\"native_iteration_after\":1851,\"frozen_iterator_steps\":1,\"flow_solution_steps\":0,\"physical_time_s\":0,\"solvers_restored\":true}");
'''
s=s.replace(needle,update+'\n'+needle)
s=s.replace('Source native iteration1850; zero solver steps;','Source native iteration1850; one iterator step with flow/turbulence frozen, saved native iteration1851; zero flow solution steps;')
s=s.replace('\\\"source_native_iteration\\\":1850,','\\\"source_native_iteration\\\":1850,\\\"native_iteration\\\":1851,\\\"frozen_iterator_steps\\\":1,')
macro=h/'macros/PrepareC0WallLayersFrozen.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_layers36_frozen_',",1)
old="v.update(iteration=int(row['iteration']),steady_initialization=True,operation='STEADY_INITIALIZATION')"
assert old in t;t=t.replace(old,"v.update(iteration=int(row.get('native_iteration') or row['iteration']),additional_iterations=int(row['iteration']),steady_initialization=True,operation='STEADY_INITIALIZATION')")
p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — aktualizacja Overset przy zamrożonym przepływie',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
job=dict(id='c0_wall_layers36_frozen',macro=macro.name,input=str(h/'cases/SP_C_split0_overset/c0_flux_recovery_20261103_012140/steady_checkpoint.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='1CPU single frozen-flow/turbulence iterator step to evaluate deferred connectivity update after36 main-wall active layers. Source native1850; expected1851,time0. No physical solver steps, no clear/initialization/remeshing. Native/geometry audit required before any flow recovery.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_frozen_connectivity_update',job=job,scientific_approved=False,prior_outcome='Reset+initialize did not change any cell statuses; native wall vertex containment passes with zero active centers inside either solid. Isolate deferred kernel update with all flow/turbulence solvers frozen, retain physical time0.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['prior_outcome']+'\n')
print(json.dumps(ev,indent=2))

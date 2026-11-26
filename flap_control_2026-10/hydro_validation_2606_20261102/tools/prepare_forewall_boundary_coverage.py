from pathlib import Path
import json,datetime,subprocess,shutil,py_compile
h=Path(__file__).resolve().parents[1];state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text());assert not state.get('active')
review=json.loads((h/'cases/SP_C_split0_overset/c0_forewall36_20261103_022619/work_native_vertex_delta.json').read_text());assert review['main']['after']['missing_count']==2 and review['main']['partitioned']['missing_count']==0
s=(h/'macros/PrepareC0ForewallLayers.java').read_text(encoding='utf8').replace('class PrepareC0ForewallLayers','class PrepareC0ForewallCoverage').replace('c0_forewall36_','c0_forewall36_coverage_')
needle='target.getConditions().get(DynamicOversetBehaviour.class).setSelected(DynamicOversetBehaviour.Type.ALWAYS_ACTIVE);';assert s.count(needle)==1
s=s.replace(needle,'for(Boundary b:fixed)if(b!=target){b.getConditions().get(DynamicOversetBehaviour.class).setSelected(DynamicOversetBehaviour.Type.ALWAYS_ACTIVE);b.getValues().get(NumActiveLayers.class).setNumLayers(1);}\n'+needle)
s=s.replace('aft main wall,hinge arc and flap boundaries retained.','aft main wall and hinge arc ALWAYS_ACTIVE1layer; flap boundaries retained. All physical wall vertices must remain in active-wall export.')
s=s.replace('\\\"native_wall_partition_only\\\":true','\\\"native_wall_partition_only\\\":true,\\\"other_main_wall_layers\\\":1')
# Export complete failed mesh information immediately; no extra solve/reassembly, no loosened guards.
needle='}catch(Exception e){try{Files.writeString(out.resolve("preparation_error.txt"),e.toString());';assert needle in s
s=s.replace(needle,'}catch(Exception e){try{try{auditFull("failure",579468);}catch(Exception diag){Files.writeString(out.resolve("failure_audit_diagnostic.txt"),diag.toString());}Files.writeString(out.resolve("preparation_error.txt"),e.toString());')
macro=h/'macros/PrepareC0ForewallCoverage.java';assert not macro.exists();macro.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for n in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/n,backup/n)
p=h/'tools/night_native.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('allowed={',"allowed={'"+macro.name+"':1,",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_queue.py';t=p.read_text(encoding='utf8');assert macro.name not in t;t=t.replace('ALLOWED={',"ALLOWED={'"+macro.name+"',",1).replace('prefix={',"prefix={'"+macro.name+"':'c0_forewall36_coverage_',",1);p.write_text(t,encoding='utf8')
p=h/'tools/night_dashboard.py';t=p.read_text(encoding='utf8').replace('case={',"case={'"+macro.name+"':'C0 — ochrona przedniej części i ciągłość pozostałej ściany',",1);p.write_text(t,encoding='utf8')
for n in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/n),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text())
job=dict(id='c0_forewall36_coverage_audit',macro=macro.name,input=str(h/'cases/SP_C_split0_overset/c0_overlap_band05mm_20261103_003837/SP_C_mesh_ready.sim'),initial_time_s=0,angle_deg=0,approved=True,purpose='1CPU zero-flow-step audit:forewallx<0.80m36active layers; remaining main NativeSkin and HingeArc1active layer,flap unchanged. Prior nativepass had two missing active-wall vertices atx0.9416..0.9418,so not flow-approved. Exact original mesh/physical geometry must match; all physical wall vertices required plus zero errors/difficult donors/solid intrusion. Source zero-iteration only; no solved checkpoint reset.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_forewall_coverage_audit',job=job,scientific_approved=False,prior_outcome='Localized36 native pass:370567active,205599inactive,3302acceptors,0error/difficult; all579468cell centers/volumes exactlyunchanged. However main active-wall export lost2vertices near lower hinge; hold until coverage explained/resolved. Partition itself preserved all1163vertices.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' '+ev['prior_outcome']+'\n')
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=ev['at'];v['next']='Sprawdzenie pełnej aktywnej powierzchni głównego płata:36warstw przy przedniej części,1warstwa przy pozostałych ścianach. Poprzednia lokalna ochrona miała0błędów i niezmienioną siatkę,ale eksport aktywnej ściany pomijał2wierzchołki przy zawiasie. Bez obliczeń przepływu.';p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(ev,indent=2))

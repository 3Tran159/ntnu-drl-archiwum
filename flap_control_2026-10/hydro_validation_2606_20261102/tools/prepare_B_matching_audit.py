from pathlib import Path
import json,datetime,shutil,py_compile,hashlib
h=Path(__file__).resolve().parents[1];name='InspectBMatchingNumerics.java';stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
source=h/'cases/SP_B_split0_fixed/SP_B_split0_stabilized_2606.sim'
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));assert not state.get('active'),'Wait for owned native job to finish'
assert (h/'macros/compiled/macro/InspectBMatchingNumerics.class').is_file()
backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8');assert name not in s
s=s.replace('allowed={',"allowed={'"+name+"':1,",1)
s=s.replace("assert name=='InspectHydroComparison.java' or variant=='SP_C'","assert name in ['InspectHydroComparison.java','InspectBMatchingNumerics.java'] or variant=='SP_C'")
p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8');assert name not in s
s=s.replace('ALLOWED={',"ALLOWED={'"+name+"',",1)
s=s.replace("def output_path(receipt):","def output_path(receipt):\n if receipt['macro']=='InspectBMatchingNumerics.java':return H/'audit'/('matching_B_'+receipt['run_id'])",1)
p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8');s=s.replace('case={',"case={'"+name+"':'B0 — odczyt ustawien referencji',",1);p.write_text(s,encoding='utf8')
for f in ['night_native.py','night_queue.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/f),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=json.loads(p.read_text(encoding='utf8'));job=dict(id='b0_matching_numerics_audit',macro=name,input=str(source),initial_time_s=.3,angle_deg=0,approved=True,purpose='Read-only native audit of B reference: actual URFs, schemes,dt,inner iterations,residual scales and reports.0solver steps,no .sim save,no changes to source. Required for an explicitly matched C0 URANS diagnostic.')
assert not any(j['id']==job['id'] for j in cfg['jobs'])
cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
event=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_B_matching_readonly_audit_prepared',job=job,source_sha256=hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),scientific_approved=False)
(h/'audit/B_matching_audit_input.json').write_text(json.dumps(event,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(event)+'\n')
print(json.dumps(event,indent=2))

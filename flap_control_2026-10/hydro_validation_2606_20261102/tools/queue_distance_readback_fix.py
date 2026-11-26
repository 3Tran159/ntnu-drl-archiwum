from pathlib import Path
import json,datetime,os,hashlib
from night_queue import processes
h=Path(__file__).resolve().parents[1];st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));failed=st['jobs']['c0_distance_interpolation'];assert st.get('active') is None and failed['state']=='failed'
assert not any(p['ownedBatch'] for p in processes()) and not st['last_metrics'].get('owned_active_pids')
err=(Path(failed['output'])/'error.txt').read_text(encoding='utf8');assert 'Saved control solution must be initialized; no reset allowed' in err and failed['macro_status']['steps']==0
source=h/'cases/SP_C_split0_overset/c0_inner40_20261102_223940/checkpoint.sim'
assert hashlib.file_digest(source.open('rb'),'sha256').hexdigest()=='c0f2dbd97b39f82fac4b7a8f2a517ad9cf81db0133ea7f7d1e423d7c214ac0f9'
at=datetime.datetime.now().astimezone().isoformat();cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));assert not any(j['id']=='c0_distance_interpolation_readback' for j in cfg['jobs'])
reason='Initial isInitialized query occurred before native mesh/field loading. Replace this guard with exact saved-time and Fx/Fz/Mh/CL/CD readback against source history. No initializeSolution, clearSolution or remesh call. Previous launch solved zero steps; original control checkpoint retained.'
cfg['release_failure_hold']['c0_distance_interpolation']=dict(at=at,reason=reason)
cfg['jobs'].append(dict(id='c0_distance_interpolation_readback',macro='C0DistanceInterpolationTest.java',input=str(source),approved=True,initial_time_s=.5184,angle_deg=0,purpose='Same single-change distance interpolation diagnostic; fixed field-loading guard with numerical readback verification. 8CPU, no GPU, max150 steps; no angles.'))
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=at,kind='corrected_diagnostic_guard',reason=reason,job='c0_distance_interpolation_readback',scientific_gate=False))+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+at+'\n'+reason+'\n')
print(json.dumps(dict(at=at,approved_job='c0_distance_interpolation_readback',source=str(source),change=reason),indent=2))

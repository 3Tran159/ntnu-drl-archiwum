from pathlib import Path
import json,datetime,os,hashlib
from night_queue import processes
h=Path(__file__).resolve().parents[1];st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));failed=st['jobs']['c0_distance_interpolation_readback'];assert st.get('active') is None and failed['state']=='failed'
assert not any(p['ownedBatch'] for p in processes()) and not st['last_metrics'].get('owned_active_pids')
out=Path(failed['output']);err=(out/'error.txt').read_text(encoding='utf8');assert 'Property key (AutoNormalizeIndex) does not exist' in err and failed['macro_status']['steps']==0
readback=(out/'saved_solution_readback.txt').read_text(encoding='utf8');assert 'initializeSolution_called=false' in readback
source=h/'cases/SP_C_split0_overset/c0_inner40_20261102_223940/checkpoint.sim';digest=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
assert digest=='c0f2dbd97b39f82fac4b7a8f2a517ad9cf81db0133ea7f7d1e423d7c214ac0f9'
at=datetime.datetime.now().astimezone().isoformat();cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));jobid='c0_distance_interpolation_metadata_fixed';assert not any(j['id']==jobid for j in cfg['jobs'])
reason='Saved physical time/forces successfully re-read without initialization; optional residual accessor AutoNormalizeIndex refers to absent native property. Removed this accessor; normalization factor and residual exports retained, optional errors explicitly recorded. Zero steps were solved; scientific gate remains false.'
cfg['release_failure_hold']['c0_distance_interpolation_readback']=dict(at=at,reason=reason)
cfg['jobs'].append(dict(id=jobid,macro='C0DistanceInterpolationTest.java',input=str(source),approved=True,initial_time_s=.5184,angle_deg=0,purpose='Single-change interpolation diagnostic with native readback verified; corrected optional residual metadata export. Max8CPU/noGPU/max150steps.'))
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
evidence=dict(at=at,checkpoint=str(source),sha256=digest,native_reopen_verified=True,physical_time_s=.5184,evidence=str(out/'saved_solution_readback.txt'),initialize_solution_called=False,source_fields=[str(out/'Background_control_source_volume.csv'),str(out/'FlapOverset_control_source_volume.csv')],scientific_approved=False)
(h/'validation/C0_inner40_checkpoint_readback.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=at,kind='correct_optional_metadata_accessor',reason=reason,job=jobid,scientific_gate=False))+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+at+'\n'+reason+'\n')
print(json.dumps(dict(at=at,job=jobid,source_checkpoint_native_read_verified=True,scientific_gate=False),indent=2))

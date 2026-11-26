from pathlib import Path
import json,datetime,hashlib,os
from night_queue import processes
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_inner40_20261102_223940';cp=run/'checkpoint.sim'
st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));job=st['jobs']['c0_inner40_sensitivity']
assert st.get('active') is None and job['state']=='failed' and job['macro_status']['status']=='paused_by_marker'
assert not any(p['ownedBatch'] for p in processes()),'Owned STAR still active'
assert not st['last_metrics'].get('owned_active_pids')
native=json.loads((run/'status.json').read_text(encoding='utf8'))
assert native['steps']>=100 and native['pressure_violations']==0 and abs(native['saved_time_s']-.5184)<1e-9
review=json.loads((run/'work_review.json').read_text(encoding='utf8'))
assert review['samples']==108 and all(review['whole_run_guards'].values()) and all(w.get('force_window_pass') for w in review['window_results'][-3:])
audit=(run/'full_audit_final.txt').read_text(encoding='utf8')
assert 'total=361532' in audit and 'errors=0 difficult_interpolation=0' in audit
digest=hashlib.file_digest(cp.open('rb'),'sha256').hexdigest()
assert digest=='c0f2dbd97b39f82fac4b7a8f2a517ad9cf81db0133ea7f7d1e423d7c214ac0f9'
at=datetime.datetime.now().astimezone().isoformat()
marker=(h.parent/'STOP_OWNED_CFD.json').resolve()
assert marker.parent==h.parent.resolve()
data=json.loads(marker.read_text(encoding='utf8'));assert data['source']=='work_inner40_diagnostic_concluded'
dest=(h/'audit/STOP_inner40_concluded_20261102_2308.json').resolve()
assert dest.is_relative_to(h.resolve()) and not dest.exists()
marker.rename(dest)
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));assert not any(j['id']=='c0_distance_interpolation' for j in cfg['jobs'])
cfg['release_failure_hold']['c0_inner40_sensitivity']=dict(at=at,reason='Intentional Work conclusion after108 steps, 3 stable windows and full final connectivity audit. Original paused_by_marker/qualification=false retained; only diagnostic next test approved.',evidence=str(run/'work_review.json'))
cfg['jobs'].append(dict(id='c0_distance_interpolation',macro='C0DistanceInterpolationTest.java',input=str(cp),approved=True,initial_time_s=native['saved_time_s'],angle_deg=0,purpose='Isolate interpolation only: LinearQuasi2D to distance weighted. Same 361532 mesh, U18, SST, dt.002,40inner; no time/solution reset; max150 steps. Investigate omega clipping/pressure defect; scientific gate remains false.',input_sha256=digest))
cfg['controller_exit_requested']=True
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
decision=dict(at=at,kind='work_approved_diagnostic',job='c0_distance_interpolation',source_checkpoint=str(cp),source_sha256=digest,source_time_s=native['saved_time_s'],cpu=8,gpu=False,reason='40-inner control did not remove B/C bias. Test interpolation on same mesh before changing resolution.',scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(decision)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+at+'\nInner40 saved at t=.5184 (108 steps), SHA256 '+digest+'. Native exit0, no owned STAR children. Intentional paused status retained.\nNext approved: C0 distance-weighted interpolation only; no angles. Full fields and residual normalization exported before change and every25 steps.\n')
print(json.dumps(decision,indent=2))

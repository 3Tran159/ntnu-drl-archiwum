from pathlib import Path
import json,datetime,os,hashlib
from night_queue import processes
h=Path(__file__).resolve().parents[1];st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));old='c0_distance_interpolation_metadata_fixed';rec=st['jobs'][old]
assert st.get('active') is None and rec['macro_status']['status']=='paused_by_marker'
assert not any(p['ownedBatch'] for p in processes()) and not st['last_metrics'].get('owned_active_pids')
cp=Path(rec['output'])/'checkpoint.sim';digest=hashlib.file_digest(cp.open('rb'),'sha256').hexdigest()
assert digest=='e3594c9b927545954e305d5b062672dec93f3a418df2a1ebe99885b6c2c5f375'
marker=(h.parent/'STOP_OWNED_CFD.json').resolve();assert marker.parent==h.parent.resolve()
assert json.loads(marker.read_text(encoding='utf8'))['source']=='work_distance_remedy_rejected'
dest=(h/'audit/STOP_distance_remedy_rejected_20261102_2340.json').resolve();assert dest.is_relative_to(h.resolve()) and not dest.exists();marker.rename(dest)
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'));at=datetime.datetime.now().astimezone().isoformat()
cfg['release_failure_hold'][old]=dict(at=at,reason='Intentional scientific rejection of remedy; partial result/paused status preserved. Only read-only setup audits authorized next, zero flow steps.')
for id,path,t in [('c0_distance_native_setup',cp,.6644),('b0_native_setup',h/'cases/SP_B_split0_fixed/SP_B_split0_stabilized_2606.sim',.3)]:
 assert not any(j['id']==id for j in cfg['jobs']);cfg['jobs'].append(dict(id=id,macro='InspectHydroComparison.java',input=str(path),approved=True,initial_time_s=t,angle_deg=0,purpose='Read-only frozen-solver/model/motion/wall status comparison. 1CPU, no solution steps or simulation saves.'))
tmp=h/'NIGHT_QUEUE.json.tmp';tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');os.replace(tmp,h/'NIGHT_QUEUE.json')
d=dict(at=at,kind='work_readonly_audits',checkpoint=str(cp),sha256=digest,saved_time_s=.6644,flow_solver_stopped=True,partial_steps=73,next=['c0_distance_native_setup','b0_native_setup'],scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(d)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+at+'\nDistance remedy rejected after73steps, saved t=.6644, native exit0, no owned solver children. SHA256 '+digest+'. Native final all361532cells:0errors,0difficult,all2559acceptors distance weighted. Physical/accuracy qualification incomplete. Next: C/B read-only setup audits only.\n')
print(json.dumps(d,indent=2))

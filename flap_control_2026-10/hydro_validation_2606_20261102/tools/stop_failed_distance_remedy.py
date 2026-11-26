from pathlib import Path
import json,datetime
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_distance_20261102_232050'
r=json.loads((run/'work_review.json').read_text(encoding='utf8'))
assert r['samples']>=50 and r['delta_B_percent']['CL_hydro']>10 and r['delta_B_percent']['CD']<-5
assert r['field_exports']['step_50']['omega_floor_cells']>r['field_exports']['control_source']['omega_floor_cells']*1.2
assert r['field_exports']['step_50']['meanflow_p0_max_near_Pa']>400000
at=datetime.datetime.now().astimezone().isoformat()
d=dict(at=at,kind='work_rejected_remedy',case=str(run),reason='Distance interpolation preserves valid connectivity but does not cure anomalous fields: at step50 omega-floor1368 versus1087 control; local mean-flow energy screen425kPa versus164kPa B. Last25 CL+15.08%,CD-10.84% relative B. Do not continue for a formal force-window pass.',decision='Graceful stop after current physical step with final full audit, field exports, and unique checkpoint. Mark diagnostic unsuccessful/incomplete qualification, never approved.',next='Read-only native solver frozen/model/motion/wall-status audit; then decide between clean-state control and overlap-resolution repair.',scientific_gate=False)
marker=h.parent/'STOP_OWNED_CFD.json';assert not marker.exists()
with marker.open('x',encoding='utf8') as f:json.dump(dict(source='work_distance_remedy_rejected',at=at,reason=d['reason']),f,indent=2)
(run/'work_rejection.json').write_text(json.dumps(d,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(d)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+at+'\n'+d['reason']+'\n'+d['decision']+'\nNext: '+d['next']+'\n')
print(json.dumps(d,indent=2))

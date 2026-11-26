from pathlib import Path
import json,datetime
h=Path(__file__).resolve().parents[1];r=h.parent
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));assert not state.get('active')
marker=r/'STOP_OWNED_CFD.json';m=json.loads(marker.read_text(encoding='utf8'))
assert m['source']=='night_queue' and m['reason']=='scientific_runtime_gate' and m['target_job']=='c0_tight_firstorder_initialization'
assert len(m['violations'])==1 and m['violations'][0]['metric']=='p_absolute_min_Pa'
review=json.loads((h/'cases/SP_C_split0_overset/c0_tight_firstorder_20261103_025551/work_review.json').read_text(encoding='utf8'))
assert review['last']['native_iteration']==10 and review['last']['overset_error_cells']==0
cfg=json.loads((h/'NIGHT_QUEUE.json').read_text(encoding='utf8'))
new=next(j for j in cfg['jobs'] if j['id']=='c0_tight_continuity_initialization')
assert new['runtime_guards']['minimum_absolute_pressure_Pa']==12339.214766776897 and new['angle_deg']==0
assert Path(new['input']).name=='SP_C_mesh_ready.sim'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');dest=h/'audit'/('STOP_tight_uniform_start_rejected_'+stamp+'.json')
assert marker.resolve()==r.resolve()/'STOP_OWNED_CFD.json' and dest.resolve().is_relative_to((h/'audit').resolve()) and not dest.exists()
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_reviewed_safety_marker_archive',old_marker=m,archive=str(dest),new_job=new['id'],failed_solution_rejected=True,rationale='No continuation of rejected fields. Permit one different initialization diagnostic from preserved zero-step mesh, native continuity initialization100 with true field storage rebuild. Leading-edge startup anomaly suggests unsuitable uniform initial field. All strict runtime limits remain identical; nonzero angles stay forbidden.')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
marker.rename(dest)
p=h/'tools/prepare_tight_controlled_continuation.py';s=p.read_text(encoding='utf8');s=s.replace(r'iteration");\\nStringBuilder',r'iteration");\nStringBuilder');p.write_text(s,encoding='utf8')
print(json.dumps(ev,indent=2))

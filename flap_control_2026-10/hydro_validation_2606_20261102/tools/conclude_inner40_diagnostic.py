from pathlib import Path
import json,datetime
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_inner40_20261102_223940'
review=json.loads((run/'work_review.json').read_text(encoding='utf8'))
assert review['samples']>=100 and all(review['whole_run_guards'].values())
assert len(review['window_results'])>=4 and all(x.get('force_window_pass') for x in review['window_results'][-3:])
assert abs(review['delta_B_percent']['CL_hydro'])>10 and abs(review['delta_B_percent']['CD'])>5
at=datetime.datetime.now().astimezone().isoformat()
decision=dict(at=at,kind='work_scientific_decision',case=str(run),decision='Conclude inner-iteration diagnostic at next completed physical timestep; preserve native paused_by_marker status, full final audit and checkpoint. Not a completed hydrodynamic qualification.',evidence=str(run/'work_review.json'),reason='At least 100 physical steps and three stable force windows at steps50/75/100; CL/CD bias persists. More inner iterations do not explain dominant B/C discrepancy. Omega/viscosity pathology remains.',next='Only separate C0 distance-weighted interpolation diagnostic from saved 40-inner control after checkpoint/native-process verification.',scientific_gate=False)
marker=h.parent/'STOP_OWNED_CFD.json'
assert not marker.exists() and not (h.parent/'PAUSED_FOR_HOME.json').exists()
with marker.open('x',encoding='utf8') as f:json.dump(dict(source='work_inner40_diagnostic_concluded',at=at,reason=decision['reason']),f,indent=2)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(decision)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+at+'\n'+decision['decision']+'\n'+decision['reason']+'\nNext: '+decision['next']+'\n')
(run/'work_conclusion.json').write_text(json.dumps(decision,indent=2),encoding='utf8')
print(json.dumps(decision,indent=2))

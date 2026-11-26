import json,datetime
from pathlib import Path
R=Path(__file__).resolve().parent
st=json.loads((R/'temporal_validation_state.json').read_text())
assert st['status']=='waiting_for_M08','Do not alter a running experiment plan'
p=R/'temporal_validation_plan.json';plan=json.loads(p.read_text());name='T04_M04_SO_dt1ms_inner10_r1'
if not any(j['id']==name for j in plan['jobs']):
 j=dict(next(x for x in plan['jobs'] if x['id']=='T02_M04_SO_dt1ms_r1'))
 j.update(id=name,inner=10,purpose='Matched iteration-count efficiency screen versusT02: same M04 source,second-order,dt1ms,timeinterval; only inner limit20to10 changes.')
 plan['jobs'].append(j)
plan['performance_comparison']='T04 versusT02 isolates10versus20inneriterations. Compare CL/CD,pressure/viscous Fx,adjacentdrift,residualsandmass conservation,actualwalltime. No automatic production adoption; retain finalmeshwavechecks.'
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(plan,indent=2));tmp.replace(p)
with (R/'RESUME_AT_HOME.txt').open('a') as f:f.write('\nPERFORMANCE TEST ADDITION ~19:34CET: While temporalcontroller stillwaiting_for_M08, fourthmatchedbranchT04_M04_SO_dt1ms_inner10_r1 appendedto temporal_validation_plan.json. It is identicaltoT02exceptinner10ratherthan20. Existingcontroller readsplan afterM08, so no restartorGPUinterruptionneeded. Aftercompletion compareT04vsT02explicitly; controllerstoredpairs currentlycoverT01/T02andT02/T03only. Fullcasehistory/experiment_result includesT04. CurrentM08last10innerforcechanges medians~0.019%Fx,0.013%Fz suggesttesting, notautomaticacceptance. Preservecriticalresidual/mass/forcechecks andmeasure actualspeedup.\n')
q=R/'overnight_plan_20261029.json';n=json.loads(q.read_text());n['temporal_efficiency_test']={'id':name,'reference':'T02_M04_SO_dt1ms_r1','status':'Added to waiting controller plan','change':'inner iterations20to10 only','extra_runtime_estimate_min':[7,12]}
q.write_text(json.dumps(n,indent=2))
print(json.dumps({'status':'prepared_in_existing_queue','controller_status':st['status'],'branches':[x['id'] for x in plan['jobs']]}))

from pathlib import Path
import json,sys,datetime,re
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve();inner=int(sys.argv[2]);assert run.is_relative_to(h/'cases/SP_C_split0_overset') and inner==40
read=lambda p:json.loads(p.read_text(encoding='utf8'))
r=read(run/'work_review.json');st=read(run/'status.json');assert st['status']=='urans_diagnostic_ready' and st['force_windows_stable']
assert all(r['whole_run_guards'].values()) and len(r['window_results'])>=3 and all(w['force_window_pass'] for w in r['window_results'][-3:])
f=r['field_exports']['final'];assert f['omega_floor_cells']==f['k_floor_cells']==f['viscosity_ratio_cap_cells']==0
audit=(run/'full_audit_final.txt').read_text(encoding='utf8');assert 'total=333939' in audit and 'errors=0' in audit and 'difficult_interpolation=0' in audit
state=read(h/'NIGHT_QUEUE_STATE.json');cp=state['checkpoint_integrity'][str(run/'checkpoint.sim')];assert cp['native_save_complete']
last=r['last'];assert abs(cp['saved_time_s']-last['time_s'])<1e-9
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_completed_urans_review',run=str(run),source_checkpoint=cp,last=last,last_25_means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],whole_run_guards=r['whole_run_guards'],last_three_window_passes=[w['force_window_pass'] for w in r['window_results'][-3:]],field_review=f,scientific_approved=False,continuation_approved=True,approved_inner_iterations=40,next='Continue exact retained0degree solution with only15to40 inner iterations,dt0.002s and all other settings unchanged. Bounded numerical sensitivity: minimum75,maximum150additional timesteps. Compare force change with preceding drift and examine residuals. No nonzero angles before the completed0degree scientific audit.')
(run/'work_stage_decision.json').write_text(json.dumps(ev,indent=2),encoding='utf8')
p=h/'WORK_CURRENT_REVIEW.json';v=read(p);v['at']=ev['at'];v['previous_recovery_checkpoint']=v['reviewed_recovery_checkpoint']
v['reviewed_recovery_checkpoint']=dict(path=cp['path'],sha256=cp['sha256'],bytes=cp['bytes'],native_iteration=int(last['native_iteration']),physical_time_s=last['time_s'],dt_s=.002,inner_iterations=15,flow_convection='SECOND_ORDER',sst_convection='SECOND_ORDER',CL=last['CL_hydro'],CD=last['CD'],Mh_Nm=last['Mh_Nm'],pabs_min_Pa=last['p_absolute_min_Pa'],native_reopen_verified=False,scientific_approved=False,note='Healthy URANS checkpoint with all recorded strict gates and last3force windows passed. Awaiting inner-iteration sensitivity; not yet approved for nonzero angles.')
v['decision']='Continue controlled0degree inner-iteration sensitivity. Completed matched URANS passes force windows,pressure,mass,turbulence and mesh checks; full C0 scientific approval remains HOLD.'
v['next']=ev['next'];v['obstacle']='Need assess whether increasing inner iterations materially changes forces/residuals. Original unphysical C0 remains rejected. No field artifacts seen on the new cage, but no mesh/time-independence claim is made.'
v['last_verified_transient_checkpoint']=v['reviewed_recovery_checkpoint'];v['completed_urans_review']=dict(run=str(run),time_s=last['time_s'],last_25_means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],all_strict_guards=True,last_three_force_windows_passed=True,scientific_approved=False)
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2),encoding='utf8');tmp.replace(p)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(ev)+'\n')
print(json.dumps({k:v for k,v in ev.items() if k not in ['field_review','last']},indent=2))

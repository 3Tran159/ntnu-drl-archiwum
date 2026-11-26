from pathlib import Path
import json,datetime,re,os
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
r=read(run/'work_review.json');st=read(run/'status.json');state=read(h/'NIGHT_QUEUE_STATE.json')
assert st['status']=='urans_diagnostic_ready' and st['force_windows_stable']
assert all(r['whole_run_guards'].values()) and len(r['window_results'])>=3
# Three consecutive force windows provide two adjacent mean-change comparisons.
w=r['window_results'][-3:];assert all(x.get('force_window_pass',False) for x in w[1:])
assert all(x['relative_ranges']['CL_hydro']<.01 and x['relative_ranges']['CD']<.02 and x['relative_ranges']['Mh_Nm']<.02 for x in w)
f=r['field_exports']['final'];assert f['omega_floor_cells']==f['k_floor_cells']==f['viscosity_ratio_cap_cells']==f['head_gt1p1q_near_cells']==0
audit=(run/'full_audit_final.txt').read_text(encoding='utf8')
assert 'total=333939' in audit and 'errors=0' in audit and 'difficult_interpolation=0' in audit
cp=state['checkpoint_integrity'][str(run/'checkpoint.sim')];assert cp['native_save_complete']
last=r['last'];assert abs(last['time_s']-st['saved_time_s'])<1e-9 and abs(last['time_s']-cp['saved_time_s'])<1e-9
res=read(run/'inner40_residual_review_final.json');pressure=read(run/'pressure_location_final.json');sensitivity=read(run/'inner40_force_sensitivity.json')
at=datetime.datetime.now().astimezone().isoformat()
ev=dict(at=at,kind='work_completed_inner40_review',run=str(run),source_checkpoint=cp,last=last,last_25_means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],strict_guards=r['whole_run_guards'],force_windows=w,field_review=f,residual_review=res,pressure_location_review=pressure,force_sensitivity=sensitivity,scientific_approved=False,training_approved=False,approved_next_diagnostic='pressure_urf_0p1',reason='Near-wall artifacts and original large bias are absent on corrected overlap. Force histories and strict mesh/pressure/mass guards pass, but inner residuals plateau and remote-top pressure minima fluctuate; the same class of issue is present in B without Overset. Before approving0degree, test pressureURF0.2to0.1 only, retaining40inner and all geometry/physics/time settings. Record zone minima and coordinates at each step. This is bounded0degree numerical diagnosis; nonzero angles remain blocked.')
(run/'work_stage_decision.json').write_text(json.dumps(ev,indent=2),encoding='utf8')
p=h/'WORK_CURRENT_REVIEW.json';v=read(p);v['at']=at;v['previous_recovery_checkpoint']=v['reviewed_recovery_checkpoint']
v['reviewed_recovery_checkpoint']=dict(path=cp['path'],sha256=cp['sha256'],bytes=cp['bytes'],native_iteration=int(last['native_iteration']),physical_time_s=last['time_s'],dt_s=.002,inner_iterations=40,velocity_urf=.8,pressure_urf=.2,flow_convection='SECOND_ORDER',sst_convection='SECOND_ORDER',CL=last['CL_hydro'],CD=last['CD'],Mh_Nm=last['Mh_Nm'],pabs_min_Pa=last['p_absolute_min_Pa'],native_reopen_verified=False,scientific_approved=False,note='Healthy diagnostic checkpoint, complete save/hash and strict guards. Pressure-residual diagnosis remains pending; not approved hydrodynamics or training.')
v['last_verified_transient_checkpoint']=v['reviewed_recovery_checkpoint']
v['decision']='C0 scientific HOLD. Completed40-inner continuation passes force and mesh guards; continue one pressure-relaxation diagnostic at0degrees.'
v['next']='PressureURF0.2to0.1 only,40inner,dt0.002s,8CPU/noGPU. Continue retained checkpoint without reset. Save per-zone pressure locations,fields and checkpoints; minimum75,maximum150steps. Evaluate before any nonzero angle.'
v['obstacle']='Inner continuity residual plateau and remote-top pressure oscillations remain unresolved in both baseline B and corrected C. No nonzero angles until positive scientific review.'
v['completed_inner40_review']=dict(run=str(run),time_s=last['time_s'],last_25_means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],strict_guards_passed=True,force_windows_passed=True,scientific_approved=False)
v['live_work_evidence']=dict(run=str(run),observed_time_s=last['time_s'],native_iteration=last['native_iteration'],CL=last['CL_hydro'],CD=last['CD'],Mh_Nm=last['Mh_Nm'],mesh_cells=333939,overset_errors=0)
v['summary']=v['summary'].split(' Inner-iteration sensitivity is still running.')[0]+' Completed40-inner continuation shows small force changes and no restored near-wall spikes; residual plateau/top-boundary pressure fluctuations require the documented single-change pressure-relaxation diagnostic.'
tmp=p.with_suffix('.work_tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,p)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(ev)+'\n')
print(json.dumps(dict(at=at,time_s=last['time_s'],checkpoint=cp,means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],approved_next_diagnostic=ev['approved_next_diagnostic'],scientific_approved=False),indent=2))

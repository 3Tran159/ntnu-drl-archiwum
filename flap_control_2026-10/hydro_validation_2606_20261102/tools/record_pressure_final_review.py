from pathlib import Path
import json,datetime,os
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_urans_pressure_urf01_20261103_043547';read=lambda p:json.loads(p.read_text(encoding='utf8'))
r=read(run/'work_review.json');st=read(run/'status.json');state=read(h/'NIGHT_QUEUE_STATE.json')
assert st['status']=='urans_diagnostic_ready' and all(r['whole_run_guards'].values())
assert len(r['window_results'])>=3 and all(w['force_window_pass'] for w in r['window_results'][-2:])
f=r['field_exports']['final'];assert f['omega_floor_cells']==f['k_floor_cells']==f['viscosity_ratio_cap_cells']==f['head_gt1p1q_near_cells']==0
cp=state['checkpoint_integrity'][str(run/'checkpoint.sim')];assert cp['native_save_complete'] and abs(cp['saved_time_s']-.6)<1e-9
at=datetime.datetime.now().astimezone().isoformat()
ev=dict(at=at,kind='work_completed_pressure_relaxation_diagnostic',run=str(run),checkpoint=cp,last_25_means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],strict_guards=r['whole_run_guards'],field_review=f,pressure_history=read(run/'pressure_relaxation_live_review.json'),residual_review=read(run/'pressure_relaxation_residual_review_final.json'),farfield_review=read(run/'far_top_vectors_final.json'),technical_complete=True,scientific_approved=False,training_approved=False,conclusion='PressureURF0.1 did not remove remote-top pressure oscillations or residual plateau. No safety failure; not an accepted remedy. Preserve finalt0.6 diagnostic. For a controlled next boundary-direction test, prefer previousC40t0.45 with originalURF0.8/0.2 to avoid mixing changes; this is a separate checkpoint branch, not resetting an active solution.',next='Read-onlyC/B outlet backflow setting audits. No nonzero angle or boundary mutation before Work reviews their actual settings.')
(run/'work_stage_decision.json').write_text(json.dumps(ev,indent=2),encoding='utf8')
p=h/'WORK_CURRENT_REVIEW.json';v=read(p);v['at']=at
v['decision']='C0 scientific HOLD. Pressure-relaxation diagnostic completed at0.600s; it did not resolve the far-boundary problem. Read-only C/B outlet inspections next.'
v['obstacle']='Shared remote-top tangential-velocity loss, pressure oscillations and residual plateau. Native backflow direction/pressure settings must be checked. No nonzero angles.'
v['next']=ev['next'];v['latest_completed_pressure_diagnostic']=dict(run=str(run),checkpoint=cp,time_s=.6,native_iteration=10560,pressure_urf=.1,velocity_urf=.8,inner_iterations=40,last_25_means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],scientific_approved=False,remedy_accepted=False)
v['preferred_controlled_branch']=dict(source=v['reviewed_recovery_checkpoint']['path'],physical_time_s=.45,pressure_urf=.2,velocity_urf=.8,inner_iterations=40,reason=ev['conclusion'])
v['live_work_evidence']=dict(run=str(run),observed_time_s=.6,native_iteration=10560,CL=r['last']['CL_hydro'],CD=r['last']['CD'],Mh_Nm=r['last']['Mh_Nm'],mesh_cells=333939,solver_completed=True)
v['backflow_manual_evidence']={'flow_boundary_reference':'E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP/GUID-E14693DE-8C70-4C1E-9DDE-CD4E8591E1BC.html','theory':'E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP/GUID-B52EEA73-AA46-4E60-9F85-4779E3C7397D.html','finding':'Manual recommends extrapolated direction for flow parallel to pressure boundary. Actual native settings pending inspection; no mutation yet.'}
tmp=p.with_suffix('.work_tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,p)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(ev)+'\n')
print(json.dumps(dict(at=at,checkpoint=cp,means=r['last_25_means'],delta_B_percent=r['delta_B_percent'],scientific_approved=False,next=ev['next']),indent=2))

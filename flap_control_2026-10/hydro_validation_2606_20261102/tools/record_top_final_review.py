from pathlib import Path
import json,datetime,os,pandas as pd
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_top_direction_20261103_050724';read=lambda p:json.loads(p.read_text(encoding='utf8'));at=datetime.datetime.now().astimezone().isoformat()
st=read(h/'NIGHT_QUEUE_STATE.json');assert not st.get('active'),'Wait until all owned native children finish'
job=st['jobs']['c0_top_backflow_extrapolated'];native=read(run/'status.json');r=read(run/'work_review.json');live=read(run/'top_direction_live_review.json');res=read(run/'top_residual_live_review.json');far=read(run/'top_boundary_fields_final.json')
assert job['state']=='completed' and native['status']=='urans_diagnostic_ready' and native['steps']>=100
assert all(r['whole_run_guards'].values()) and len(r['window_results'])>=4 and all(w['force_window_pass'] for w in r['window_results'][-3:])
assert all(res['native_csv_crosscheck'].values()) and res['last_step']>=native['steps']
assert all(x['median_last_over_first']<.001 for x in res['cases']['extrapolated'].values()),'Residual decay remains insufficient'
field=r['field_exports']['final'];assert field['omega_floor_cells']==field['k_floor_cells']==field['viscosity_ratio_cap_cells']==field['head_gt1p1q_near_cells']==0
assert far['candidate']['pabs_min_Pa']>35000 and abs(far['candidate']['piezometric_min_Pa'])<5000 and abs(far['candidate']['piezometric_max_Pa'])<5000
assert far['candidate']['uniform18_velocity_deviation_rms']<far['baseline']['uniform18_velocity_deviation_rms']
assert live['last25_pressure']['top_minimum_steps']==0 and live['last25_pressure']['std_global_Pa']<50
text=(run/'full_audit_final.txt').read_text();assert 'total=333939 ' in text and 'errors=0 difficult_interpolation=0' in text
cp=st['checkpoint_integrity'][str(run/'checkpoint.sim')].copy();assert cp['native_save_complete'] and abs(cp['saved_time_s']-native['saved_time_s'])<1e-9
row=pd.read_csv(run/'history.csv').iloc[-1]
cp.update(physical_time_s=float(row.time_s),native_iteration=int(row.native_iteration),dt_s=.002,inner_iterations=40,velocity_urf=.8,pressure_urf=.2,top_backflow_direction='EXTRAPOLATED',top_backflow_pressure='ENVIRONMENTAL',CL=float(row.CL_hydro),CD=float(row.CD),Mh_Nm=float(row.Mh_Nm),pabs_min_Pa=float(row.p_absolute_min_Pa),scientific_approved=False,note='Complete native save/hash verified; native reopen pending. Corrected mesh and top-direction diagnostic passed strict guards, force windows and residual checks. Far-top velocity memory remains, so final hydrodynamic/training approval is withheld pending matchedB and settling assessment.')
ev=dict(at=at,kind='work_completed_top_direction_diagnostic',run=str(run),checkpoint=cp,last25_means=r['last_25_means'],force_windows=r['window_results'][-3:],strict_guards=r['whole_run_guards'],full_native_audit=text,near_field=field,far_top=far,residual=res,diagnostic_mechanism_positive=True,scientific_approved=False,training_approved=False,conclusion='The direction-only change eliminated the repeated remote-top pressure minima and inner-iteration residual plateau. Near-foil field remains healthy and force windows stable. Tangential velocity memory is recovering but not fully settled; not a final training/validation result. Approve matched B0 follow-up with topEXTRAPOLATED and40inner to isolate Overset under the same boundary/numerics. Keep all nonzero angles blocked.')
(run/'work_stage_decision.json').write_text(json.dumps(ev,indent=2),encoding='utf8')
decision=dict(at=at,diagnostic_approved=True,scientific_approved=False,source_C_review=str(run/'work_stage_decision.json'),requires='Serial8CPU/noGPU; preserve original B checkpoint. B top direction change and15to40inner documented; no other physics/mesh/geometry changes. No nonzero angles.',reason=ev['conclusion'])
(h/'audit/B0_matched_top_followup_decision.json').write_text(json.dumps(decision,indent=2),encoding='utf8')
v=read(h/'WORK_CURRENT_REVIEW.json');v.update(at=at,latest_top_boundary_checkpoint=cp,completed_top_boundary_review=ev,decision='C0 top-direction diagnostic completed with positive mechanism evidence; scientific HOLD. Matched B0 follow-up approved.',obstacle='Matched B/C comparison under corrected top boundary and40inner; far-top velocity memory still needs settling assessment. No nonzero angles.',next='Run prepared B0 topEXTRAPOLATED/40inner continuation from retained originalB fields, inspect result, then decide on C0 settling/motion. Scientific gate remains false.')
tmp=h/'WORK_CURRENT_REVIEW.work_tmp';tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,h/'WORK_CURRENT_REVIEW.json')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
print(json.dumps(dict(at=at,checkpoint=cp,means=r['last_25_means'],diagnostic_mechanism_positive=True,scientific_approved=False,approved_next='MatchedB0 only'),indent=2))

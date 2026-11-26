from pathlib import Path
import json,csv,datetime
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_tight_urans_v2_20261103_035710'
rows=list(csv.DictReader((run/'history.csv').open()));last={k:float(v) for k,v in rows[-1].items()}
assert last['time_s']>0 and last['native_iteration']>2310
review=json.loads((run/'work_review.json').read_text(encoding='utf8'))
assert all(review['whole_run_guards'].values())
f=review['field_exports']['step_50'];assert f['omega_floor_cells']==f['k_floor_cells']==f['viscosity_ratio_cap_cells']==0
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));cp=state['checkpoint_integrity'][str(run/'checkpoint_step_50.sim')];assert cp['native_save_complete'] and cp['saved_time_s']==.1
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=datetime.datetime.now().astimezone().isoformat()
v['decision']='Continue current0degree URANS diagnostic. Native physical-time advance verified; all reviewed strict gates pass. Hydrodynamic approval and all nonzero angles remain HOLD.'
v['next']='Finish at least150steps(0.3s),review several0.05s force windows,inner residual behavior,local fields and B/C force decomposition. If force stability alone passes but numerical convergence remains uncertain, perform a bounded0degree inner-iteration sensitivity in a separate continuation before approving any angle.'
v['obstacle']='Original C/B force bias remains unapproved pending completed matched URANS and residual review. New-cage force difference is shrinking during physical-time stabilization; previous steady coefficients were not final.'
v['last_verified_transient_checkpoint']={**cp,'native_iteration':3060,'dt_s':.002,'scientific_approved':False,'note':'Saved/hash-verified at t0.1; native reopen not yet performed. Current solve continues; use latest durable checkpoint when resuming.'}
v['live_work_evidence']=dict(run=str(run),observed_time_s=last['time_s'],native_iteration=last['native_iteration'],CL=last['CL_hydro'],CD=last['CD'],Mh_Nm=last['Mh_Nm'],pabs_min_Pa=last['p_absolute_min_Pa'],mass_imbalance_relative=last['mass_imbalance_relative'],reviewed_field_time_s=.1,meanflow_p0_max_near_Pa=f['meanflow_p0_max_near_Pa'],mesh_cells=333939,overset_errors=0,difficult_stencils=0)
v['transition_implementation_verified']=dict(source_relaxation='0.3/0.1,dynamic=false',after_model_conversion_defaults='0.8/0.2,dynamic=false',matched_B=True,source_force_readback_preserved=True,physical_time_before_first_step=0,native_iteration_before_first_step=2310,initialized_or_cleared=False)
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2),encoding='utf8');tmp.replace(p)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(dict(at=v['at'],kind='work_urans_live_review',evidence=v['live_work_evidence'],checkpoint=v['last_verified_transient_checkpoint'],continue_current_case=True,scientific_approved=False))+'\n')
print(json.dumps(v['live_work_evidence'],indent=2))

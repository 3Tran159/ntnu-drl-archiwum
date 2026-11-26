from pathlib import Path
import json,csv,datetime,re,sys,os
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve();assert run.is_relative_to(h/'cases/SP_C_split0_overset')
nxt=sys.argv[2];r=json.loads((run/'work_review.json').read_text(encoding='utf8'));st=json.loads((run/'status.json').read_text(encoding='utf8'))
assert st['status']=='steady_diagnostic_ready'
last=r['last'];f=r['field_exports']['final'];audit=(run/'full_audit_final.txt').read_text(encoding='utf8')
assert last['p_absolute_min_Pa']>12339.214766776897 and last['mass_imbalance_relative']<1e-4
assert f['omega_floor_cells']==f['k_floor_cells']==f['viscosity_ratio_cap_cells']==0
assert 'errors=0' in audit and 'difficult_interpolation=0' in audit
rows=list(csv.DictReader((run/'steady_iterations.csv').open()));native=int(float(rows[-1].get('native_iteration') or rows[-1]['iteration']))
state=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));cp=state['checkpoint_integrity'][str(run/'steady_checkpoint.sim')];assert cp['native_save_complete']
p=h/'WORK_CURRENT_REVIEW.json';v=json.loads(p.read_text(encoding='utf8'));v['at']=datetime.datetime.now().astimezone().isoformat()
v['previous_recovery_checkpoint']=v['reviewed_recovery_checkpoint']
readback=run/'checkpoint_readback.txt'
if readback.exists():v['previous_recovery_checkpoint']['native_reopen_verified']=True
v['reviewed_recovery_checkpoint']=dict(path=cp['path'],sha256=cp['sha256'],bytes=cp['bytes'],native_iteration=native,physical_time_s=0,CL=last['CL_hydro'],CD=last['CD'],Mh_Nm=last['Mh_Nm'],pabs_min_Pa=last['p_absolute_min_Pa'],native_reopen_verified=False,scientific_approved=False,note='Healthy numerical diagnostic with force-window criterion passed. Residuals and far-top-boundary drift are unresolved; not a converged hydrodynamic result.')
v['latest_field_review']=dict(iteration=native,additional_iterations=last['iteration'],meanflow_p0_max_near_Pa=f['meanflow_p0_max_near_Pa'],meanflow_p0_p99_near_Pa=f['meanflow_p0_p99_near_Pa'],zero_omega_and_k_floor=True,mesh_errors=0,mesh_difficult_stencils=0,interpretation='No old upstream interface spikes in this phase. Far-field velocity evolution and native residuals require further review; no scientific approval.')
v['decision']='HOLD scientific approval and all nonzero angles. Permit only the documented next0degree numerical diagnostic.'
v['next']=nxt
v['obstacle']='Numerical force-window pass does not establish PDE convergence. Residuals remain elevated; largest velocity changes also occur near remote pressure top x30-42m,z~8m. B reference shows remote-top minimum-pressure fluctuations too. Do not silently change physical boundary conditions. Full original CL/CD discrepancy remains quantitatively unresolved pending matched second-order URANS.'
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,p)
ev=dict(at=v['at'],kind='work_tight_stage_review',run=str(run),next=nxt,checkpoint=v['reviewed_recovery_checkpoint'],field_review=v['latest_field_review'],residual_convergence_approved=False,scientific_approved=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as out:out.write(json.dumps(ev)+'\n')
(run/'work_stage_decision.json').write_text(json.dumps(ev,indent=2),encoding='utf8')
print(json.dumps(ev,indent=2))

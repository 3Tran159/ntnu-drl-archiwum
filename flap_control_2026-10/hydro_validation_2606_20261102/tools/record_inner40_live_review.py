from pathlib import Path
import json,datetime,os,re
h=Path(__file__).resolve().parents[1]
run=h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433'
now=datetime.datetime.now().astimezone().isoformat()
def atomic(path,obj):
 tmp=path.with_suffix(path.suffix+'.work_tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf8');os.replace(tmp,path)
p=h/'WORK_CURRENT_REVIEW.json';review=json.loads(p.read_text(encoding='utf8'))
back=h/'audit/WORK_CURRENT_REVIEW_before_inner40_live.json'
if not back.exists():back.write_text(p.read_text(encoding='utf8'),encoding='utf8')
readback=(run/'checkpoint_readback.txt').read_text(encoding='utf8')
assert 'native_iteration=4560' in readback and 'time=0.3000000000000002' in readback
for name,value in [('HF_CL_hydro',.3246950252287313),('HF_CD',.007284020860022872),('HF_Mh_Nm',-12.031262038756221)]:
 actual=float(re.search(name+r'=([-+0-9.eE]+)',readback).group(1));assert abs(actual-value)<1e-10
for key in ['reviewed_recovery_checkpoint','last_verified_transient_checkpoint']:
 review[key]['native_reopen_verified']=True
 review[key]['native_reopen_evidence']=str(run/'checkpoint_readback.txt')
review['at']=now
review['decision']='RUNNING: retained 0-degree URANS solution, 40 inner iterations. Nonzero angles remain blocked pending completed scientific audit.'
review['summary']='Original C/B discrepancy (CL +14.6869%, CD -9.5692%) is rejected: roughly 94% of excess lift came from the fixed main foil, with nonphysical near-wall pressure/velocity peaks. More inner iterations and interpolation changes alone did not fix it. On the old rectangular Overset region, second-order momentum recreated peaks even without turbulence clipping. Restricting the numerical Overset region to the flap and hinge gap removed those peaks while preserving physical STL geometry and all background cells. The corrected second-order URANS case at t=0.300 s gives final-window CL 0.3245475 and CD 0.00728838, or -0.840% and +1.742% versus B. This supports a near-wall Overset discretization/overlap cause; it does not identify a single code-level defect or establish mesh/time independence. Inner-iteration sensitivity is still running.'
review['current_run']=str(run);review['current_mesh_cells']=333939
review['live_work_evidence']=json.loads((run/'work_review.json').read_text(encoding='utf8'))
atomic(p,review)
cfgpath=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgpath.read_text(encoding='utf8'))
assert cfg['scientific_gates']['C0_bias_explained_and_approved'] is False
cfg['scientific_gates']['reason']='Original C0 rejected for near-wall numerical field artifacts. Corrected 333939-cell C0 passes recorded strict guards but awaits completed inner-iteration sensitivity and scientific review; all nonzero angles remain blocked.'
atomic(cfgpath,cfg)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=now,event='work_live_inner40_review',run=str(run),native_reopen_verified=True,scientific_approved=False,nonzero_angles_approved=False),ensure_ascii=False)+'\n')
print(json.dumps(dict(at=now,run=str(run),source_reopen_verified=True,current_time_s=review['live_work_evidence']['last_time_s'],guards=review['live_work_evidence']['whole_run_guards']),indent=2))

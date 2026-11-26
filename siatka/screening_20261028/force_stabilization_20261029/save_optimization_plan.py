import json,datetime,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
d=json.loads((R/'mesh_budget_cfl.json').read_text())['cases']['M07']
plan={
 'updated_at':datetime.datetime.now().astimezone().isoformat(),
 'basis':'Accepted M07 centroid census; cell shares are cost indicators, not guaranteed removable cells or runtime savings.',
 'reference_cells':d['cells'],'regions':d['regions'],
 'priorities':[
 {'priority':1,'region':'Deep water and upper air','current_share_pct':sum(a['share_pct'] for a in d['regions'] if a['region'] in ['Deep water','Upper air']),'action':'Increase outer-cell size gradually outside protected foil/wake/free-surface controls. Keep the physical domain and boundary conditions fixed. Audit transition quality and forces.'},
 {'priority':2,'region':'Free-surface refinement band','current_share_pct':next(a['share_pct'] for a in d['regions'] if a['region']=='Free-surface band'),'action':'Consider a narrower calm-only band after measuring actual interface motion. Preserve interface transport accuracy, inlet resolution and calm-wave propagation. H0.5m waves require at least the amplitude envelope plus numerical margin, then wavelength/time-step checks; do not transfer a calm-only narrow band blindly.'},
 {'priority':3,'region':'Near-foil outer refinement box','current_share_pct':next(a['share_pct'] for a in d['regions'] if a['region']=='Foil refinement box'),'action':'Inspect velocity/pressure gradients and boundary-layer/prism-core transition before contracting outer refinement. Keep wall layers, foil contour, leading/trailing edges and wake protected.'}],
 'sequence':'Finish controlled M08 and the separate M04 temporal-order screen first. Reserve M09 and M10 for targeted optimization or remaining accuracy discrepancies. Do not add variants aboveM10.',
 'controls':'Change one resolution family at a time; preserve exact source foil and single-cell span. No domain shrink. Audit zero invalid cells, positive volume/closure, wall y+, transition, force components, CFL and actual computing time.',
 'acceptance':'Both mean CL and CD within1% of comparable denser evidence; both adjacent0.2s mean changes below0.5%; no automatic validation from low cell count. Final-mesh time-step verification required.'
}
(R/'mesh_optimization_plan.json').write_text(json.dumps(plan,indent=2))
p=json.loads((R/'mesh_selection_plan.json').read_text())
p['updated_at']=plan['updated_at'];p['temporal_priority']='run_temporal_comparison.py waits for M08_until_settled_r3 completed, then claims root queue.lock for separate M04 FO1ms, SO1ms, SO0.5ms branches. Do not duplicate or mix with mesh means.'
p['optimization_plan']='mesh_optimization_plan.json'
p['M08_recovery']='r1 stopped at first step, max velocity114.13m/s>90 guard. r2 starts from initialized pre-step checkpoint,dt0.5ms,50inner,40steps to0.020s, all finite and guard retained. r3 continues atdt1ms,20inner until original0.5%force criterion. All attempts preserved.'
(R/'mesh_selection_plan.json').write_text(json.dumps(p,indent=2))
print('Optimization and execution priorities saved.')

"""Read-only accepted-field study for a future LE/TE targeted candidate."""
import csv,json,statistics,math,sys,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(Q/'deps311'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return [{k:(float(v) if v else None) for k,v in a.items()} for a in csv.DictReader(f)]
faces=rows(R/'M08_pressure_face_contributions.csv');topo=rows(Q/'M08'/'foil_layer_topology.csv')
assert len(faces)==len(topo)==856 and all(all(math.isfinite(v) for v in a.values()) for a in faces)
c=1.19;bands=[('Leading region',-math.inf,.05),('Middle chord',.05,.85),('Trailing region',.85,math.inf)]
summary=[]
for name,lo,hi in bands:
 a=[r for r in faces if lo<=r['x']/c<hi];t=[r for r in topo if lo<=r['x']/c<hi]
 summary.append({'region':name,'x_over_c':[max(lo,0),min(hi,1)],'surface_segments':len(a),'median_edge_mm':statistics.median(r['edge_length_m'] for r in a)*1000,'Cp_min':min(r['Cp_hydro_subtracted'] for r in a),'Cp_max':max(r['Cp_hydro_subtracted'] for r in a),'pressure_Fx_N_snapshot':sum(r['pressure_drag_N'] for r in a),'edge_length_share_pct':100*sum(r['edge_length_m'] for r in a)/sum(r['edge_length_m'] for r in faces),'wall_length_with_under_40_layers_pct':100*sum(r['edge_length_m'] for r in t if r['continuous_quad_layers']<40)/sum(r['edge_length_m'] for r in t)})
assert sum(r['surface_segments'] for r in summary)==len(faces)
proposal={'source_x_over_c_range':[min(r['x']/c for r in faces),max(r['x']/c for r in faces)],'pressure_Fx_N_snapshot_total':sum(r['pressure_drag_N'] for r in faces),'status':'design_study_not_meshed','candidate':'M10 subject to M09/temporal review','reference':'M08 accepted t=1.600s','regions':summary,'proposed_middle_chord_x_over_c':[.05,.85],'middle_surface_target_mm':4.0,'LE_TE_surface_target_mm':2.0408163265,'first_layer_um':1.5306122449,'prism_layers':48,'total_prism_mm':15.46,'coarsening_scope':'Tangential surface and adjacent volume targets only; protect LE/TE and preserve wall-normal layers. Keep M09 remote-region design separate until its evidence passes.','implementation_gate':'Current global foil surface control must be locally overridden by supported edge/surface or volume controls. Verify actual surface-edge lengths and region transitions after generation; blocks alone do not prove surface refinement.','acceptance':'No automatic admission. Audit source geometry, layer continuity, closure/volume, y+, local pressure and viscous drag, CFL, step cost and both settled coefficient differences against comparable evidence.','limitation':'Cp and pressure-force localization are one accepted field snapshot, not window means. Local viscous-wall traction is not exported, so savings and accuracy cannot be concluded from this study.','updated_at':datetime.datetime.now().astimezone().isoformat()}
ideal=sum((r['edge_length_m']/(.004 if .05<=r['x']/c<.85 else .0020408163265)) if r['edge_length_m']>=.7*.002857142857 else 1 for r in faces)
proposal['ideal_surface_segments_with_curvature_floor']=round(ideal)
proposal['ideal_prism_cell_reduction_estimate']=(len(faces)-ideal)*48
proposal['ideal_total_cell_reduction_from_prisms_only_pct']=100*(len(faces)-ideal)*48/254989
proposal['estimation_limit']='Indicative tangential edge-length scaling; small curvature-limited segments retained. Actual local controls, transitions and mesh counts must be measured.'
proposal['design_reason']='Narrow LE x/c<0.05 and TE x/c>0.85 controls are the initial design. Refining a broad 0–0.15 plus 0.75–1 end region while coarsening the middle nearly cancels the surface-edge saving; it is not an efficient first test.'
(R/'leading_trailing_refinement_review.json').write_text(json.dumps(proposal,indent=2),encoding='utf-8')
fig,axs=plt.subplots(2,1,figsize=(10,7),sharex=True,layout='constrained')
for sign,color,label in [(1,'#0072B2','Surface branch A'),(-1,'#D55E00','Surface branch B')]:
 a=sorted([r for r in faces if r['area_z_m2']*sign>0],key=lambda r:r['x'])
 x=[r['x']/c for r in a]
 axs[0].plot(x,[r['Cp_hydro_subtracted'] for r in a],color=color,lw=1.3,label=label)
 axs[1].plot(x,[r['edge_length_m']*1000 for r in a],color=color,lw=1,marker='.',ms=2)
for ax in axs:
 ax.axvspan(.05,.85,color='#777777',alpha=.09)
 ax.axvline(.05,color='#555',ls='--',lw=.8);ax.axvline(.85,color='#555',ls='--',lw=.8)
 ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
axs[0].set_ylabel('Cp, hydrostatic contribution removed');axs[0].legend(frameon=False)
axs[0].set_title('M08 accepted field: evidence for a local LE/TE mesh test')
axs[1].set_ylabel('Actual surface segment length [mm]');axs[1].set_xlabel('x / chord')
axs[1].set_yscale('log');axs[1].set_xlim(-.001,1)
fig.savefig(R/'leading_trailing_refinement_review.png',dpi=160)
print(json.dumps({'regions':summary,'proposal_status':proposal['status']},indent=2))

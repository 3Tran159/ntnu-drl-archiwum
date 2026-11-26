"""Read-only localization of high-y+ and incomplete prism layers at accepted snapshots."""
import csv,json,math,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def rows(path):
 with Path(path).open(encoding='utf-8-sig',newline='') as f:return [{k:(float(v) if v and v.strip() else None) for k,v in r.items()} for r in csv.DictReader(f)]
snap=json.loads((R/'selected_snapshots.json').read_text())
registry=json.loads((R/'campaign_registry.json').read_text())
layers={c['id']:c['layers'] for c in registry['cases']}
result={}
for mesh in ['M04','M06','M07','M08','M09','M10']:
 if mesh not in snap or snap[mesh]['status']!='Settled':continue
 p=rows(R/(mesh+'_pressure_face_contributions.csv'));w=rows(snap[mesh]['wall']);t=rows(Q/mesh/'foil_layer_topology.csv')
 out=[]
 for a in p:
  wall=min(w,key=lambda b:(b['X (m)']-a['x'])**2+(b['Z (m)']-a['z'])**2)
  topo=min(t,key=lambda b:(b['x']-a['x'])**2+(b['z']-a['z'])**2)
  wd=math.hypot(wall['X (m)']-a['x'],wall['Z (m)']-a['z'])
  td=math.hypot(topo['x']-a['x'],topo['z']-a['z'])
  assert wd<1e-8 and td<1e-8,(mesh,wd,td)
  out.append(dict(x_over_c=a['x']/1.19,wall_yplus=wall['Wall Y+'],layers=topo['continuous_quad_layers'],wall_area_m2=a['edge_length_m']*.02,
   pressure_drag_raw_N=a['pressure_drag_N'],pressure_drag_hydro_sub_N=a['Cp_hydro_subtracted']*162000*a['area_x_m2'],
   pressure_lift_hydro_sub_N=a['Cp_hydro_subtracted']*162000*a['area_z_m2']))
 area=sum(a['wall_area_m2'] for a in out)
 reconstructed=sum(a['pressure_drag_raw_N'] for a in out)
 exact=snap[mesh]['pressure_drag_N']
 assert abs(reconstructed-exact)<max(1e-7,abs(exact)*1e-6)
 masks={'last_2pct_chord':lambda a:a['x_over_c']>=.98,'last_1pct_chord':lambda a:a['x_over_c']>=.99,
 'last_half_pct_chord':lambda a:a['x_over_c']>=.995,'yplus_above5':lambda a:a['wall_yplus']>5,
 'incomplete_nominal_layers':lambda a:a['layers']<layers[mesh],'yplus_above5_and_incomplete':lambda a:a['wall_yplus']>5 and a['layers']<layers[mesh]}
 groups={}
 for name,keep in masks.items():
  selected=[a for a in out if keep(a)]
  groups[name]={'faces':len(selected),'wall_area_pct':100*sum(a['wall_area_m2'] for a in selected)/area,
   'min_x_over_c':min((a['x_over_c'] for a in selected),default=None),'max_x_over_c':max((a['x_over_c'] for a in selected),default=None),
   'pressure_drag_hydro_sub_N':sum(a['pressure_drag_hydro_sub_N'] for a in selected),
   'pressure_lift_hydro_sub_N':sum(a['pressure_lift_hydro_sub_N'] for a in selected)}
 result[mesh]={'time_s':snap[mesh]['time_s'],'nominal_layers':layers[mesh],'pressure_reconstruction_error_N':reconstructed-exact,
  'max_yplus':max(a['wall_yplus'] for a in out),'groups':groups}
 with (R/(mesh+'_trailing_edge_audit.csv')).open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=out[0]);writer.writeheader();writer.writerows(out)
document={'updated_at':datetime.datetime.now().astimezone().isoformat(),'cases':result,
 'method':'Exact-centroid matches of accepted STAR wall exports, oriented CGNS boundary-face pressure contributions, and independent layer-connectivity audit. Pressure sums use nominal hydrostatic subtraction (rho1000,g9.81,free surfacez2); full raw pressure sum cross-checked against matching instantaneous STAR report.',
 'limits':['Instantaneous accepted snapshots, not time-averaged local loads.','Subset pressure forces depend on pressure reference; this diagnostic uses the stated hydrostatic-subtracted convention.','Small direct force in a defective area does not bound its downstream or total-force error.','Local viscous force was not exported and is not inferred from y+.','Incomplete quad-layer count is a topology flag, not itself proof of inaccurate flow.']}
(R/'trailing_edge_audit.json').write_text(json.dumps(document,indent=2))
print(json.dumps({m:{'time_s':d['time_s'],'high_yplus':d['groups']['yplus_above5'],'incomplete':d['groups']['incomplete_nominal_layers']} for m,d in result.items()}))

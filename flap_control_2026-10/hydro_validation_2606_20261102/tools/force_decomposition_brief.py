from pathlib import Path
import json,re,datetime
h=Path(__file__).resolve().parents[1]
files={'B':h/'audit/comparison_SP_B_20261102_222923/diagnostic.txt','C':h/'audit/comparison_SP_C_20261102_222216/diagnostic.txt'}
forces={}
for label,p in files.items():
 text=p.read_text(encoding='utf8');forces[label]={m.group(1)+'_'+m.group(2):[float(x) for x in m.group(3).split(',')] for m in re.finditer(r'(main|flap)_(pressure|shear|total)_force=\[([^\]]+)\]',text)}
delta={k:[c-b for c,b in zip(forces['C'][k],forces['B'][k])] for k in forces['B']}
dz=sum(delta[k][2] for k in ['main_total','flap_total']);dx=sum(delta[k][0] for k in ['main_total','flap_total'])
out=dict(at=datetime.datetime.now().astimezone().isoformat(),forces_N=forces,C_minus_B_N=delta,total_delta_Fz_N=dz,total_delta_Fx_N=dx,main_share_of_delta_lift=delta['main_total'][2]/dz,pressure_delta_drag_N=sum(delta[k][0] for k in ['main_pressure','flap_pressure']),shear_delta_drag_N=sum(delta[k][0] for k in ['main_shear','flap_shear']),caution='Instantaneous saved-field forces, not the window-averaged CL/CD. C audit interrupted later during vector table export; these force reports completed before that export. Difference attribution is not yet a causal proof.',C0_approved=False)
(h/'validation/BC_force_decomposition.json').write_text(json.dumps(out,indent=2),encoding='utf8')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n### '+out['at']+' — B/C scientific hold\nC-B instantaneous lift difference is '+str(round(dz,3))+' N; '+str(round(100*out['main_share_of_delta_lift'],1))+'% occurs on the fixed main foil. Drag decreases by '+str(round(-dx,3))+' N despite a '+str(round(out['shear_delta_drag_N'],3))+' N increase in viscous drag; pressure drag decreases by '+str(round(-out['pressure_delta_drag_N'],3))+' N. Cp shows jumps within the overlap/hinge area. C has recurring turbulent-viscosity limiting in one cell; B has none. This is a mesh/interpolation/turbulence diagnostic concern, not approved hydrodynamic benefit. Exact cause pending full native audit.\n')
print(json.dumps(out,indent=2))

from pathlib import Path
import json
h=Path(__file__).resolve().parents[1]
s=(h/'tools/design_tight_cage_v1.py').read_text()
s=s.replace('c0_tight_cage_v1','c0_tight_cage_v2')
s=s.replace('for a,b in zip(poly,poly[1:]+poly[:1]):','for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):')
s=s.replace("groups['OversetOuter'].extend([[A,C,B],[A,D,C]])","patch='OversetArc' if i<128 else ['OversetLowerRamp','OversetLowerAft','OversetTrailing','OversetUpperAft','OversetUpperRamp'][i-128]\n groups[patch].extend([[A,C,B],[A,D,C]])")
s=s.replace("triangles=sum(map(len,groups.values())),","triangles=sum(map(len,groups.values())),patch_triangles={k:len(v) for k,v in groups.items()},patch_change_only=True,")
p=h/'tools/design_tight_cage_v2.py';assert not p.exists();p.write_text(s)
s=(h/'tools/prepare_tight_cage_mesh.py').read_text()
s=s.replace('PrepareC0TightCage','PrepareC0TightCagePatches').replace('c0_tight_cage_v1','c0_tight_cage_v2')
s=s.replace("cfg['jobs'].append(job);cfg['controller_exit_requested']=True","cfg['jobs'].append(job);cfg['release_failure_hold']['c0_tight_cage_v1_mesh_audit']='Native guide-surface sweep failed before any flow. Same cage coordinates now have separate side patches at sharp corners; fixed foil,flap,span and all numerical targets unchanged.';cfg['controller_exit_requested']=True")
s=s.replace("Numerical outer cage only: front arc","Numerical outer cage unchanged relative to failed v1, only side-surface patches split at existing corners to support directed sweeping. Numerical outer cage: front arc")
p=h/'tools/prepare_tight_cage_patch_mesh.py';assert not p.exists();p.write_text(s)
print('Prepared one-shot v2 geometry and native mesh scripts; no native launch in this script.')

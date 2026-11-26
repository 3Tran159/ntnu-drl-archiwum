from pathlib import Path
import json,shutil
R=Path(r'F:\ntnu\mesh_screening_20261028\force_stabilization_20261029')
p=R/'mesh_convergence.py';backup=R/'mesh_convergence_before_componentwise_refinement.py'
if not backup.exists():shutil.copy2(p,backup)
s=p.read_text(encoding='utf-8')
anchor='def assess(persist=True):'
helper='''def resolution_refines(fine,coarse,defs):
 """A finer confirmation must resolve every controlled direction at least as finely."""
 a,b=defs.get(fine,{}),defs.get(coarse,{})
 size_keys=['base_m','foil_target_m','foil_min_m','global_min_m','near_foil_m','free_surface_m','first_layer_um']
 if any(a.get(k) is None or b.get(k) is None for k in size_keys+['layers','total_prism_mm']):return False
 if abs(a['total_prism_mm']-b['total_prism_mm'])>1e-7:return False
 if any(a[k]>b[k]*(1+1e-8) for k in size_keys) or a['layers']<b['layers']:return False
 return any(a[k]<b[k]*(1-1e-8) for k in size_keys) or a['layers']>b['layers']

'''
assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor+"\n from mesh_definition import definitions\n defs=definitions()")
s=s.replace("'same_family':a['family']==b['family'],","'same_family':a['family']==b['family'],'finer_in_all_controls':a['family']==b['family'] and resolution_refines(b['id'],a['id'],defs),")
s=s.replace("b['cells']>a['cells'] and b['family']==a['family']","b['cells']>a['cells'] and b['family']==a['family'] and resolution_refines(b['id'],a['id'],defs)")
s=s.replace("across candidate and at least two finer meshes in the same near-wall family.","across the candidate and at least two finer comparable meshes in the same near-wall family. Each confirming mesh must have no larger nominal outer/surface/zone/first-layer size and no fewer prism layers, at the same total prism thickness and unchanged geometry/domain. Cell count alone does not establish directional refinement.")
s=s.replace("kind='Refinement' if p['same_family'] else 'Wall-resolution comparison'","kind=('Refinement' if p['finer_in_all_controls'] else 'Mixed mesh changes') if p['same_family'] else 'Wall-resolution comparison'")
s=s.replace("status=('Within 1%' if p['within_1pct'] else 'Above 1%') if p['same_family'] else 'Different near-wall mesh'","status=('Within 1%' if p['within_1pct'] else 'Above 1%') if p['finer_in_all_controls'] else ('Diagnostic comparison' if p['same_family'] else 'Different near-wall mesh')")
s=s.replace("Force components help explain the total-drag difference; the agreed 1% acceptance test applies to CD and CL.","Force components help explain the total-drag difference; the agreed 1% acceptance test applies to CD and CL. Finer confirmations must retain or refine every controlled mesh direction. Mixed changes remain diagnostic comparisons.")
p.write_text(s,encoding='utf-8')
from mesh_definition import definitions
from mesh_convergence import resolution_refines,assess
d=definitions()
assert resolution_refines('M07','M08',d)
assert resolution_refines('M08','M06',d)
assert not resolution_refines('M06','M08',d)
d['candidate_test']={**d['M08'],'base_m':.25}
assert resolution_refines('M08','candidate_test',d) and resolution_refines('M07','candidate_test',d)
assert not resolution_refines('M06','candidate_test',d)
a=assess();assert a['recommended_candidate'] is None
(R/'refinement_relation_check.json').write_text(json.dumps({'status':'passed','checks':['M07 refines M08','M08 refines M06','M06 is not finer in wall-normal controls than a 48-layer M09-style candidate','M08 and M07 can confirm a coarser-outer 48-layer candidate only after actual force agreement'],'selected_mesh':None},indent=2))
print('Directional refinement eligibility verified; no mesh selected automatically.')

import json,datetime
from pathlib import Path
R=Path(__file__).resolve().parent
Q=R.parent/'quasi2d_012_20261029'
p=R/'refinement_build_results.json'
previous=json.loads(p.read_text(encoding='utf-8'))
archive=R/'refinement_build_results_initial_20261029.json'
if not archive.exists():archive.write_text(json.dumps(previous,indent=2),encoding='utf-8')
results=[]
for mesh in ['M06','M07']:
    folder=Q/mesh
    m=json.loads((folder/'measurement.json').read_text())['metrics']
    top=json.loads((folder/'topology_audit.json').read_text())
    status=json.loads((Q/(mesh+'_build')/'build_status.json').read_text())
    assert status['status']=='verified' and top['single_layer_topology'] and not top['invalid_cells']
    assert all(m[k]==0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells'])
    assert top['max_target_source_xz_displacement_m']==0 and m['min_cell_quality']>.01 and m['min_face_validity']>.5
    results.append({'id':mesh,'status':'verified','cells':m['cell_count'],'method':'Exact extrusion of audited source polygons','updated_at':datetime.datetime.now().astimezone().isoformat(),'initial_attempts':'refinement_build_results_initial_20261029.json'})
tmp=p.with_suffix('.tmp')
tmp.write_text(json.dumps(results,indent=2),encoding='utf-8');tmp.replace(p)
print(json.dumps(results))

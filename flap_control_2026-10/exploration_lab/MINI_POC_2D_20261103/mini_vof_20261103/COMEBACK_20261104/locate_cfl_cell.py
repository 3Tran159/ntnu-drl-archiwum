"""Match exported CFL maxima to the corresponding mesh cells."""
import json
from pathlib import Path
import sys

import numpy as np

from summarize_h010 import get, peak
sys.path.insert(0, str(Path(__file__).parent / "WALL_FUNCTIONS_AUDIT"))
from audit_wall import load_mesh, centroid, map_vertices, ROOT
from audit_motion_map import signed_area

def mesh_cell(mesh, xyz, angle, previous_angle, dt):
    xy, cells, walls = load_mesh(mesh)
    points = map_vertices(xy,angle) if angle else xy
    center = np.array([centroid(points[list(c)]) for c in cells])
    idx = int(np.argmin(np.linalg.norm(center-xyz,axis=1)))
    cell = points[list(cells[idx])]
    edges = np.linalg.norm(np.roll(cell,-1,axis=0)-cell,axis=1)
    wall = points[np.array([[a,b] for a,b,_ in walls])]
    t = wall[:,1]-wall[:,0]
    frac = np.clip(np.sum((xyz-wall[:,0])*t,axis=1)/np.sum(t*t,axis=1),0,1)
    distance = np.linalg.norm(xyz-(wall[:,0]+t*frac[:,None]),axis=1)
    q = int(np.argmin(distance))
    prior = map_vertices(xy,previous_angle) if previous_angle else xy
    grid = (center[idx]-centroid(prior[list(cells[idx])]))/dt
    return {"mesh":str(mesh),"cell_index_gmsh_order_0based":idx,"center_xy_m":center[idx].tolist(),
        "cell_match_error_m":float(np.linalg.norm(center[idx]-xyz)),
        "vertices_xy_m":cell.tolist(),"edge_lengths_m":edges.tolist(),
        "area_m2":float(abs(signed_area(cell))),"grid_velocity_xy_from_prescribed_map_m_s":grid.tolist(),
        "distance_to_nearest_foil_wall_m":float(distance[q]),"nearest_wall_group":walls[q][2],
        "nearest_wall_xy_m":(wall[q,0]+t[q]*frac[q]).tolist()}

mode, directory = sys.argv[1:3]
folder = Path(directory)
if mode=="B":
    original=next((folder.parent).glob("B_SEEDED_URANS_DT25US_*"))
    tail=get(original/"single_phase.csv")[-2:]
    read=peak(folder,"cell_cfl.csv")
    location=np.array([read["X (m)"],read["Y (m)"]])
    mesh=ROOT/"sealed_demo_delta_0"/"geometry_and_mesh.msh"
    a,b=(float(r["delta_measured_deg"]) for r in tail)
    result=mesh_cell(mesh,location,b,a,float(tail[1]["time_s"])-float(tail[0]["time_s"]))
else:
    read=peak(folder)
    location=np.array([read["X (m)"],read["Y (m)"]])
    mesh=Path(__file__).parent/"WALL_FUNCTIONS_AUDIT"/"HIGH_YPLUS_CANDIDATE_V2"/"geometry_and_mesh.msh"
    result=mesh_cell(mesh,location,0,0,25e-6)
result["native_field_row"]=read
result["x_over_c"]=float(location[0]/1.19)
text=json.dumps(result,indent=2)
(folder/"CFL_CELL_ANALYSIS.json").write_text(text,encoding="utf8")
print(text)


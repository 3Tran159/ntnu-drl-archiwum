from pathlib import Path
import argparse
import json
import numpy as np
from audit_motion_map import HINGE, map_vertices
from export_trajectory import csv_rows, digest

def coordinates(path):
    with path.open(encoding="utf8") as f:
        if not f.readline().startswith('"Position[X]'):
            raise ValueError("Expected actual STAR Position components")
    a=np.loadtxt(path,delimiter=",",skiprows=1,usecols=(0,1,2),ndmin=2)
    if len(a)<50 or not np.isfinite(a).all():
        raise ValueError("Invalid native vertex cloud")
    return a

def distance_max(a,b):
    maxima=[]
    for x,y in ((a,b),(b,a)):
        maxima.append(max(float(np.sqrt(((y-pt)**2).sum(axis=1).min())) for pt in x))
    return max(maxima)

def check(run):
    state=json.loads((run/"SOLVE_STATUS.json").read_text(encoding="utf8"))
    h=csv_rows(run/"motion.csv")
    origin=coordinates(run/"vertices_0000.csv")
    reasons=[]
    if state["status"]!="MOTION_NATIVE_PENDING_VERTEX_REVIEW" or len(h)!=40:
        reasons.append("Incomplete kinematic path")
    if set(np.round(np.unique(origin[:,2]),9))!={0.0,.02}:
        reasons.append("Span layers do not match 0 and 20 mm")
    deviations=[]
    for i,row in enumerate(h,1):
        native=coordinates(run/f"vertices_{i:04d}.csv")
        prediction=np.column_stack([map_vertices(origin[:,:2],float(row["delta_command_deg"])),origin[:,2]])
        deviations.append(distance_max(native,prediction))
        if float(row["min_volume_m3"])<=0 or float(row["min_face_validity"])<.5 or float(row["min_cell_quality"])<=0:
            reasons.append(f"Native mesh guard, sample {i}")
        if abs(float(row["delta_command_deg"])-float(row["delta_measured_deg"]))>.08:
            reasons.append(f"Angle error, sample {i}")
    if not deviations or max(deviations)>2e-5:
        reasons.append("Vertex cloud deviates from map by >20 micrometres")
    r=dict(status="PASS_KINEMATICS_ONLY" if not reasons else "HOLD",reasons=reasons,
           max_position_error_m=max(deviations,default=None),samples=len(h),
           checkpoint_sha256=digest(run/"FINAL.sim"),training_approved=False)
    (run/"MOTION_REVIEW.json").write_text(json.dumps(r,indent=2),encoding="utf8")
    return r

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("run",type=Path)
    print(json.dumps(check(parser.parse_args().run),indent=2))


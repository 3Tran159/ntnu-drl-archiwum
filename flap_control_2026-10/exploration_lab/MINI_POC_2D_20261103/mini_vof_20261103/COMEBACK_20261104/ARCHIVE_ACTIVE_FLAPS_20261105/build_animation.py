import csv
import json
from pathlib import Path
import sys
P=Path(r"F:/ntnu/flap_control/exploration_lab/MINI_POC_2D_20261103/mini_vof_20261103/COMEBACK_20261104")
base=P/"WALL_FUNCTIONS_AUDIT/ACTIVE_GAP25_PRISM_20261104"
sys.path.insert(0,str(base/"plot_dependencies"))
import numpy as np
from run import cases,T,H,read

HX=.952
HY=.02128173276777

def s(x):
    q=np.clip(x,0,1)
    return q**3*(10-15*q+6*q*q)

def mesh(kind):
    name="SEALED_OUTER_MESH_GAPPED" if kind=="gap" else "SEALED_SHARP_MATCHED_OUTER"
    dat=np.load(base/name/"plot_mesh.npz")
    edges=np.concatenate((dat["main"],dat["flap"]))
    ids=np.unique(edges)
    xy=dat["xy"][ids]
    x,y=(xy-[HX,HY]).T
    radius=np.hypot(x,y)
    blend=(np.maximum(s((.03755-radius)/.00235),s((x+.00745)/.00745))
           if kind=="gap" else s(x/.035))
    weight=blend*s((1.4-radius)/1.1)
    arrays=np.searchsorted(ids,edges)
    return xy,weight,{"vertices":np.round(np.column_stack((x,y,weight)),11).tolist(),
           "main":arrays[:len(dat["main"])].tolist(),"flap":arrays[len(dat["main"]):].tolist()}

def main():
    geo={}
    for kind in ("sealed","gap"):
        geo[kind]=mesh(kind)
    simulations=[]
    for name,folder,file,origin,partial in cases:
        src=T/folder
        info=read(src/"RESULT.json")
        with (src/file).open(newline="") as f:
            rows=list(csv.DictReader(f))
        angles=[float(r["delta_measured_deg"]) for r in rows]
        x=Path(info["checkpoint"]).parent/"vertices_final.csv"
        kind="gap" if "Gap25" in name else "sealed"
        xy,weight,_=geo[kind]
        if x.is_file():
            native=np.loadtxt(x,delimiter=",",skiprows=1,usecols=(0,1))
            a=np.deg2rad(angles[-1])*weight
            u,v=(xy-[HX,HY]).T
            moved=np.column_stack((HX+u*np.cos(a)+v*np.sin(a),HY-u*np.sin(a)+v*np.cos(a)))
            err=max(np.sqrt(((native[:,None,:]-moved[None,:,:])**2).sum(axis=2)).min(axis=1))
            if err>2e-7:
                raise RuntimeError(f"Native vertices mismatch in {name}: {err}")
            print(name, "max native-wall verification error [m]", err)
        frames=[[0,0]]+[[round(float(r["time_s"])-origin,8),round(a,8)] for r,a in zip(rows,angles)]
        label=("2.5 mm gap" if kind=="gap" else "Sharp sealed")+" · "+("±2°" if "Minus2" in name else "±5°")
        if partial:
            label+=" · partial / CFL hold"
        simulations.append(dict(label=label,geometry=kind,frames=frames,partial=partial))
    data=dict(geometries={k:v[2] for k,v in geo.items()},cases=simulations)
    html=(Path(__file__).with_name("motion_template.html")).read_text(encoding="utf-8")
    out=H/"geometry_animation.html"
    out.write_text(html.replace("/* CFD_DATA */",json.dumps(data,separators=(",",":"))),encoding="utf-8")

if __name__=="__main__":
    main()


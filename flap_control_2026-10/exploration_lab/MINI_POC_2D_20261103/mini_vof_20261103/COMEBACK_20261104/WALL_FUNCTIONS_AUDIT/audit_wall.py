import csv
import json
import math
import os
from pathlib import Path
import sys
from collections import defaultdict

import numpy as np

HERE=Path(__file__).resolve().parent
CB=HERE.parent
ROOT=CB.parents[1]
sys.path.insert(0,str(CB))
from audit_motion_map import map_vertices
sys.path.insert(0,str(ROOT.parent/"tools"/"deps"))
import gmsh

C=1.19
U=18.
NU=1e-6
RE=U*C/NU
CF=.075/(math.log10(RE)-2)**2
USTAR=U*math.sqrt(CF/2)
ZONES=("LE","main suction","main pressure","hinge","flap suction","flap pressure","TE")

def load_mesh(path):
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal",0)
        gmsh.open(str(path))
        tags,p,_=gmsh.model.mesh.getNodes()
        xy=np.array(p).reshape(-1,3)[:,:2]
        ids={int(t):i for i,t in enumerate(tags)}
        cells=[]
        for kind,_,data in zip(*gmsh.model.mesh.getElements(2)):
            width={2:3,3:4}[kind]
            cells.extend(tuple(ids[int(t)] for t in a) for a in np.array(data).reshape(-1,width))
        walls=[]
        for dim,tag in gmsh.model.getPhysicalGroups(1):
            name=gmsh.model.getPhysicalName(dim,tag)
            if name not in ("main","flap"):continue
            for e in gmsh.model.getEntitiesForPhysicalGroup(dim,tag):
                for a in gmsh.model.mesh.getElements(1,e)[2]:
                    for u,v in np.array(a).reshape(-1,2):
                        walls.append((ids[int(u)],ids[int(v)],name))
        if not walls:raise ValueError("Mesh wall groups missing")
        return xy,cells,walls
    finally:
        gmsh.finalize()

def quant(v,w,probs=(.05,.5,.95)):
    order=np.argsort(v)
    a,b=v[order],w[order]
    return [float(x) for x in np.interp(probs,(np.cumsum(b)-.5*b)/b.sum(),a)]

def zone(x,name,ny):
    if x/C<=.05:return "LE"
    if .77<=x/C<=.83:return "hinge"
    if x/C>=.97:return "TE"
    return name+(" suction" if ny>0 else " pressure")

def centroid(p):
    d=p-p[0]
    q=np.roll(d,-1,axis=0)
    cross=d[:,0]*q[:,1]-d[:,1]*q[:,0]
    return p[0]+np.sum((d+q)*cross[:,None],axis=0)/(3*cross.sum())

def wall_geometry(path):
    xy,cells,walls=load_mesh(path)
    adjacency=defaultdict(list)
    for i,cell in enumerate(cells):
        for j,a in enumerate(cell):
            b=cell[(j+1)%len(cell)]
            adjacency[tuple(sorted((a,b)))].append((i,j))
    geom=[]
    for a,b,name in walls:
        e=tuple(sorted((a,b)))
        [(ix,j)]=adjacency[e]
        cell=cells[ix]
        a,b=cell[j],cell[(j+1)%len(cell)]
        t=xy[b]-xy[a]
        length=np.linalg.norm(t)
        n=np.array([-t[1],t[0]])/length
        center=(xy[a]+xy[b])/2
        ycenter=float((centroid(xy[list(cell)])-center)@n)
        if ycenter<=0:raise ValueError("Unexpected wall adjacency orientation")
        layer=[]
        edge=e
        used=set()
        while len(layer)<30:
            nxt=[pair for pair in adjacency[edge] if pair[0] not in used]
            if len(nxt)!=1: break
            ii,jj=nxt[0]
            cc=cells[ii]
            if len(cc)!=4:break
            u,v=cc[(jj+2)%4],cc[(jj+3)%4]
            mid=(xy[u]+xy[v])/2
            height=float((mid-center)@n)
            if height<=0 or (layer and height<=layer[-1]):break
            if height>0.025:break
            layer.append(height)
            edge=tuple(sorted((u,v)))
            used.add(ii)
        dh=np.diff([0,*layer])
        geom.append(dict(a=a,b=b,cell=ix,x=center[0],y=center[1],length=length,
            side=name,zone=zone(center[0],name,n[1]),first_centroid_m=ycenter,
            first_layer_m=layer[0] if layer else None,quad_layers=len(layer),
            first_prism_volume_m3=float(np.sum(np.cross(xy[list(cell)]-xy[cell[0]],np.roll(xy[list(cell)]-xy[cell[0]],-1,axis=0)))*.01),
            max_local_expansion=float(max(dh[1:]/dh[:-1])) if len(dh)>1 else None))
    return xy,cells,geom

def group_geometry(g):
    result={}
    for z in ("all",*ZONES):
        sel=[a for a in g if z=="all" or a["zone"]==z]
        w=np.array([a["length"] for a in sel])
        y=np.array([a["first_centroid_m"] for a in sel])
        thickness=np.array([a["first_layer_m"] or np.nan for a in sel])
        q=np.isfinite(thickness)
        layers=np.array([a["quad_layers"] for a in sel])
        ratios=np.array([a["max_local_expansion"] or np.nan for a in sel])
        r=np.isfinite(ratios)
        result[z]=dict(faces=len(sel),centroid_y_um_p05_p50_p95=quant(y*1e6,w),
           predicted_yplus_p05_p50_p95=quant(y*USTAR/NU,w),wall_quad_area_pct=float(w[q].sum()/w.sum()*100),
           first_quad_thickness_um_p05_p50_p95=quant(thickness[q]*1e6,w[q]) if np.any(q) else None,
           quad_rows_p05_p50_p95=quant(layers,w),
           worst_measured_expansion_p05_p50_p95=quant(ratios[r],w[r]) if np.any(r) else None)
    return result

def wall_values(csvfile,geom):
    data=np.loadtxt(csvfile,delimiter=",",skiprows=1)
    centers=np.array([[g["x"],g["y"]] for g in geom])
    samples=data[:,2:4]
    dist=((centers[:,None,:]-samples[None,:,:])**2).sum(axis=2)
    ids=np.argmin(dist,axis=1)
    err=float(np.max(np.sqrt(np.min(dist,axis=1))))
    if err>1e-7 or len(set(ids))!=len(ids):raise ValueError(f"STAR wall export/mesh mismatch {err} m")
    result=[]
    for g,j in zip(geom,ids):
        result.append(dict(x_m=g["x"],y_m=g["y"],zone=g["zone"],area_m2=g["length"]*.02,
                           wall_yplus=float(data[j,1]),Cp=float(data[j,0])))
    return result,err

def summarize(data):
    result={}
    for z in ("all",*ZONES):
        rows=[a for a in data if z=="all" or a["zone"]==z]
        w=np.array([a["area_m2"] for a in rows])
        y=np.array([a["wall_yplus"] for a in rows])
        result[z]=dict(faces=len(rows),yplus_p05_p50_p95=quant(y,w),yplus_min=float(y.min()),yplus_max=float(y.max()),
            area_pct_30_100=float(100*w[(y>30)&(y<100)].sum()/w.sum()),
            area_pct_50_70=float(100*w[(y>=50)&(y<=70)].sum()/w.sum()))
    return result

def motion_check(xy,cells,geom):
    sides=[np.array([cells[a["cell"]] for a in geom if len(cells[a["cell"]])==size]) for size in (3,4)]
    ids=np.array([a["a"] for a in geom]);ends=np.array([a["b"] for a in geom])
    angle_results=[]
    for deg in np.linspace(-2,2,41):
        x=map_vertices(xy,deg)
        least=np.inf;nonpos=0
        for g in sides:
            if not len(g):continue
            p=x[g];u=np.roll(p,-1,axis=1)-p;v=np.roll(u,-1,axis=1)
            j=u[:,:,0]*v[:,:,1]-u[:,:,1]*v[:,:,0]
            least=min(least,float(j.min()))
            nonpos+=int((j<=0).sum())
        angle_results.append(dict(angle_deg=float(deg),nonpositive_near_wall_corner_count=nonpos,min_corner_jacobian_m2=least))
    return angle_results

def output_csv(path,rows):
    with path.open("w",newline="",encoding="utf8") as f:
        c=csv.DictWriter(f,fieldnames=rows[0]);c.writeheader();c.writerows(rows)

def make_plot(wall,q):
    os.environ["MPLCONFIGDIR"]=str(CB/"mpl_cache")
    sys.path.insert(0,str(CB.parents[3]/"hydro_validation_2606_20261102"/"tools"/"deps"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    fig,ax=plt.subplots(2,1,figsize=(11,6.5),layout="constrained")
    a=ax[0].scatter([p["x_m"]/C for p in wall],[p["y_m"]/C for p in wall],
            c=[p["wall_yplus"] for p in wall],s=9,cmap="viridis",norm=Normalize(0,100))
    ax[0].set(xlabel="x/c",ylabel="y/c",title="Native STAR Wall Y+ | archived sealed 0°, single phase")
    ax[0].set_aspect("equal",adjustable="box")
    for x in (.05,.77,.80,.83,.97):ax[0].axvline(x,color=".5",lw=.7,ls=":")
    fig.colorbar(a,ax=ax[0],label="Wall Y+",extend="max")
    ax[1].axvspan(30,100,color="tab:green",alpha=.14,label="ITTC design range")
    y=[p["wall_yplus"] for p in wall];w=np.array([p["area_m2"] for p in wall])
    ax[1].hist(y,bins=np.linspace(0,max(105,max(y)),48),weights=100*w/w.sum(),color="#2a7b93")
    ax[1].set(xlabel="Wall Y+",ylabel="Wetted area [% per bin]",title="Wall-face area weighted")
    ax[1].legend(frameon=False)
    fig.savefig(HERE/"ARCHIVED_SEALED_WALL_YPLUS.png",dpi=180)
    plt.close(fig)

def main():
    xy,cells,q=wall_geometry(CB.parent/"SEALED0_A005"/"geometry_and_mesh.msh")
    g0=wall_geometry(ROOT/"sealed_demo_delta_0"/"geometry_and_mesh.msh")[2]
    wall,e=wall_values(ROOT/"sealed0_fast_20261103"/"Cp_yplus.csv",g0)
    report=dict(reynolds=RE,cf=CF,friction_velocity_m_s=USTAR,design={str(a):dict(centroid_um=a*NU/USTAR*1e6,
        full_layer_um=2*a*NU/USTAR*1e6) for a in (30,50,60,70,100)},
        q2d_cells=len(cells),q2d_mesh=group_geometry(q),kinematics_offline=motion_check(xy,cells,q),
        archived_wall_0deg=summarize(wall),archived_wall_match_error_m=e,
        measured_q2d_wall_yplus=False)
    g2=wall_geometry(ROOT/"sealed_c2_delta_2"/"geometry_and_mesh.msh")[2]
    w2,e2=wall_values(ROOT/"sealed_c2_delta_2"/"Cp_yplus.csv",g2)
    report.update(archived_wall_2deg=summarize(w2),archived_wall_2deg_match_error_m=e2)
    output_csv(HERE/"archived_sealed0_wall.csv",wall)
    output_csv(HERE/"archived_sealed2_wall.csv",w2)
    output_csv(HERE/"q2d_wall_geometry.csv",q)
    (HERE/"WALL_AUDIT.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf8")
    make_plot(wall,q)
    print(json.dumps({k:v for k,v in report.items() if k!="kinematics_offline"},indent=2))

if __name__=="__main__":main()



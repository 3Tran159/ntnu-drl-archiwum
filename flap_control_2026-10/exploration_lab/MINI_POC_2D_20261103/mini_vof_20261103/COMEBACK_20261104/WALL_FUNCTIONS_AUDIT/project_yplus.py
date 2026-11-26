from pathlib import Path
import json
import os
import sys
import numpy as np

from audit_wall import HERE, CB, ROOT, C, quant, wall_geometry, output_csv, ZONES
old=CB.parent/"SEALED0_A005"/"geometry_and_mesh.msh"
new=HERE/"HIGH_YPLUS_CANDIDATE_V2"/"geometry_and_mesh.msh"
_,_,a=wall_geometry(old)
_,_,b=wall_geometry(new)
a=sorted(a,key=lambda r:(r["x"],r["y"]))
b=sorted(b,key=lambda r:(r["x"],r["y"]))
if max(np.hypot(v["x"]-w["x"],v["y"]-w["y"]) for v,w in zip(a,b))>1e-12:
    raise ValueError("Wall geometry changed")
arch=np.loadtxt(ROOT/"sealed0_fast_20261103"/"Cp_yplus.csv",delimiter=",",skiprows=1)
x=np.array([(v["x"],v["y"]) for v in a])
j=np.argmin(((x[:,None,:]-arch[None,:,2:4])**2).sum(axis=2),axis=1)
assert np.max(abs(x-arch[j,2:4]))<1e-9
y=arch[j,1]
ratio=np.array([v["first_centroid_m"]/w["first_centroid_m"] for v,w in zip(b,a)])
est=y*ratio
wt=np.array([v["length"] for v in a])
zones=np.array([v["zone"] for v in a])
rows=[]
for z in ["all",*ZONES]:
    m=zones==z if z!="all" else np.ones(len(y),dtype=bool)
    rows.append(dict(zone=z,area_fraction=float(wt[m].sum()/wt.sum()),
                     measured_archived_yplus_p05_p50_p95=quant(y[m],wt[m]),
                     projected_yplus_fixed_wall_shear_p05_p50_p95=quant(est[m],wt[m]),
                     projected_area_fraction_30_100=float(wt[m&(est>30)&(est<100)].sum()/wt[m].sum()),
                     projected_area_fraction_50_70=float(wt[m&(est>=50)&(est<=70)].sum()/wt[m].sum())))
(HERE/"CANDIDATE_YPLUS_PROJECTION.json").write_text(json.dumps(
    dict(method="archived single-phase y+ times measured wall-centroid-distance ratio, fixed wall shear assumption",
         candidate_solver_executed=False,zones=rows),indent=2),encoding="utf8")
os.environ["MPLCONFIGDIR"]=str(CB/"mpl_cache")
sys.path.insert(0,str(CB.parents[3]/"hydro_validation_2606_20261102"/"tools"/"deps"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig,ax=plt.subplots(3,1,figsize=(11,8),layout="constrained")
for axis,v,title,lim in ((ax[0],y,"Archive: measured STAR y+ · sealed 0°, single-phase",12),
                         (ax[1],est,"Candidate: projected y+ if wall shear were unchanged · CFD pending",110)):
    h=axis.scatter(x[:,0]/C,x[:,1]/C,c=v,s=12,vmin=0,vmax=lim,cmap="viridis")
    axis.set(xlabel="x/c",ylabel="y/c",title=title)
    axis.set_aspect("equal",adjustable="box")
    for q in (.05,.77,.83,.97):axis.axvline(q,ls=":",color=".55",lw=.7)
    fig.colorbar(h,ax=axis,label="y+")
ax[2].axvspan(30,100,color="tab:green",alpha=.13,label="ITTC design range")
for arr,label in ((y,"Measured archive"),(est,"Candidate projection")):
    ax[2].hist(arr,bins=np.arange(0,155,3),weights=wt/wt.sum()*100,histtype="step",lw=1.5,label=label)
ax[2].set(xlabel="y+",ylabel="Wetted area [% per bin]")
ax[2].legend(frameon=False)
fig.savefig(HERE/"WALL_YPLUS_BASELINE_AND_PROJECTION.png",dpi=175)
print(json.dumps(rows,indent=2))


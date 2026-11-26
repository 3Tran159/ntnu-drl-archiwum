import sys,json,csv
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
sys.path.insert(0,str(r/"deps311"))
import h5py,numpy as np,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"svg.fonttype":"none"})
out=r/"plots";out.mkdir(exist_ok=True)
colors={"M01":"#167e92","M02":"#bc6115","M03":"#704cb6"}
for name in ["M01","M02","M03"]:
 p=r/name/"mesh.CGNS"
 if not p.exists():continue
 with h5py.File(p) as f:
  z=f["Base/fluid"];xz=np.column_stack([z["GridCoordinates/CoordinateX/ data"][...],z["GridCoordinates/CoordinateZ/ data"][...]])
  g=z["Q2D_span_source"];con=g["ElementConnectivity/ data"][...]-1;off=g["ElementStartOffset/ data"][...]
  edges=set()
  for i in range(len(off)-1):
   v=con[off[i]:off[i+1]]
   for a,b in zip(v,np.roll(v,-1)):edges.add(tuple(sorted((int(a),int(b)))))
  lines=xz[np.array(list(edges))]
  fig,axs=plt.subplots(1,3,figsize=(14,4.4),layout="constrained")
  limits=[(-.04,1.24,-.13,.16),(-.015,.065,-.032,.045),(1.12,1.205,-.035,.045)]
  titles=["Profil i warstwy przyścienne","Krawędź natarcia","Krawędź spływu"]
  for ax,lim,title in zip(axs,limits,titles):
   mask=(lines[:,:,0].min(axis=1)<lim[1])&(lines[:,:,0].max(axis=1)>lim[0])&(lines[:,:,1].min(axis=1)<lim[3])&(lines[:,:,1].max(axis=1)>lim[2])
   ax.add_collection(LineCollection(lines[mask],colors="#244459",linewidths=.35))
   ax.set(xlim=lim[:2],ylim=lim[2:],title=title,xlabel="x [m]",ylabel="z [m]");ax.set_aspect("equal")
  fig.suptitle(name+" · rzeczywista siatka na boku wycinka")
  fig.savefig(out/(name+"_mesh.png"),dpi=150);fig.savefig(out/(name+"_mesh.svg"));plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(14,4.1),layout="constrained")
for name,color in colors.items():
 p=r/name/"F18_dt500us/history.csv"
 if not p.exists():continue
 with p.open() as f:data=[{k:float(v) if v else None for k,v in row.items()} for row in csv.DictReader(f)]
 data=[x for x in data if x["physical_time_s"]>=.002]
 for ax,key,title in zip(axs,["CD","CL_total","foil_mean_yplus"],["CD (rozruch, od t=0,002 s)","CL z wyporem (rozruch)","Średnie y+ po powierzchni"]):
  ax.plot([x["physical_time_s"] for x in data],[x[key] for x in data],label=name,color=color,lw=1.8);ax.set(title=title,xlabel="Czas fizyczny [s]");ax.grid(alpha=.2);ax.legend()
fig.suptitle("Porównanie siatek przy dt = 0,5 ms · 18 m/s · siły jeszcze nieustalone")
fig.savefig(out/"mesh_comparison.png",dpi=150);fig.savefig(out/"mesh_comparison.svg");plt.close(fig)
print("Saved plots",str(out))

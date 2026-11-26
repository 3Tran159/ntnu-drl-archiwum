"""Area-weighted native y+ on the fixed V2 foil."""
import json
from pathlib import Path
import sys

import numpy as np
from summarize_h010 import field, col

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/"WALL_FUNCTIONS_AUDIT"))
from audit_wall import load_mesh, quant, zone, ZONES

out = Path(sys.argv[1])
names, data = field(out/"wall_yplus_pressure.csv")
xyz = data[:,[col(names,"X ("),col(names,"Y (")]]
yplus = data[:,col(names,"Wall Y+")]
mesh = HERE/"WALL_FUNCTIONS_AUDIT"/"HIGH_YPLUS_CANDIDATE_V2"/"geometry_and_mesh.msh"
xy, cells, walls = load_mesh(mesh)
edges = xy[np.array([[a,b] for a,b,_ in walls])]
center = edges.mean(axis=1)
length = np.linalg.norm(edges[:,1]-edges[:,0],axis=1)
idx = np.argmin(np.linalg.norm(center[:,None]-xyz[None,:],axis=2),axis=1)
gap = float(np.max(np.linalg.norm(center-xyz[idx],axis=1)))
if len(set(idx.tolist())) != len(walls) or len(data) != len(walls) or gap > 1e-7:
    raise RuntimeError(f"Wall table is not one matching face per extruded edge: {gap} m")
yplus = yplus[idx]
tags = np.array([zone(center[i,0],name,-(xy[b]-xy[a])[0]) for i,(a,b,name) in enumerate(walls)])
metrics = {}
for tag in ("all",*ZONES):
    use = tags==tag if tag!="all" else np.ones(len(tags),dtype=bool)
    if not np.any(use):
        continue
    yp, w = yplus[use], length[use]
    metrics[tag] = dict(p05_p50_p95=quant(yp,w),pct_area_30_100=float(100*w[(yp>=30)&(yp<=100)].sum()/w.sum()),
                        max=float(yp.max()),faces=int(use.sum()))
(out/"NATIVE_WALL_YPLUS_SUMMARY.json").write_text(json.dumps(metrics,indent=2))
print(json.dumps(metrics,indent=2))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
fig, axes = plt.subplots(2,1,figsize=(9,6),layout="constrained",gridspec_kw={"height_ratios":[1,2]})
lines = LineCollection(edges, cmap="viridis", linewidth=2)
lines.set_array(yplus)
axes[0].add_collection(lines)
axes[0].autoscale()
axes[0].set_aspect("equal")
fig.colorbar(lines,ax=axes[0],label="Wall y+")
for tag in ZONES:
    use=tags==tag
    if use.any():
        axes[1].scatter(center[use,0]/1.19,yplus[use],s=8,label=tag)
axes[1].axhspan(30,100,color="#d9ead3",alpha=.45)
axes[1].legend(ncols=3,frameon=False)
axes[1].set(xlabel="x/c",ylabel="Wall y+")
fig.suptitle("V2 fixed foil | native STAR wall values at last saved step")
fig.savefig(out/"NATIVE_WALL_YPLUS.png",dpi=180)


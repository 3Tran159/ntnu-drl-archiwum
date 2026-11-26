from pathlib import Path
import json
import numpy as np

out=Path(__file__).resolve().parent
base=out.parents[1]
case=Path(json.loads((out/"RESULT.json").read_text())["checkpoint"]).parent
grid=np.load(base/"SEALED_SHARP_MATCHED_OUTER/plot_mesh.npz")
result={}
for group in ("main","flap"):
    cells=grid["xy"][grid[group]]
    lengths=np.linalg.norm(cells[:,1]-cells[:,0],axis=1)
    a=np.loadtxt(case/f"yplus_2400_{group}.csv",delimiter=",",skiprows=1)
    delta=np.linalg.norm(a[:,None,1:3]-cells.mean(axis=1)[None,:,:],axis=2)
    ids=delta.argmin(axis=1)
    if len(ids)!=len(lengths) or len(set(ids))!=len(ids) or np.max(delta.min(axis=1))>1e-7:
        raise RuntimeError("Mesh-to-native wall face mismatch")
    w=lengths[ids]
    y=a[:,0]
    order=np.argsort(y)
    rank=(np.cumsum(w[order])-.5*w[order])/w.sum()
    result[group]=dict(faces=len(y),weighted_p10_p50_p90=np.interp([.1,.5,.9],rank,y[order]).tolist(),
                       fraction_area_yplus_30_to_100=float(w[(y>=30)&(y<=100)].sum()/w.sum()))
(out/"YPLUS_T0600.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))


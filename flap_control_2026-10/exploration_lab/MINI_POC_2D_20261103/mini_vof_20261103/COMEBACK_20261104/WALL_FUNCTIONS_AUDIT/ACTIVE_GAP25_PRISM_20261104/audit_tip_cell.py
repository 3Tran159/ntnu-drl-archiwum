import numpy as np
from pathlib import Path
d=Path(__file__).resolve().parent
m=np.load(d/"plot_mesh.npz")
xy=m["xy"]
for group in ("triangles","quads"):
    p=xy[m[group]]
    mid=p.mean(axis=1)
    indices=np.argsort(np.linalg.norm(mid-[1.1900198238029007,-.00010273634662672022],axis=1))[:8]
    for i in indices:
        a=p[i]
        delta=np.roll(a,-1,axis=0)-a
        print(group,i,mid[i],a.tolist(),np.linalg.norm(delta,axis=1).tolist())
print("Trailing wall faces:")
print(xy[m["flap"]][(xy[m["flap"]][:,:,0].max(axis=1)>1.186)])


from pathlib import Path
import json
import numpy as np

d = Path(__file__).resolve().parent
mesh = np.load(d/"plot_mesh.npz")
xy = mesh["xy"]
quads = mesh["quads"]
edges = {tuple(sorted((int(a),int(b)))): cell
         for cell in quads for a,b in zip(cell,np.roll(cell,-1))}
output = {}
for name in ("main","flap"):
    ab = xy[mesh[name]]
    edge = ab[:,1]-ab[:,0]
    lengths = np.linalg.norm(edge,axis=1)
    cell = np.array([edges[tuple(sorted(e))] for e in mesh[name]])
    p = xy[cell]
    n = np.roll(p,-1,axis=1)
    cross = p[...,0]*n[...,1]-p[...,1]*n[...,0]
    centroid = ((p+n)*cross[...,None]).sum(axis=1)/(3*cross.sum(axis=1)[:,None])
    v = centroid - ab[:,0]
    y = abs(edge[:,0]*v[:,1]-edge[:,1]*v[:,0])/lengths
    predicted = y * .65387 / 1e-6
    output[name] = dict(cell_centroid_distance_mm=np.percentile(y*1000,[0,10,50,90,100]).tolist(),
                        flat_plate_yplus_estimate=np.percentile(predicted,[0,10,50,90,100]).tolist(),
                        min_edge_mm=float(lengths.min()*1000))
(d/"WALL_LAYER_GEOMETRY_AUDIT.json").write_text(json.dumps(output,indent=2))
print(json.dumps(output,indent=2))


from build_gap_mesh import move

def distance(a, b):
    v = b[:, 1] - b[:, 0]
    h = a[:, None, :] - b[None, :, 0, :]
    t = np.clip(np.sum(h * v, axis=-1) / np.sum(v * v, axis=-1), 0, 1)
    return np.linalg.norm(h - t[..., None] * v, axis=-1).min()

fixed = xy[mesh["main"]]
flap = xy[mesh["flap"]]
gap = {}
for angle in np.linspace(-2, 2, 41):
    rotated = move(flap.reshape(-1,2),angle).reshape(-1,2,2)
    gap[str(round(angle,2))] = float(min(distance(fixed[:,0],rotated),distance(rotated[:,0],fixed))*1000)
(d/"MESH_GAP_CLEARANCE.json").write_text(json.dumps(gap,indent=2))
print("Clearance [mm] at -2, 0, +2:",[gap[str(a)] for a in (-2.,0.,2.)],"minimum",min(gap.values()))


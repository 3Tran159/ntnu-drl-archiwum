from pathlib import Path
import json
import sys

import numpy as np
from plot_gap import OUT, SEALED, plt, LineCollection

CB = OUT.parents[1]
sys.path.insert(0,str(CB/"WALL_FUNCTIONS_AUDIT"))
from audit_wall import load_mesh
from audit_motion_map import HINGE, map_vertices
from matplotlib.patches import Rectangle

OUTPUT = Path(sys.argv[1]) if len(sys.argv)>1 else OUT/"AFT_ONLY_PRESSURE_GATE"
GAP_MESH = OUTPUT if (OUTPUT/"plot_mesh.npz").exists() else OUT
RUN_PREFIX = {"TRAILING_EDGE_LAYER_RELIEF":"ACTIVE_GAP25_TIP_RELIEF", "SEALED_OUTER_MESH_GAPPED":"ACTIVE_GAP25_MATCHED_OUTER"}.get(OUTPUT.name,"ACTIVE_GAP25_FLAP_MARGIN")


def rigid(points, delta):
    a=np.radians(delta)
    transform=np.array([[np.cos(a),np.sin(a)],[-np.sin(a),np.cos(a)]])
    return (points-HINGE)@transform.T+HINGE


def native_outline(expected, source):
    xyz=np.loadtxt(source,delimiter=",",skiprows=1)[:,:2]
    flat=expected.reshape(-1,2)
    distance=np.linalg.norm(flat[:,None,:]-xyz[None,:,:],axis=-1)
    nearest=distance.argmin(axis=1)
    if np.max(distance[np.arange(len(nearest)),nearest])>2e-6:
        raise ValueError(f"Native vertices do not match expected moving wall topology: {source}")
    return xyz[nearest].reshape(expected.shape)


def connected_paths(edges):
    pending={tuple(sorted(map(int,p))) for p in edges}
    paths=[]
    while pending:
        degree={}
        for a,b in pending:
            degree[a]=degree.get(a,0)+1
            degree[b]=degree.get(b,0)+1
        start=next((n for n,c in degree.items() if c==1),min(degree))
        path=[start]
        while True:
            edge=next((pair for pair in pending if path[-1] in pair),None)
            if edge is None:
                break
            pending.remove(edge)
            path.append(edge[0] if edge[1]==path[-1] else edge[1])
        paths.append(np.array(path))
    return paths


def draw(name, xy, cells, main, flap, files, sealed):
    groups = [(np.array([c for c in cells if len(c)==n]), color)
              for n,color in ((3,"#a7b8c5"),(4,"#5594bc"))]
    meshes=[(np.stack([xy[c],xy[np.roll(c,-1,axis=1)]],axis=2).reshape(-1,2,2), color)
            for c,color in groups if len(c)]
    fig=plt.figure(figsize=(10.4,8.0 if sealed else 8.6),layout="constrained")
    gs=fig.add_gridspec(3 if sealed else 4, 1, height_ratios=[1.1,1.05,1.3] if sealed else [1.1,1.05,1.2,1.3])
    axs=[fig.add_subplot(gs[i,0]) for i in range(gs.nrows)]
    extrema=[]
    paths=connected_paths(flap)
    for angle,path,colour,style in zip((-2,2),files,("#126ba1","#b94b75"),((0,(5,3)),(0,(3,2)))):
        vertices=map_vertices(xy,angle) if sealed else rigid(xy,angle)
        expected=[vertices[path] for path in paths]
        if path and path.exists():
            lines=[native_outline(chain,path) for chain in expected]
            state="STAR vertices"
        else:
            lines=expected
            state="prescribed motion"
        extrema.append((lines,colour,style,f"{angle:+d}° · {state}"))
    for i,ax in enumerate(axs):
        for segments,color in meshes:
            ax.add_collection(LineCollection(segments,colors=color,lw=.29 if i==0 else .48,alpha=.58 if i else .55,rasterized=True))
        ax.set_aspect("equal")
        ax.set_ylabel("Vertical position [m]")
        if i:
            for wall,col,label in ((main,"#354a5b","Fixed main foil"),(flap,"#e48c42","Flap at 0°")):
                ax.add_collection(LineCollection(xy[wall],colors=col,lw=1.55,label=label,zorder=3))
            for lines,colour,style,label in extrema:
                ax.add_collection(LineCollection(lines,colors=colour,linewidths=1.4,
                                                linestyles=style,label=label,zorder=5))
            ax.scatter(*HINGE,s=16,c="#263b4d",zorder=7)
    xlim=(float(xy[:,0].min()),float(xy[:,0].max()))
    ylim=(float(xy[:,1].min()),float(xy[:,1].max()))
    axs[0].set(xlim=xlim,ylim=ylim,title="A  Full computational domain")
    axs[0].add_patch(Rectangle((-.16,-.14),1.51,.32,facecolor="none",edgecolor="#e48c42",lw=1.15))
    axs[1].set(xlim=(-.16,1.35),ylim=(-.073,.137),title="B  Foil and mesh at 0° with extreme flap positions")
    axs[2].set(xlim=(.885,1.205),ylim=(-.029,.077),title="C  Flap close-up | clockwise positive")
    axs[2].annotate("Hinge axis · x/c = 0.80",HINGE,xytext=(.965,.066),
                    arrowprops={"arrowstyle":"-","color":"#354a5b"},fontsize=8)
    if not sealed:
        axs[3].set(xlim=(.911,.929),ylim=(.009,.034),title="D  Hinge clearance and wall-layer cells")
        axs[3].set_xticks([.915,.925])
    for ax in axs: ax.set_xlabel("Streamwise position [m]")
    axs[1].legend(loc="lower center",bbox_to_anchor=(.5,-.08),ncol=4,frameon=True,fontsize=7.5)
    kind=("Sharp sealed active flap" if OUTPUT.name=="SEALED_SHARP_MATCHED_OUTER" else "Sealed active flap") if sealed else "Active flap with a nominal 2.5 mm gap"
    note = "Matched sealed outer mesh | neutral mesh with ±2° flap outlines" if not sealed and OUTPUT.name=="SEALED_OUTER_MESH_GAPPED" else "Neutral mesh with ±2° flap outlines"
    fig.suptitle(f"{kind} | {len(cells):,} cells\n{note}",fontweight="bold")
    fig.savefig(OUTPUT/name,dpi=210)
    plt.close(fig)


if OUTPUT.name=="SEALED_SHARP_MATCHED_OUTER":
    g=np.load(OUTPUT/"plot_mesh.npz")
    draw("SEALED_SHARP_MESH_FLAP_EXTREMA_EN.png",g["xy"],g["triangles"].tolist()+g["quads"].tolist(),g["main"],g["flap"],[None,None],True)
    raise SystemExit(0)

smesh=CB/"WALL_FUNCTIONS_AUDIT/COARSE_FACETED_OPEN_CELLS/geometry_and_mesh.msh"
xy,cells,walls=load_mesh(smesh)
draw("SEALED_MESH_FLAP_EXTREMA_EN.png",xy,cells,np.array([(a,b) for a,b,n in walls if n=="main"]),
     np.array([(a,b) for a,b,n in walls if n=="flap"]),
     [SEALED/"vertices_step0050.csv",SEALED/"vertices_step0150.csv"],True)

g=np.load(GAP_MESH/"plot_mesh.npz")
folder=None
for name,step1,step2 in (("DT0333MS",150,450),("DT050MS",100,300),("DT100MS",50,150)):
    candidates=sorted((CB/"runs").glob(f"{RUN_PREFIX}_{name}_*"),reverse=True)
    if candidates:
        candidate=candidates[0]
        paths=[candidate/f"vertices_step{i:04d}.csv" for i in (step1,step2)]
        if any(p.exists() for p in paths):
            folder=paths
            break
draw("GAPPED_MESH_FLAP_EXTREMA_EN.png",g["xy"],g["triangles"].tolist()+g["quads"].tolist(),
     g["main"],g["flap"],folder or [None,None],False)




from pathlib import Path
p=Path(__file__).resolve().parent/"plot_mesh_extrema.py"
s=p.read_text(encoding="utf8")
s=s.replace("def draw(name, xy, cells, main, flap, files, sealed):",'''def connected_paths(edges):
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


def draw(name, xy, cells, main, flap, files, sealed):''')
s=s.replace("    extrema=[]","    extrema=[]\n    paths=connected_paths(flap)")
s=s.replace('        expected=(map_vertices(xy,angle)[flap] if sealed else rigid(xy[flap],angle))','        vertices=map_vertices(xy,angle) if sealed else rigid(xy,angle)\n        expected=[vertices[path] for path in paths]')
s=s.replace('            lines=native_outline(expected,path)','            lines=[native_outline(chain,path) for chain in expected]')
s=s.replace('title="D  Hinge clearance and wall-layer cells")','title="D  Hinge clearance and wall-layer cells")\n        axs[3].set_xticks([.915,.925])')
p.write_text(s,encoding="utf8")


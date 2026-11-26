from pathlib import Path

root=Path(__file__).resolve().parent
out=root/"SEALED_SHARP_MATCHED_OUTER"
out.mkdir(exist_ok=False)
s=(root/"SEALED_OUTER_MESH_GAPPED"/"build_matched_mesh.py").read_text(encoding="utf8")
s=s.replace('return np.maximum(smooth((.03755 - radius)/.00235), smooth((x + .00745)/.00745)) * smooth((1.4 - radius)/1.1)',
            'return smooth(x/.035) * smooth((1.4 - radius)/1.1)')
start=s.index('        for name in ("main", "flap"):')
end=s.index('        dom = ',start)
s=s[:start]+'''        profile = solid("intact")
        points = []
        for a,b in zip(profile,np.roll(profile,-1,axis=0)):
            points.append(a)
            if (a[0]-hinge[0])*(b[0]-hinge[0])<0:
                t=(hinge[0]-a[0])/(b[0]-a[0])
                points.append(np.array([hinge[0],a[1]+t*(b[1]-a[1])]))
        poly=np.array(points)
        ids=[geo.addPoint(*p,0) for p in poly]
        lines=[geo.addLine(a,b) for a,b in zip(ids,ids[1:]+ids[:1])]
        groups["main"]=[]
        groups["flap"]=[]
        for a,b,line in zip(poly,np.roll(poly,-1,axis=0),lines):
            name="flap" if (a[0]+b[0])/2>hinge[0]+1e-10 else "main"
            groups[name].append(line)
            wall_curves.append(line)
            if name!="flap" or max(a[0],b[0])<1.188:
                prism_curves.append(line)
            if np.linalg.norm((a+b)/2-hinge)<.044:
                hinge_curves.append(line)
        loops.append(geo.addCurveLoop(lines))
'''+s[end:]
s=s.replace('    assert np.max(abs(weight[wall_nodes["flap"]] - 1)) < 1e-8, np.min(weight[wall_nodes["flap"]])',
'''    flap_aft = wall_nodes["flap"][xy[wall_nodes["flap"],0] >= hinge[0]+.035]
    assert len(flap_aft)>0 and np.max(abs(weight[flap_aft] - 1)) < 1e-8''')
s=s.replace('gap_nominal_m=.0025','gap_nominal_m=0., sharp_trailing_edge=True, trailing_edge_x_m=float(xy[wall_nodes["flap"],0].max())')
s=s.replace('minimum_flap_weight=float(np.min(weight[wall_nodes["flap"]]))','minimum_rigid_flap_weight=float(np.min(weight[flap_aft])), sealed_blend_length_m=.035')
s=s.replace('Gapped flap with wall-layer quadrilaterals','Sharp sealed flap with wall-layer quadrilaterals')
s=s.replace('Gapped NACA 66-012 MOD','Sharp sealed NACA 66-012 MOD')
s=s.replace('OUT / "geometry_and_mesh.msh"','OUT / "cavity_gmsh.msh"')
(out/"build_matched_sharp_sealed.py").write_text(s,encoding="utf8")


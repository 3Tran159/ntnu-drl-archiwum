from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'prepare_geometry.py';s=p.read_text()
s=s.replace("for a,b,c in triangulate(poly):\n  tris.append([(poly[k][0],-.02,poly[k][1]) for k in (a,b,c)])\n  tris.append([(poly[k][0],.02,poly[k][1]) for k in (c,b,a)])","from shapely import constrained_delaunay_triangles\n for tri in constrained_delaunay_triangles(Polygon(poly)).geoms:\n  pp=list(tri.exterior.coords)[:3]\n  if area(pp)<0:pp.reverse()\n  tris.append([(x,-.02,z) for x,z in pp])\n  tris.append([(x,.02,z) for x,z in reversed(pp)])")
s=s.replace("gap_m=gap","gap_m=clearance,nose_radius_m=radius")
s=s.replace("Coarse native-profile demonstrator with artificial 2% chord clearance; not hydrodynamically validated","Native NACA 66-012 modified contour; rounded flap nose and matching hinge recess; 1.5% chord radial clearance; not hydrodynamically validated")
p.write_text(s)
p=R/'macros/BuildFlapPOC.java';s=p.read_text().replace('import star.common.*;','import star.common.*;import star.metrics.*;')
s=s.replace('s.getSolverStoppingCriterionManager().getSolverStoppingCriterion(InnerIterationStoppingCriterion.class).setIsUsed(true);','for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())if(c instanceof InnerIterationStoppingCriterion){c.setIsUsed(true);((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(8);}')
s=s.replace('s.getSolverStoppingCriterionManager().getSolverStoppingCriterion(InnerIterationStoppingCriterion.class).setMaximumNumberInnerIterations(8);','')
p.write_text(s)
print('Updated coarse geometry and 2606 macro APIs')

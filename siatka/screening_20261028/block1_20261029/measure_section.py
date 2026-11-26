import json,math,collections
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028\block1_20261029")
text=(root/"foil_fine.stl").read_text()
pts=[tuple(map(float,line.split()[1:4])) for line in text.splitlines() if line.split() and line.split()[0]=="vertex"]
tris=[pts[i:i+3] for i in range(0,len(pts),3)]
segments=[]
for tri in tris:
    hits=[]
    for a,b in zip(tri,tri[1:]+tri[:1]):
        if abs(a[1]-b[1])<1e-12:continue
        t=-a[1]/(b[1]-a[1])
        if -1e-10<=t<=1+1e-10:
            p=(a[0]+t*(b[0]-a[0]),a[2]+t*(b[2]-a[2]))
            if not any(math.dist(p,h)<1e-9 for h in hits): hits.append(p)
    if len(hits)==2:segments.append(hits)
def section_at(x):
    zs=[]
    for (xa,za),(xb,zb) in segments:
        if abs(xb-xa)<1e-12:continue
        t=(x-xa)/(xb-xa)
        if -1e-9<=t<=1+1e-9:zs.append(za+t*(zb-za))
    return [min(zs),max(zs)] if zs else None
samples=[]
for i in range(1,1000):
    x=1.19*i/1000
    zz=section_at(x)
    if zz:samples.append({"x_over_c":x/1.19,"thickness_over_c":(zz[1]-zz[0])/1.19,"camber_over_c":sum(zz)/2/1.19,"z_lower":zz[0],"z_upper":zz[1]})
max_t=max(samples,key=lambda p:p["thickness_over_c"])
max_c=max(samples,key=lambda p:p["camber_over_c"])
ends=[p for seg in segments for p in seg]
out={"root_section_max_vertical_thickness":max_t,"root_section_max_camber":max_c,
"section_at_nominal_LE_x0":section_at(0),"section_at_nominal_TE_x1_19":section_at(1.19),
"closest_section_point_to_nominal_LE":min(ends,key=lambda p:math.hypot(*p)),
"closest_section_point_to_nominal_TE":min(ends,key=lambda p:math.hypot(p[0]-1.19,p[1]))}
edge_counts=collections.Counter()
for tri in tris:
    rounded=[tuple(round(v,9) for v in p) for p in tri]
    for a,b in zip(rounded,rounded[1:]+rounded[:1]):edge_counts[tuple(sorted([a,b]))]+=1
out["edge_multiplicity_counts"]=dict(collections.Counter(edge_counts.values()))
r=json.loads((root/"geometry_metrics.json").read_text());S=r["stl"][1]["half_sum_absolute_projected_area_yz_xz_xy"][2]
out["S_ref_full_projected_m2"]=S;out["S_ref_half_projected_m2"]=S/2
out["mean_geometric_chord_m"]=S/11
out["area_ref_comparison"]={"previous_nominal_full_m2":9.823,"recipe_full_m2":10.897425,"coefficient_change_from_previous_percent":100*(9.823/S-1),"coarse_to_fine_projected_area_change_percent":100*(S/r["stl"][0]["half_sum_absolute_projected_area_yz_xz_xy"][2]-1)}
out["night_common_time_coefficients"]=[]
for case in ["D001","D002","D003","D004"]:
    import csv
    with open(Path(r"E:\ntnu_cfd_night_20261028")/case/"history.csv") as f:
        history=list(csv.DictReader(f))
    row=min(history,key=lambda x:abs(float(x["physical_time_s"])-.0002))
    if abs(float(row["physical_time_s"])-.0002)>1e-10:raise ValueError("Missing common time")
    fx=float(row["Fx_half_N"]);fz=float(row["Fz_half_N"])
    out["night_common_time_coefficients"].append({"case":case,"time_s":float(row["physical_time_s"]),"Fx_half_N":fx,"Fz_half_N":fz,"mean_yplus":float(row["foil_mean_yplus"]),"C_D":fx/(162000*S/2),"C_L":fz/(162000*S/2)})
(root/"block1_geometry_summary.json").write_text(json.dumps(out,indent=2))
(root/"root_section_samples.json").write_text(json.dumps(samples))
print(json.dumps(out,indent=2))

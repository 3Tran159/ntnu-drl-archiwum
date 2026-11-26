import json, math
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028\block1_20261029")
samples=json.loads((root/"root_section_samples.json").read_text())
chord=1.19
def points(file):
    out=[]
    for line in file.read_text().splitlines():
        p=line.split()
        if len(p)==2:
            try: out.append(tuple(map(float,p)))
            except ValueError: pass
    return out
def section(pts,x):
    z=[]
    for a,b in zip(pts,pts[1:]+pts[:1]):
        if abs(a[0]-b[0])<1e-14: continue
        t=(x-a[0])/(b[0]-a[0])
        if -1e-12<=t<=1+1e-12:z.append(a[1]+t*(b[1]-a[1]))
    if len(z)<2:raise ValueError((x,z))
    return min(z),max(z)
result={"cad_source":"foil_fine.stl; actual HF_v2 CAD in baseline_clean.sim","root_chord_m":chord,"comparison_interval_x_over_c":[.02,.98],"method":"Vertical intersections of source DAT polygon compared with tessellated CAD root section; linear interpolation introduces discretization error.","profiles":{}}
for name in ["010","012"]:
    pts=points(root/("reference_"+name+".dat"))
    errors=[]; ts=[]; stations=[]
    for s in samples:
        x=s["x_over_c"]
        low,up=section(pts,x)
        ts.append((up-low,x))
        if .02<=x<=.98:
            errors.extend([s["z_lower"]/chord-low,s["z_upper"]/chord-up])
        if any(abs(x-v)<1e-8 for v in [.1,.3,.465,.5,.7,.9]):
            stations.append({"x_over_c":x,"cad_t_c":s["thickness_over_c"],"reference_t_c":up-low})
    result["profiles"][name]={"point_count":len(pts),"max_vertical_thickness_c":max(ts)[0],"x_at_max_thickness_c":max(ts)[1],"surface_rmse_c":math.sqrt(sum(e*e for e in errors)/len(errors)),"surface_rmse_mm":1000*chord*math.sqrt(sum(e*e for e in errors)/len(errors)),"max_surface_error_mm":1000*chord*max(map(abs,errors)),"reference_peak_upper_m":max(p[1] for p in pts)*chord,"reference_peak_lower_m":min(p[1] for p in pts)*chord,"stations":stations}
result["cad_max_vertical_thickness_c"]=max(s["thickness_over_c"] for s in samples)
result["cad_max_vertical_thickness_mm"]=1000*chord*result["cad_max_vertical_thickness_c"]
result["rmse_ratio_012_to_010"]=result["profiles"]["012"]["surface_rmse_c"]/result["profiles"]["010"]["surface_rmse_c"]
(root/"profile_identity_comparison.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

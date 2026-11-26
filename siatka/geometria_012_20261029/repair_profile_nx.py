import json,hashlib,traceback,re
from pathlib import Path
import NXOpen
root=Path(r"F:\ntnu\geometry_012_20261029")
source=Path(r"F:\ntnu\HF_v2.prt")
target=root/"HF_012_v3.prt"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def formulas(stem,point):
    x,z=[format(float(v),".16g") for v in point]
    dx="((%s)-HF_pivot_xc)"%x
    a,c=stem+"a",stem+"c"
    return ("%sqx+%s*(%s*cos(%s)+(%s)*sin(%s))"%(stem,c,dx,a,z,a),
            "%sqz+%s*(-%s*sin(%s)+(%s)*cos(%s))"%(stem,c,dx,a,z,a))
def export_stl(s,p,name):
    e=s.DexManager.CreateStlCreator()
    try:
        e.OutputFile=str(root/name)
        e.OutputType=NXOpen.STLCreator.OutputTypeEnum.Binary
        e.ChordalTol=0.01
        e.AngularTol=0.5
        e.AdjacencyTol=0.001
        e.AutoNormalGen=True
        e.ExportSelectionBlock.Add(list(p.Bodies))
        e.Commit()
    finally:e.Destroy()
try:
    if target.exists():raise RuntimeError("Target exists; refusing overwrite")
    original_sha=sha(source)
    old_xt_sha=sha(Path(r"F:\ntnu\HF_v2.x_t"))
    m=json.loads((root/"profile_point_replacement.json").read_text())
    s=NXOpen.Session.GetSession()
    p,ls=s.Parts.OpenBaseDisplay(str(source))
    if p is None:raise RuntimeError("Source part load failed")
    ls.Dispose()
    expr={e.Name:e for e in p.Expressions}
    masters={k:expr[k].Value for k in ["HF_span","HF_root_chord","HF_taper","HF_center_fraction","HF_sweep_deg","HF_dihedral_deg","HF_incidence_deg","HF_tip_twist_deg","HF_pivot_xc"]}
    expected=[11000,1190,.33,.5,0,0,0,0,.25]
    if any(abs(a-b)>1e-10 for a,b in zip(masters.values(),expected)):raise RuntimeError("Unexpected master dimensions")
    if len(list(p.Bodies))!=1 or not list(p.Bodies)[0].IsSolidBody:raise RuntimeError("Original is not one solid")
    edits=[]
    for i in range(5):
        stem="HF_s%02d_"%i
        for j,(old,new) in enumerate(zip(m["old_points"],m["new_points"])):
            for axis,oldrhs,newrhs in zip("xz",formulas(stem,old),formulas(stem,new)):
                name=stem+"p%03d_"%j+axis
                if re.sub(r"\s","",expr[name].RightHandSide)!=re.sub(r"\s","",oldrhs):
                    raise RuntimeError("Unexpected source formula: "+name)
                edits.append((name,newrhs))
    if len(edits)!=1600:raise RuntimeError("Unexpected coordinate count")
    export_stl(s,p,"native_original_fine_mm.stl")
    mark=s.SetUndoMark(NXOpen.Session.MarkVisibility.Visible,"Replace verified 010 source coordinates with 012")
    for name,rhs in edits:p.Expressions.EditExpression(expr[name],rhs)
    errors=s.UpdateManager.DoUpdate(mark)
    if errors:raise RuntimeError("NX update errors: "+str(errors))
    bodies=list(p.Bodies)
    if len(bodies)!=1 or not bodies[0].IsSolidBody:raise RuntimeError("Updated model is not one solid")
    if any(abs(expr[k].Value-v)>1e-10 for k,v in masters.items()):raise RuntimeError("Master geometry changed")
    bodies[0].SetName("HF_012_v3")
    export_stl(s,p,"native_012_fine_mm.stl")
    status=p.SaveAs(str(target))
    unsaved=status.NumberUnsavedParts
    status.Dispose()
    if unsaved:raise RuntimeError("SaveAs reported unsaved parts")
    ex=s.DexManager.CreateParasolidExporter()
    try:
        ex.ExportFrom=NXOpen.ParasolidExporter.ExportFromOption.DisplayedPart
        ex.ObjectTypes.Curves=False
        ex.ObjectTypes.Surfaces=False
        ex.ObjectTypes.Solids=True
        ex.OutputFile=str(root/"HF_012_v3.x_t")
        ex.ParasolidVersion=NXOpen.ParasolidExporter.ParasolidVersionOption.Ps371Nx2506
        ex.ExportSelectionBlock.SelectionComp.Add(bodies)
        ex.Commit()
    finally:ex.Destroy()
    if sha(source)!=original_sha or sha(Path(r"F:\ntnu\HF_v2.x_t"))!=old_xt_sha:raise RuntimeError("Original hash changed")
    result={"status":"NX_REBUILT_PENDING_SECTION_AND_STAR_CHECK","original_prt_sha256":original_sha,"original_xt_sha256":old_xt_sha,"target_prt":str(target),"target_prt_sha256":sha(target),"target_xt_sha256":sha(root/"HF_012_v3.x_t"),"source_012_sha256":m["source_012_sha256"],"edited_coordinate_expressions":len(edits),"master_values_unchanged":masters,"solid_count":len(bodies),"face_count":len(bodies[0].GetFaces()),"update_error_count":errors,"tessellation_tolerance_mm":.01,"method":"Replace all verified old DAT point coordinate constants with verified 012 DAT coordinates; preserve expressions, station laws and downstream NX features."}
    (root/"nx_repair_result.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
except Exception:
    (root/"nx_repair_error.txt").write_text(traceback.format_exc())
    print(traceback.format_exc())
    raise

import json,hashlib,traceback
from pathlib import Path
import NXOpen
root=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
source=Path(r"F:\ntnu\geometry_012_20261029\HF_012_v3.prt")
try:
    target=root/"HF_012_constant_section.prt"
    assert not target.exists()
    original_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    s=NXOpen.Session.GetSession()
    p,ls=s.Parts.OpenBaseDisplay(str(source));ls.Dispose()
    expr={e.Name:e for e in p.Expressions}
    mark=s.SetUndoMark(NXOpen.Session.MarkVisibility.Visible,"Constant verified 012 section for quasi 2D")
    for name,val in {"HF_span":"1000","HF_taper":"1"}.items():
        p.Expressions.EditExpression(expr[name],val)
    errors=s.UpdateManager.DoUpdate(mark)
    assert errors==0
    bodies=list(p.Bodies)
    assert len(bodies)==1 and bodies[0].IsSolidBody
    bodies[0].SetName("HF_012_constant_section")
    st=p.SaveAs(str(target));assert st.NumberUnsavedParts==0;st.Dispose()
    ex=s.DexManager.CreateParasolidExporter()
    ex.ExportFrom=NXOpen.ParasolidExporter.ExportFromOption.DisplayedPart
    ex.ObjectTypes.Curves=False;ex.ObjectTypes.Surfaces=False;ex.ObjectTypes.Solids=True
    ex.OutputFile=str(root/"HF_012_constant_section.x_t")
    ex.ParasolidVersion=NXOpen.ParasolidExporter.ParasolidVersionOption.Ps371Nx2506
    ex.ExportSelectionBlock.SelectionComp.Add(bodies);ex.Commit();ex.Destroy()
    e=s.DexManager.CreateStlCreator()
    e.OutputFile=str(root/"HF_012_constant_section_mm.stl")
    e.OutputType=NXOpen.STLCreator.OutputTypeEnum.Binary
    e.ChordalTol=.01;e.AngularTol=.5;e.AdjacencyTol=.001;e.AutoNormalGen=True
    e.ExportSelectionBlock.Add(bodies);e.Commit();e.Destroy()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original_sha
    d={"source_sha256":original_sha,"solid_count":len(bodies),"face_count":len(bodies[0].GetFaces()),"masters":{n:expr[n].Value for n in ["HF_span","HF_root_chord","HF_taper","HF_sweep_deg","HF_incidence_deg","HF_tip_twist_deg"]},"fluid_slice_y_m":[.01,.03],"fluid_span_m":.02,"reference_area_m2":1.19*.02,"note":"Constant corrected 012 section; narrow fluid slice inside one loft interval avoids station seams. Source unchanged."}
    (root/"section_geometry.json").write_text(json.dumps(d,indent=2))
    print(json.dumps(d))
except Exception:
    (root/"nx_section_error.txt").write_text(traceback.format_exc())
    raise

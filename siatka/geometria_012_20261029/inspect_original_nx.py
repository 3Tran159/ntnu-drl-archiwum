import json, traceback
from pathlib import Path
import NXOpen
import NXOpen.UF
out=Path(r"F:\ntnu\geometry_012_20261029")
try:
    s=NXOpen.Session.GetSession()
    p,status=s.Parts.OpenBaseDisplay(r"F:\ntnu\HF_v2.prt")
    load_messages=[{"file":status.GetPartName(i),"code":status.GetStatus(i),"message":status.GetStatusDescription(i)} for i in range(status.NumberUnloadedParts)]
    (out/"nx_load_status.json").write_text(json.dumps(load_messages),encoding="utf-8")
    print(json.dumps({"load_status":load_messages}))
    status.Dispose()
    if p is None: raise RuntimeError("Part was not loaded; see nx_load_status.json")
    uf=NXOpen.UF.UFSession.GetUFSession()
    result={"part":p.FullPath,"units":str(p.PartUnits),"expressions":[{"name":e.Name,"rhs":e.RightHandSide,"value":e.Value} for e in p.Expressions],"features":[],"bodies":[]}
    for f in p.Features:
        item={"type":f.FeatureType,"name":f.Name,"journal_id":f.JournalIdentifier}
        try:item["parents"]=[g.JournalIdentifier for g in f.GetParents()]
        except Exception as ex:item["parents_error"]=str(ex)
        result["features"].append(item)
    for b in p.Bodies:
        result["bodies"].append({"tag":int(b.Tag),"solid":b.IsSolidBody,"name":b.Name,"faces":len(b.GetFaces())})
    (out/"nx_original_inventory.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"status":"ok","expression_count":len(result["expressions"]),"feature_count":len(result["features"]),"features":result["features"],"bodies":result["bodies"]}))
except Exception:
    (out/"nx_original_inventory_error.txt").write_text(traceback.format_exc(),encoding="utf-8")
    print(traceback.format_exc())
    raise

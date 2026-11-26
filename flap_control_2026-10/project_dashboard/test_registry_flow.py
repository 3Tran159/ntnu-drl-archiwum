"""Regression tests for controller-discovered runs & archived CFD flow fields.
Never modifies campaign sources, solver, queue, checkpoint or STAR session.
"""
import csv, json, math, time, threading, urllib.request, urllib.error
from pathlib import Path
import server, ramp_live, runs_registry as registry, flow_field as flow

RESULTS=[]
def test(label,ok,details=""):
    passed=bool(ok)
    RESULTS.append({"test":label,"pass":passed,"detail":str(details)})
    print(("PASS " if passed else "FAIL ")+label+(" "+str(details) if details else ""),flush=True)
    return passed

def states():
    root=flow.CAMP
    paths=[
        root/"NIGHT_QUEUE_STATE.json",root/"NIGHT_STATUS.json",
        root/"cases"/"SP_C_split0_overset"/"ramp_plus2_20261103_093316"/"history.csv",
        root/"cases"/"SP_C_split0_overset"/"ramp_plus2_20261103_094340"/"history.csv",
        root/"cases"/"SP_C_split0_overset"/"ramp_plus2_20261103_093316"/"Background_final_volume.csv",
        root/"cases"/"SP_C_split0_overset"/"ramp_plus2_20261103_093316"/"FlapOverset_final_volume.csv",
    ]
    return {str(x):(x.stat().st_size,x.stat().st_mtime_ns) if x.is_file() else None for x in paths}

def main():
    before=states()
    rs=registry.list_runs()
    ids={r["id"]:r for r in rs}
    test("Controller discovers multiple independent run_ids",len(rs)>=10,len(rs))
    test("Explicit smoke/production grouped",ids["exp:RAMP_C0_PLUS2_S5_20261103"]["segments"]==2)
    ramp=registry.fetch_series("exp:RAMP_C0_PLUS2_S5_20261103")
    test("RAMP 5+73 unique samples",ramp["count"]==78,len(ramp["history"]))
    test("RAMP fail is preserved",ramp["status"]=="FAILED",ramp["status"])
    test("No expectation of new ramp samples",abs(ramp["history"][-1]["t"]-.806)<1e-9)
    test("RAMP time never duplicated",len({round(row["t"],9) for row in ramp["history"]})==78)
    test("RAMP provenance for 2 controller segments",len(ramp["sources"])==2)
    test("RAMP first and last segments distinct",ramp["provenance"][0]["id"]!=ramp["provenance"][1]["id"])
    test("Known latest dynamic run discovered",any("SPEED_SWEEP" in x for x in ids))
    test("External approved controller output root discovered", "exp:C0_SPEED_DOWN_20261103" in ids)
    speed=registry.fetch_series("exp:C0_SPEED_DOWN_20261103")
    test("External speed-down 20 source samples",speed is not None and speed["count"]==20 and abs(speed["history"][-1]["t"]-.690)<1e-9)
    test("External speed-down is diagnostic, not accepted",speed is not None and speed["status"]=="DIAGNOSTIC")
    test("Unknown dynamic run rejected",registry.fetch_series("../foo") is None)
    test("Case paths constrained to campaign",registry.is_controller_case(r"F:\ntnu\flap_control\project_dashboard") is None)
    test("Legacy reference series retained",all(k in server.RUNS for k in ("B0","C0","A0","K0","W02","W03","W04pre")))
    m=registry.manifest([{"id":i,"label":i,"status":"DIAGNOSTIC"} for i in server.RUNS])
    test("Combined registry contains all references + controller runs",m["total"]==len(rs)+len(server.RUNS))
    # Explicit scientific acceptance must be recorded; completion alone remains diagnostic.
    fake={"id":"future","state":"completed","run_id":"future001","_folder":str(registry.CASE_ROOT/"foo"),
          "_history":ramp["source"],"_mtime":time.time(),"macro_status":{}}
    test("Completed alone never scientific ACCEPTED",registry.status_for([fake])=="DIAGNOSTIC")
    test("Explicit accepted scientific gate",registry.status_for([dict(fake,macro_status={"scientific_approved":True})])=="ACCEPTED")
    test("Failed remains FAILED",registry.status_for([dict(fake,state="failed",macro_status={})])=="FAILED")
    test("New run_id becomes registry key",registry.run_key(fake)=="run:future001")
    # In-memory restart overlap, never edit controlled CSV.
    prev=registry.read_history_file
    segment_a={"id":"A","_history":"A","_mtime":1}
    segment_b={"id":"B","_history":"B","_mtime":2}
    def fake_read(path):
        return [{"time_s":".650","CL":".1"},{"time_s":".652","CL":".2"}] if path=="A" else \
               [{"time_s":".652","CL":".3"},{"time_s":".654","CL":".4"}]
    try:
        registry.read_history_file=fake_read
        out,count,details=registry.merged_history([segment_a,segment_b])
        test("Restart overlapping samples collapse",count==3)
        test("New segment overrides matching time",abs(out[1]["CL"]-.3)<1e-12)
    finally:registry.read_history_file=prev
    fm=flow.manifest()
    test("Flow fields come from same named ramp",fm["experiment"]=="RAMP_C0_PLUS2_S5_20261103")
    test("Two or more actual vector snapshots",len([f for f in fm["frames"] if f["has_velocity"]])>=2)
    test("Latest full velocity older than failed solver",fm["latest_vector_field_time_s"]<fm["ramp"]["t"])
    test("Later mesh-only frame not fabricated into flow",any(f["kind"]=="mesh" and abs(f["time_s"]-.804)<1e-9 for f in fm["frames"]))
    test("Cp blocked without validated pressure reference",any("Cp" in note for note in fm["limitations"]))
    chosen=next(f for f in fm["frames"] if f["kind"]=="flow" and abs(f["time_s"]-.660)<1e-9)
    frame=flow.frame_data(chosen["id"],"foil")
    test("Native source field time preserved",abs(frame["time_s"]-.660)<1e-9)
    test("Real Background/FlapOverset layers",set(x["name"] for x in frame["layers"])=={"Background","FlapOverset"})
    test("Background has >1000 active populated bins",len(frame["layers"][0]["cells"])>1000,len(frame["layers"][0]["cells"]))
    test("FlapOverset has native populated active cells",len(frame["layers"][1]["cells"])>100,len(frame["layers"][1]["cells"]))
    test("Velocity and pressure are from actual columns",frame["has_velocity"] and frame["has_pressure"])
    test("No inactive/acceptor cells enter raster",all(isinstance(c[0],int) and isinstance(c[1],int) and c[2]>0 for layer in frame["layers"] for c in layer["cells"]))
    test("Native main and flap wall samples",all(len(w["points"])>80 for w in frame["walls"]))
    test("No full field on newest mesh-only snapshot",flow.frame_data(next(x for x in fm["frames"] if x["kind"]=="mesh")["id"],"hinge")["has_velocity"] is False)
    roi=flow.frame_data(chosen["id"],"hinge")
    test("Hinge ROI properly clipped",roi["bounds"]["x0"]>=.8 and roi["bounds"]["x1"]<=1.2)
    test("Invalid ROI rejected",_raises(lambda:flow.frame_data(chosen["id"],"bogus")))
    test("Invalid frame identity rejected",_raises(lambda:flow.frame_data("../checkpoint.sim","foil")))
    test("Native mesh image real",flow.native_image(chosen["id"],"mesh_hinge") is not None)
    zones=fm["pressure_zones"]["points"]
    last=[z for z in zones if z["zone"]=="liquid_all"][-1]
    test("Real point pressure at last failure",abs(last["t"]-.806)<1e-10 and abs(last["pabs"]-12333.273116792843)<1e-7)
    test("New 12.339 kPa screen",abs((last["pabs"]-flow.LIMIT)+5.7268832071568)<1e-7)
    http=server.serve("127.0.0.1",0)
    worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start()
    try:
        root="http://127.0.0.1:"+str(http.server_address[1])
        for ep in ("/api/runs","/api/run_series?id=exp%3ARAMP_C0_PLUS2_S5_20261103",
                   "/api/flow/manifest","/api/flow/frame?id="+chosen["id"]+"&region=hinge",
                   "/flow_field.js","/flow_field.css","/runs_registry.css","/api/flow/native?id="+chosen["id"]+"&view=mesh_hinge"):
            with urllib.request.urlopen(root+ep,timeout=25) as res:
                test("HTTP "+ep.split("?")[0],res.status==200)
        try:
            urllib.request.urlopen(root+"/api/run_series?id=unknown",timeout=7)
            test("Unknown run HTTP 404",False)
        except urllib.error.HTTPError as exc:test("Unknown run HTTP 404",exc.code==404)
    finally:http.shutdown();http.server_close()
    after=states()
    volatile=("NIGHT_QUEUE_STATE.json","NIGHT_STATUS.json")
    unchanged=all(before[k]==after[k] for k in before if not k.endswith(volatile))
    change=[str(k) for k in before if before[k]!=after[k]]
    test("Completed native CFD archives untouched",unchanged,
         "changed files: "+", ".join(change) if change else "no size/mtime changes")
    test("Only volatile controller metadata may change independently",
         all(k.endswith(volatile) for k in change),"external controller changes: "+str(change))
    out={"at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"passes":sum(x["pass"] for x in RESULTS),
         "total":len(RESULTS),"overall_pass":all(x["pass"] for x in RESULTS),
         "results":RESULTS,"policy":"READ ONLY; test artifacts only in project_dashboard"}
    (server.HERE/"REGISTRY_FLOW_TEST_REPORT.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",out["passes"],"/",out["total"],out["overall_pass"],flush=True)
    return 0 if out["overall_pass"] else 1

def _raises(callback):
    try:callback();return False
    except ValueError:return True

if __name__=="__main__":raise SystemExit(main())

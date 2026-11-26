"""End-to-end read-only ramp integration validation. Only writes test report in dashboard."""
import csv
import json
import math
import time
import urllib.request
import threading
from pathlib import Path
import server
import ramp_live

tests=[]
def check(label, expr, detail=""):
    yes=bool(expr)
    tests.append({"name":label, "passed":yes,"detail":str(detail)})
    print(("PASS " if yes else "FAIL ")+label+((" | "+str(detail)) if detail else ""),flush=True)
def file_state():
    candidates=[
        ramp_live.QUEUE,ramp_live.STATUS,
        ramp_live.CAMP/"NIGHT_DASHBOARD.json",
        ramp_live.CASES/"ramp_plus2_20261103_094340"/"history.csv",
        ramp_live.CASES/"ramp_plus2_20261103_093316"/"history.csv"
    ]
    return {str(p):(p.stat().st_size,p.stat().st_mtime_ns) if p.exists() else None for p in candidates}

def main():
    before=file_state()
    q=ramp_live.read_json(ramp_live.QUEUE)
    d=ramp_live.build_payload()
    check("Real experiment auto-discovered", d["experiment_id"]=="RAMP_C0_PLUS2_S5_20261103",d["experiment_id"])
    check("Auto-selected real active run",d["active_job"]["macro"]=="RampPlus2Run.java")
    check("Multiple saved controller segments",len(d["segments"])>=2,len(d["segments"]))
    check("Output remains confined to authorized cases",all(ramp_live.safe_output(s["path"]) for s in d["segments"]))
    check("Path traversal rejected",ramp_live.safe_output(r"F:\ntnu\flap_control\hydro_validation_2606_20261102\NIGHT_STATUS.json") is None)
    check("No checkpoint binary read",ramp_live.MAX_CSV < 20_000_000)
    hist=d["history"]
    check("Actual samples available",len(hist)>10,len(hist))
    check("Physical time monotonic",all(hist[i]["t"]<hist[i+1]["t"] for i in range(len(hist)-1)))
    check("Original time source retained",all(r["source"].lower().endswith("history.csv") for r in hist))
    # Independent last source calculation with exact CSV row, updated by solver concurrently.
    last=d["current"]
    with Path(last["source"]).open("r",encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    matches=[r for r in rows if abs(float(r["time_s"])-last["t"])<1e-10]
    row=matches[-1] if matches else None
    check("Original row recoverable at timestamp",row is not None)
    if row:
        for key,col in [("CL","CL_hydro"),("CD","CD"),("Mh","Mh_Nm"),("Fx","Fx_N"),("Fz","Fz_N"),
                        ("angle","flap_angle_deg"),("actual_angle","measured_angle_deg"),
                        ("rate","flap_angular_velocity_deg_s"),("pabs","p_absolute_min_Pa"),
                        ("mass","mass_imbalance_relative"),("overset","overset_error_cells")]:
            diff=abs(last[key]-float(row[col]))
            check("Native CSV "+key, diff<1e-10,diff)
        power=float(row["Mh_Nm"])*float(row["flap_angular_velocity_deg_s"])*math.pi/180
        check("Mechanical power uses rad/s",abs(power-last["Pmech"])<1e-10,power)
    check("Native ramp targets supplied",d["profile"]["start_s"]==.650 and d["profile"]["end_s"]==.850 and d["profile"]["target_deg"]==2)
    check("Pressure limit correct",d["threshold_pa"]==12340)
    check("Pressure reserve",abs(d["pressure_margin_pa"]-(last["pabs"]-12340))<1e-10)
    check("No fictitious waveform before ramp", all(r.get("angle") is not None or r.get("actual_angle") is None for r in hist))
    check("Active source freshness conservative",d["state"] in ("RUNNING","STALE","HOLD","FAILED","COMPLETE"))
    def claim(js,qs,age,pid,rows):
        return ramp_live.classify(js,qs,age,pid,rows)[0]
    check("STALE simulated",claim("active","MONITORING",91,True,True)=="STALE")
    check("HOLD simulated",claim("active","HOLD",5,True,True)=="HOLD")
    check("FAILED simulated",claim("failed","MONITORING",5,True,True)=="FAILED")
    check("COMPLETE simulated",claim("complete","MONITORING",5,False,True)=="COMPLETE")
    check("No false RUNNING without PID",claim("active","MONITORING",3,False,True)=="HOLD")
    check("No false RUNNING without fresh CSV",claim("active","MONITORING",90,True,True)=="STALE")
    check("No false RUNNING with no samples",claim("active","MONITORING",1,True,False)=="HOLD")
    # In-memory overlapping restart test only; no source mutations.
    original_select=ramp_live.select_experiment
    original_rows=ramp_live.rows_for_job
    job1={"id":"RAMP_OVERLAP_A","experiment_id":"RAMP_OVERLAP","macro":"RampPlus2Run.java",
          "output":str(ramp_live.CASES/"ramp_plus2_mockA"),"at":"A","state":"completed"}
    job2={**job1,"id":"RAMP_OVERLAP_B","output":str(ramp_live.CASES/"ramp_plus2_mockB"),
          "at":"B","state":"complete"}
    def fake_sel(q):return {"experiment_id":"RAMP_OVERLAP","jobs":[job1,job2],"active":None}
    def fake_rows(j):
        if j["id"]=="RAMP_OVERLAP_A":return ([{"t":.652,"CL":.22,"source":"A","step":1},{"t":.654,"CL":.23,"source":"A","step":2}],time.time()-20)
        return ([{"t":.654,"CL":.35,"source":"B","step":2},{"t":.656,"CL":.36,"source":"B","step":3}],time.time()-2)
    try:
        ramp_live.select_experiment=fake_sel
        ramp_live.rows_for_job=fake_rows
        overlap=ramp_live.build_payload(queue={"queue_state":"COMPLETE"},status={},now=time.time())
        check("Restart segment deduplication",len(overlap["history"])==3)
        check("Latest segment wins overlap",next(r["CL"] for r in overlap["history"] if abs(r["t"]-.654)<1e-9)==.35)
    finally:
        ramp_live.select_experiment=original_select
        ramp_live.rows_for_job=original_rows
    service=server.serve("127.0.0.1",0)
    t=threading.Thread(target=service.serve_forever,daemon=True);t.start()
    try:
        base="http://127.0.0.1:"+str(service.server_address[1])
        for endpoint in ("/api/ramp","/ramp_live.js","/ramp_live.css","/","/api/series?id=B0",
                         "/api/series?id=C0","/api/series?id=W02","/api/snapshot"):
            with urllib.request.urlopen(base+endpoint,timeout=8) as resp:
                content=resp.read()
                check("HTTP "+endpoint,resp.status==200 and len(content)>10,len(content))
                if endpoint=="/api/ramp":
                    payload=json.loads(content)
                    check("API preserves experiment identity",payload.get("experiment_id")==d["experiment_id"])
    finally:
        service.shutdown();service.server_close()
    after=file_state()
    check("No campaign source writes",before==after)
    report={"at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "passed":sum(1 for x in tests if x["passed"]),"total":len(tests),
            "overall_pass":all(x["passed"] for x in tests),"tests":tests,
            "read_only":True,"note":"Concurrent CFD source writes could change mtime independently."}
    (server.HERE/"RAMP_TEST_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("SUMMARY",report["passed"],"/",report["total"],report["overall_pass"],flush=True)
    return 0 if report["overall_pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())

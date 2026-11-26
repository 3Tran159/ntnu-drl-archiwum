"""Read-only integration and scientific provenance tests for NTNU dashboard.
Writes TEST_REPORT.json only in the dashboard directory.
"""
import csv
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from statistics import fmean
import server

TESTS=[]
def check(name,condition,detail=""):
    passed=bool(condition)
    TESTS.append({"test":name,"pass":passed,"detail":str(detail)})
    print(("PASS" if passed else "FAIL")+" "+name+" "+str(detail),flush=True)
    return passed
def get(url):
    with urllib.request.urlopen(url,timeout=7) as r:
        return r.status,r.headers,r.read()
def snapshot_files():
    files=[
        server.CAMP/"NIGHT_STATUS.json",
        server.CAMP/"NIGHT_QUEUE_STATE.json",
        server.CAMP/"NIGHT_DASHBOARD.json",
        server.VALID/"campaign_results.csv",
        server.B0/"history.csv",
        server.C0/"history.csv",
        server.VALID/"mesh_review_c0_tight_cage_v2_20261103_025110.json"
    ]
    return {str(p):[p.stat().st_size,p.stat().st_mtime_ns] if p.exists() else None for p in files}

def main():
    before=snapshot_files()
    data=server.snapshot()
    check("Campaign root exists",server.CAMP.is_dir())
    check("Source policy read-only",server.Handler.do_GET is not None and not hasattr(server.Handler,"do_POST"))
    check("Status never blindly RUNNING",data["state"] in ("HOLD","STOPPED","STALE","FAILED","OFFLINE","SAVING"))
    check("Status source provenance",bool(data.get("status_file")) and bool(data.get("source_status_at")))
    b=server.read_series("B0")
    c=server.read_series("C0")
    check("B0 100 rows",len(b["history"])==100)
    check("C0 100 rows",len(c["history"])==100)
    k=server.read_series("K0")
    w2=server.read_series("W02")
    w3=server.read_series("W03")
    check("K0 100 recorded kinematic steps",k["count"]==100)
    check("K0 frozen flow explicit",all(x.get("flow_frozen") is True for x in k["history"]))
    check("K0 actual measured deflection",max(abs(x["angle"]) for x in k["history"])>4.9)
    check("K0 zero overset errors",max(x.get("orphan") or 0 for x in k["history"])==0)
    check("K0 zero fake CL/CD",all(x["CL"] is None and x["CD"] is None for x in k["history"]))
    check("W02 wave actual CL history",len(w2["history"])>300 and sum(x["CL"] is not None for x in w2["history"])>300)
    check("W02 VOF foil probe",len(w2["gauges"])>50)
    check("W03 explicitly smoke test",w3["category"]=="SMOKE TEST")
    check("Native B0 residuals",len(b["residuals"])>=5)
    check("Native C0 residuals",len(c["residuals"])>=5)
    for label,obj in (("B0",b),("C0",c)):
        with Path(obj["source"]).open("r",encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        for key,orig in (("CL","CL_hydro"),("CD","CD"),("Mh","Mh_Nm")):
            independently=fmean(float(r[orig]) for r in rows[-25:])
            from_api=obj["stats"][key]["mean"]
            check(label+" "+key+" mean matches independent CSV",abs(independently-from_api)<1e-11,
                  "error="+str(abs(independently-from_api)))
        check(label+" measurement provenance",obj["stats"]["CL"]["n"]==25
              and abs(obj["stats"]["CL"]["to_s"]-float(rows[-1]["time_s"]))<1e-10)
    check("Scientific gate not overclaimed",data["validation"]["scientific_approved"] is False)
    check("Real STAR images available",len(data.get("images",[]))>=3)
    check("Exact mesh provenance",Path(data["mesh"].get("candidate","")).is_dir())
    check("Wave validation sources",len(data.get("waves",[]))>=3)
    wave_status={w["id"]:w for w in data.get("waves",[])}
    check("W01 qualitative only, no quantitative overclaim",wave_status["W01"]["qualitative_NWAR_accepted"] is True and wave_status["W01"]["scientific_NWAR_accepted"] is False)
    check("Kinematic state source acknowledged",data.get("kinematic_passed") is True)
    check("No checkpoint binary read",not any(str(x).endswith(".sim") for x in server.RUNS.values()))
    # Test offline/stale branch by stubbing metadata in memory, never editing source.
    original=server.stat_mtime
    old_cache=dict(server._cache)
    try:
        def stale_stamp(p):
            if str(p).endswith("NIGHT_STATUS.json"):
                return time.time()-1800
            return original(p)
        server.stat_mtime=stale_stamp
        server._cache["data"]=None
        stale=server.snapshot()
        check("Stale status detection",stale["state"]=="STALE",
              "state="+stale["state"])
        def missing_stamp(p):
            if str(p).endswith("NIGHT_STATUS.json"):
                return None
            return original(p)
        server.stat_mtime=missing_stamp
        server._cache["data"]=None
        offline=server.snapshot()
        check("Missing status detected OFFLINE",offline["state"]=="OFFLINE")
    finally:
        server.stat_mtime=original
        server._cache.update(old_cache)
    try:
        service=server.serve("127.0.0.1",0)
        port=service.server_address[1]
        th=threading.Thread(target=service.serve_forever,daemon=True)
        th.start()
        base="http://127.0.0.1:"+str(port)
        for endpoint in ("/","/styles.css","/app.js","/api/health","/api/snapshot",
                         "/api/series?id=B0","/api/series?id=C0","/api/series?id=K0",
                         "/api/series?id=W02","/api/series?id=W03","/api/history"):
            status,headers,body=get(base+endpoint)
            check("HTTP "+endpoint,status==200 and len(body)>0)
            if endpoint.startswith("/api/"):
                json.loads(body)
        status,headers,blob=get(base+"/media/"+data["images"][0]["key"])
        check("Whitelisted actual image",status==200 and len(blob)>100)
        try:
            get(base+"/api/series?id=doesnotexist")
            check("Reject unknown experiment",False)
        except urllib.error.HTTPError as exc:
            check("Reject unknown experiment",exc.code==404)
        try:
            get(base+"/media/..%2F..%2Fsecret.json")
            check("Reject path traversal",False)
        except urllib.error.HTTPError as exc:
            check("Reject path traversal",exc.code==404)
        check("No external script dependencies",b"cdn." not in get(base+"/")[2])
    finally:
        if "service" in locals():
            service.shutdown()
            service.server_close()
    after=snapshot_files()
    changed=[name for name in before if before[name]!=after[name]]
    check("Source files untouched during test",len(changed)==0,
          "changed="+",".join(changed) if changed else "no size or timestamp modifications")
    report={"at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"overall_pass":all(t["pass"] for t in TESTS),
            "passes":sum(x["pass"] for x in TESTS),"total":len(TESTS),
            "tests":TESTS,"note":"Time-based comparison may be affected by external Work updates; dashboard performs no source writes."}
    (server.HERE/"TEST_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("SUMMARY",report["passes"],"/",report["total"],"RESULT",report["overall_pass"],flush=True)
    return 0 if report["overall_pass"] else 1
if __name__=="__main__":
    sys.exit(main())

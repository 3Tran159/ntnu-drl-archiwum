import csv
import json
import os
import subprocess
from pathlib import Path
from run import D,H,cases,setup_cpu,read,sha,CLI,day_chain

cpu=setup_cpu()
manifest=H/"MANIFEST.json"
entries=read(manifest)
order=[cases[3],*cases[:3]]
for name,*_ in order:
    print("START",name,"CPU",cpu,flush=True)
    entry=entries[name]
    case=H/name
    sim=Path(entry["output"])
    if sha(sim)!=entry["output_sha256"]:
        raise RuntimeError("Input enriched archive changed")
    if entry.get("native_playback"):
        print("ALREADY VERIFIED",name,flush=True)
        continue
    preview=case/"native_playback"
    preview.mkdir(exist_ok=True)
    with (case/"trajectory.csv").open(newline="") as f:
        rows=[(0.,0.)]+[(float(row["elapsed_s"]),float(row["measured_deg"])) for row in csv.DictReader(f)]
    ids={round(i*(len(rows)-1)/40) for i in range(41)}
    ids.add(min(range(len(rows)),key=lambda i:rows[i][1]))
    ids.add(max(range(len(rows)),key=lambda i:rows[i][1]))
    with (preview/"frames.csv").open("w",newline="") as f:
        c=csv.writer(f);c.writerow(("elapsed_s","angle_deg"))
        c.writerows(rows[i] for i in sorted(ids))
    temp=preview/"WITH_PLAYBACK.sim"
    env={**os.environ,**day_chain.LIC,"FLAP_POST_DIR":str(case),
         "FLAP_PLAYBACK_GAP":str("Gap25" in name).lower(),"FLAP_POST_OUTPUT":str(temp)}
    args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(preview/"profile"),
          "-batch",str(D/"NativeFlapPlayback.java"),str(sim)]
    with (preview/"star.log").open("w",encoding="utf-8") as log:
        p=subprocess.run(args,cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    receipt=preview/"PLAYBACK_VERIFIED.json"
    if p.returncode or not temp.is_file() or not receipt.is_file():
        raise RuntimeError("Native playback did not verify for "+name)
    if len({sha(preview/file) for file in ("initial.png","minimum_angle.png","maximum_angle.png")})!=3:
        raise RuntimeError("Native playback frames appear identical")
    native=read(receipt)
    if abs(native["physical_time_s"]-entry["time_s"])>1e-9 or native["frames"]!=len(ids):
        raise RuntimeError("Geometry playback did not preserve archive time/frames")
    digest=sha(temp)
    os.replace(temp,sim)
    if sha(sim)!=digest:
        raise RuntimeError("Saved native playback checksum mismatch")
    entry.update(native_playback=native,output_sha256=digest)
    (case/"PROVENANCE.json").write_text(json.dumps(entry,indent=2))
    manifest.write_text(json.dumps(entries,indent=2))
    print("VERIFIED",name,flush=True)


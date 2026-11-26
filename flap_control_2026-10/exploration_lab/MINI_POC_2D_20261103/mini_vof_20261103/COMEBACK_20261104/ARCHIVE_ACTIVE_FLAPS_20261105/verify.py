from pathlib import Path
import json
import os
import subprocess
import time
from run import D,H,cases,setup_cpu,read,sha,CLI,day_chain

for wait in range(900):
    manifest=H/"MANIFEST.json"
    if manifest.is_file():
        try:
            if len(read(manifest))==4:
                break
        except (ValueError,OSError):
            pass
    time.sleep(2)
else:
    raise RuntimeError("Primary exports did not complete")
cpu=setup_cpu()
manifest=H/"MANIFEST.json"
entries=read(manifest)
for name,*_ in cases:
    print("REOPEN",name,flush=True)
    entry=entries[name]
    case=H/name
    sim=Path(entry["output"])
    if sha(sim)!=entry["output_sha256"]:
        raise RuntimeError("Input enriched simulation changed")
    tmp=case/"VERIFIED_COPY.sim"
    env={**os.environ,**day_chain.LIC,"FLAP_POST_DIR":str(case),"FLAP_POST_TIME":str(entry["time_s"]),
        "FLAP_POST_ROWS":str(entry["history_samples"]),"FLAP_POST_OUTPUT":str(tmp)}
    args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(case/"verify_profile"),
          "-batch",str(D/"VerifyFlapArchive.java"),str(sim)]
    with (case/"star_verify.log").open("w",encoding="utf-8") as log:
        p=subprocess.run(args,cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    receipt=case/"VERIFY.json"
    if p.returncode or not receipt.is_file() or not tmp.is_file():
        raise RuntimeError("Verification did not finish for "+name)
    digest=sha(tmp)
    os.replace(tmp,sim)
    if sha(sim)!=digest:
        raise RuntimeError("Verified archive hash mismatch")
    entry.update(reopen_verification=read(receipt),output_sha256=digest)
    (case/"PROVENANCE.json").write_text(json.dumps(entry,indent=2))
    manifest.write_text(json.dumps(entries,indent=2))
    print("VERIFIED",name,flush=True)


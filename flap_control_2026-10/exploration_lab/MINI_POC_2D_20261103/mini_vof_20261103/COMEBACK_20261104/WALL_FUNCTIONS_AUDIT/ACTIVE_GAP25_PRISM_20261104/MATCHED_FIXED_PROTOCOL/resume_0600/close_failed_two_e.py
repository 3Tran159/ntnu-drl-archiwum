from pathlib import Path
import json
import os
import subprocess
import sys

here=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(here))
from run_day import CLI, OWNER, PORT, READ, query

state=json.loads((here/"DAY_STATUS.json").read_text())
out=Path(state["output"])
if state["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E" or state.get("server_pid")!=37088:
    raise RuntimeError("Unexpected Mini state")
if query(OWNER)!=[39184]:
    raise RuntimeError("Dedicated Mini listener identity changed")
if not any(x["ProcessId"]==39184 and "21.04.009-R8" in (x.get("ExecutablePath") or "") for x in query(READ)):
    raise RuntimeError("Dedicated Mini process identity changed")
if "Host ID 0 Rank 0 on THINKPAD-LUCJAN with process ID 39184" not in (out/"server.log").read_text():
    raise RuntimeError("Listener not recorded by this Mini launch")
with (out/"close_owned_only.log").open("x",encoding="utf8") as log:
    subprocess.run([CLI,"-host","127.0.0.1","-port",str(PORT),"-nbuserdir",str(out/"close_owned_profile"),
                    "-batch",str(here/"CloseComeback.java")],cwd=out,
                    env={**os.environ,"MINI_CASE_DIR":str(out)},stdout=log,stderr=subprocess.STDOUT,
                    timeout=65,creationflags=subprocess.CREATE_NO_WINDOW,check=True)



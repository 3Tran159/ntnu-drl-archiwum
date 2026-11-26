from pathlib import Path
import json,shutil
H=Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102")
s=json.loads((H/"NIGHT_QUEUE_STATE.json").read_text(encoding="utf-8"))
cfg=json.loads((H/"NIGHT_QUEUE.json").read_text(encoding="utf-8"))
pending=[j["id"] for j in cfg["jobs"] if j["id"] not in s["jobs"] and not j.get("disabled")]
print(json.dumps({"active":s.get("active"),"failure_hold":s.get("failure_hold"),"controller_pid":s.get("controller_pid"),
"pending":pending,"accept_new_jobs":cfg.get("accept_new_jobs"),
"disk_free_GiB":round(shutil.disk_usage(H).free/1024**3,2)},indent=2))

from pathlib import Path
import json
import shutil
import sys
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
from run_day import sha
pair=D/"VOF_MESH/PAIR.json"
meta=json.loads(pair.read_text())
for key, row in meta.items():
    src=Path(row["path"])
    dest=D.parent/"WALL_FUNCTIONS_AUDIT"/"MATCHED_CALM_VOF_NIGHT_20261104"/key/"mesh_3d.msh"
    dest.parent.mkdir(parents=True,exist_ok=False)
    shutil.copy2(src,dest)
    if sha(src)!=row["sha256"] or sha(dest)!=row["sha256"]:
        raise RuntimeError("Mesh staging checksum mismatch")
    row["path"]=str(dest)
    (dest.parent/"AUDIT.json").write_text(json.dumps(row,indent=2))
t=pair.with_suffix(".tmp")
t.write_text(json.dumps(meta,indent=2))
t.replace(pair)


from pathlib import Path
import json,os
from run import H,read,sha
manifest=H/"MANIFEST.json"
entries=read(manifest)
name="03_Sharp_Sealed_PlusMinus5"
entry=entries[name]
old=Path(entry["output"])
case=H/name/"native_playback"
src=case/"WITH_PLAYBACK.sim"
dest=H/(name+"_PLAYBACK.sim")
v=read(case/"PLAYBACK_VERIFIED.json")
if sha(old)!=entry["output_sha256"] or not src.is_file() or dest.exists() or v["frames"]!=41 or v["solver_steps"]!=0:
    raise RuntimeError("Playback alternate output preflight failed")
hash=sha(src)
os.rename(src,dest)
if sha(dest)!=hash:
    raise RuntimeError("Playback alternate output checksum mismatch")
entry.update(native_playback=v,output=str(dest),output_sha256=hash,previous_scenes_only_copy=str(old))
manifest.write_text(json.dumps(entries,indent=2))
(H/name/"PROVENANCE.json").write_text(json.dumps(entry,indent=2))
print(dest,flush=True)

from pathlib import Path
import hashlib
import json
import shutil
import time

from plot_results import plot

WORK=Path(__file__).resolve().parent
ARCHIVE=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104\MATCHED_PROTOCOL_DT025")
STATE=WORK/"DT025_RESULT.json"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    deadline=time.monotonic()+4*3600
    while time.monotonic()<deadline:
        result=json.loads(STATE.read_text(encoding="utf8"))
        if result["status"]!="RUNNING":
            break
        if not (WORK.parents[2]/"CONTROLLER.lock").exists():
            raise RuntimeError("Controller ended before writing a terminal state")
        time.sleep(30)
    else:
        raise RuntimeError("Report wait time exceeded")

    plot()
    ARCHIVE.mkdir(exist_ok=False)
    manifest={}
    for name in ("SHARP_SEALED","GAP"):
        if name not in result:
            continue
        row=result[name]
        checkpoint=Path(row["checkpoint"])
        files=[checkpoint,*(checkpoint.parent/f for f in (
            "FIXED_PROTOCOL.json","fixed_history.csv","fixed_windows.csv","single_phase.csv",
            "residual_per_step.csv","FIXED_STABLE.sim","SOLVE_STATUS.json","job.json"))]
        case=ARCHIVE/name
        case.mkdir()
        for file in files:
            if not file.exists():
                continue
            output=case/file.name
            original=digest(file)
            if file==checkpoint and original!=row["checkpoint_sha256"]:
                raise RuntimeError(f"Unexpected checkpoint hash for {name}")
            shutil.copy2(file,output)
            if digest(output)!=original:
                raise RuntimeError(f"Archive copy failed for {output}")
            manifest[str(output.relative_to(ARCHIVE))]=original
    for file in (STATE,WORK/"full_histories_EN.png",WORK/"CL_CD_vs_deflection_EN.png"):
        if file.exists():
            output=ARCHIVE/file.name
            shutil.copy2(file,output)
            if digest(output)!=digest(file):
                raise RuntimeError(f"Archive copy failed for {output}")
            manifest[file.name]=digest(output)
    (ARCHIVE/"SHA256.json").write_text(json.dumps(manifest,indent=2),encoding="utf8")


if __name__=="__main__":
    main()


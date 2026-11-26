from pathlib import Path

d=Path(__file__).resolve().parent
s=(d/"run.py").read_text(encoding="utf8")
s=s.replace('output=D/"RESULT.json"','output=D/"RETRY_RESULT.json"')
s=s.replace('    if output.exists() or STOP.exists() or prev["status"]!="HOLD" or status["solver_state"]!="STOPPED":',
'''    attempt=json.loads((D/"RESULT.json").read_text())
    stop_text="Independent queue/process set changed"
    if (output.exists() or not STOP.exists() or STOP.read_text().strip()!=stop_text
        or attempt.get("W06",{}).get("stop")!=stop_text or attempt.get("samples")!=0
        or prev["status"]!="HOLD" or status["solver_state"]!="STOPPED"
        or status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600"):
'''.rstrip())
s=s.replace('    source=Path(receipt["path"])','    saved=Path(receipt["path"])')
s=s.replace('or source.parent!=prefix or source.stat().st_size!=receipt["bytes"]\n        or sha(source)!=sha(archive)):', '''or saved.parent!=prefix or saved.stat().st_size!=receipt["bytes"]
        or sha(saved)!=attempt["checkpoint_sha256"]
        or sha(archive)!=attempt["checkpoint_sha256_input"]):''')
s=s.replace('    mesh=json.loads', '    source=archive\n    mesh=json.loads')
s=s.replace('        coex.save(output,dict(status="RUNNING"', '''        archived_stop=D/"STOP_FOREIGN_PROCESS_1504.txt"
        if archived_stop.exists() or STOP.read_text().strip()!=stop_text:
            raise RuntimeError("Unexpected Mini stop marker")
        STOP.rename(archived_stop)
        coex.save(output,dict(status="RUNNING"''')
(d/"retry.py").write_text(s,encoding="utf8")


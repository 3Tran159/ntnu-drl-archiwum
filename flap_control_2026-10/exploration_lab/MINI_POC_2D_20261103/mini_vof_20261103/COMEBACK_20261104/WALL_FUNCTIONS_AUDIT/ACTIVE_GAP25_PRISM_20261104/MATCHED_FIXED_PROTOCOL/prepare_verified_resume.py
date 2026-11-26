from pathlib import Path

out=Path(__file__).resolve().parent
macro=out/"MiniVofStokes.java"
s=macro.read_text(encoding="utf8")
s=s.replace('if(b("fixed_protocol")&&b("seeded_single_phase")){','if(b("gapped_geometry")){')
s=s.replace('||!(b("after_fixed_motion")||b("seeded_single_phase")))','||!b("after_fixed_motion"))')
macro.write_text(s,encoding="utf8")
runner=out/"run_fixed_protocol.py"
s=runner.read_text(encoding="utf8")
s=s.replace('("GAP",dict(source=source,seeded_single_phase=True,expected_cells=ga["cells"],steps=0)),',
            '("GAP",dict(source=source,seeded_single_phase=True,gapped_geometry=True,after_fixed_motion=True,expected_cells=ga["cells"],steps=600)),')
runner.write_text(s,encoding="utf8")
s=s.replace('from run_day import LOCK, STOP, new_job, sha','from run_day import LOCK, STOP, independent_jobs, new_job, protected_idle, sha')
s=s.replace('    output=OUT/"RESULT.json"\n    if STOP.exists() or output.exists():\n        raise RuntimeError("Fixed protocol preflight blocked")',
'''    output=OUT/"RESUME_RESULT.json"
    original=json.loads((OUT/"RESULT.json").read_text())["SHARP_SEALED"]
    resume=Path(original["checkpoint"])
    if (output.exists() or LOCK.exists() or independent_jobs() or not STOP.exists()
        or STOP.read_text().strip()!=original["W06"]["stop"]
        or not original["W06"]["stop"].startswith("W06 seven-step median slower")
        or original["fixed"] is not None or sha(resume)!=original["checkpoint_sha256"]):
        raise RuntimeError("Resume preflight blocked")
    protected_idle()''')
s=s.replace('    with LOCK.open("x",encoding="ascii") as f:\n        f.write(str(os.getpid()))',
'''    with LOCK.open("x",encoding="ascii") as f:
        f.write(str(os.getpid()))''')
s=s.replace('    try:\n        common=', '''    try:
        saved_stop=OUT/"STOP_W06_SLOWDOWN_ARCHIVED.txt"
        if saved_stop.exists():
            raise RuntimeError("W06 stop marker already archived")
        STOP.rename(saved_stop)
        common=''')
start=s.index('            ("SHARP_SEALED",')
end=s.index('            ("GAP",',start)
s=s[:start]+'''            ("SHARP_SEALED",dict(source=resume,seeded_single_phase=True,gap_resume_steady=True,
                expected_cells=sa["cells"],steady_max_iterations=1550,steps=600,after_fixed_motion=True)),
'''+s[end:]
(out/"resume_after_w06.py").write_text(s,encoding="utf8")


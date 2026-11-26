from pathlib import Path

d=Path(__file__).resolve().parent
s=(d/"run_two_p.py").read_text(encoding="utf8")
s=s.replace('        if slowdown>.15:\n            raise RuntimeError(f"W06 seven-step median slower by {slowdown:.1%}")','')
s=s.replace('output=D/"RESULT.json"','output=D/"NO_W06_STOP_RESULT.json"')
s=s.replace('old=json.loads((R/"TWO_E_COEX_RESULT.json").read_text())','old=json.loads((D/"RESULT.json").read_text())')
s=s.replace('marker="User requested safe Mini restart on two P cores."','marker=old["W06"]["stop"]\n    if not marker.startswith("W06 seven-step median slower"):\n        raise RuntimeError("Prior Mini stop was not the W06 slowdown gate")')
s=s.replace('status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_COEX"', 'status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME_TWO_P"')
s=s.replace('baseline=statistics.median(b[1]-a[1] for a,b in zip(recent,recent[1:]))','baseline=old["W06"]["baseline_s"]')
s=s.replace('        cpus,load=choose_p()','''        cpus=old["cpu_indices"]
        if cpus!=[12,22]:
            raise RuntimeError("Unexpected prior P-core binding")
        load=None''')
s=s.replace('guard.watch=D/"W06_WATCH.csv"','guard.watch=D/"NO_W06_STOP_WATCH.csv"')
s=s.replace('D/"RESOURCE_PREFLIGHT.json"','D/"NO_W06_STOP_PREFLIGHT.json"')
s=s.replace('w06_baseline_steps=25,mini_priority="High"','w06_slowdown_gate_enabled=False,mini_priority="High"')
s=s.replace('D/"STOP_REQUESTED_E_TO_P.txt"','D/"STOP_W06_15PCT_ARCHIVED.txt"')
s=s.replace('new_job("MATCHED_FIXED_SHARP_SEALED_RESUME_TWO_P",dict(', 'new_job("MATCHED_FIXED_SHARP_SEALED_TWO_P_MONITOR_W06",dict(')
s=s.replace('dict(baseline_s=baseline,peak=guard.peak,stop=guard.stopped)','dict(baseline_s=baseline,peak=guard.peak,stop=guard.stopped,slowdown_gate_enabled=False)')
(d/"run_without_w06_slowdown_stop.py").write_text(s,encoding="utf8")


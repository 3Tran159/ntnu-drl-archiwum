from pathlib import Path

out=Path(__file__).resolve().parent
p=out/"MiniVofStokes.java"
s=p.read_text(encoding="utf8")
old='''       ||pc.getModelManager().hasModel(SteadyModel.class)==null)
     throw new IllegalStateException("Unexpected saved steady checkpoint");
    if(!b("gap_resume_steady")){'''
new='''       ||(b("fixed_from_unsteady")?pc.getModelManager().hasModel(ImplicitUnsteadyModel.class)==null:
          pc.getModelManager().hasModel(SteadyModel.class)==null))
     throw new IllegalStateException("Unexpected saved fixed checkpoint");
    if(!b("gap_resume_steady")&&!b("fixed_from_unsteady")){'''
assert s.count(old)==1
p.write_text(s.replace(old,new),encoding="utf8")

s=(out/"resume_after_w06.py").read_text(encoding="utf8")
start=s.index('    output=')
end=s.index('    if independent_jobs()',start)
s=s[:start]+'''    output=OUT/"DT025_RESULT.json"
    previous=json.loads((OUT/"RESUME_RESULT.json").read_text())["SHARP_SEALED"]
    failed=Path(previous["checkpoint"])
    resume=failed.parent/"FIXED_START.sim"
    receipt=json.loads((OUT/"DT025_INPUT.json").read_text())
    if (output.exists() or LOCK.exists() or not STOP.exists()
        or STOP.read_text().strip()!=receipt["owned_stop"]
        or previous["status"]!="HOLD_FIXED_CFL" or sha(failed)!=previous["checkpoint_sha256"]
        or sha(resume)!=receipt["sharp_fixed_start_sha256"]):
        raise RuntimeError("Matched 0.25 ms preflight blocked")
'''+s[end:]
s=s.replace('saved_stop=OUT/"STOP_W06_SLOWDOWN_ARCHIVED.txt"','saved_stop=OUT/"STOP_DT0333_ARCHIVED.txt"')
s=s.replace('"MATCHED_FIXED_SHARP_SEALED_RETRY_"','"MATCHED_FIXED_SHARP_SEALED_DT025_"')
s=s.replace('dt=.2/600','dt=.00025').replace('gap_resume_steady=True','fixed_from_unsteady=True').replace('steps=600','steps=800')
(out/"run_fixed_dt025.py").write_text(s,encoding="utf8")

p=out/"plot_results.py"
s=p.read_text(encoding="utf8")
s=s.replace('            coverage="" if len(angle)==600 else f" | partial, {len(angle)} of 600 steps"',
'''            step=active["time_s"][1]-active["time_s"][0] if len(angle)>1 else None
            expected=round(.2/step) if step else None
            coverage="" if len(angle)==expected else f" | partial, {len(angle)} steps"''')
s=s.replace('Lift and drag during flap motion | 18 m/s, time step 0.333 ms','Lift and drag during flap motion | 18 m/s')
p.write_text(s,encoding="utf8")


from pathlib import Path

p=Path(__file__).with_name("night_flap.py")
s=p.read_text()
idx=s.index("\ndef run_cycle(")
s=s[:idx]+'''

def await_resources(state,stage):
    last_error=None
    while not STOP.exists() and time.time()<END-420:
        try:
            NightGuard(None,1.777749).preflight()
            return True
        except RuntimeError as exc:
            last_error=str(exc)
            soft=("assigned Mini CPUs" in last_error or "CPU above 85 percent" in last_error)
            if not soft:
                raise
            state.update(status="WAITING_RESOURCES",active=stage,resource_wait=last_error)
            coex.save(STATUS,state)
            time.sleep(60)
    if last_error:
        state["resource_wait"]=last_error
    return False
'''+s[idx:]
old='''            if any((OUT/name).exists() for name in (PLAN[1],PLAN[2],"CALM_VOF_FIXED_SEALED","CALM_VOF_FIXED_GAP","SURROGATE_PILOT")):
                raise RuntimeError("Resource restart would duplicate an existing result")
            archive(STATUS,OUT/"RESOURCE_HOLD_BEFORE_RESUME.json")
            state["runs"][PLAN[0]]=complete
            state["resource_policy"]="Fixed foreign affinity protected. All-core foreign ranks allowed with measured host CPU headroom."
            cases=cases[1:]'''
new='''            keep={PLAN[0]:complete}
            for name in PLAN[1:3]:
                previous_result=saved["runs"].get(name,{})
                if (OUT/name).exists():
                    if not previous_result.get("checkpoint_sha256") or sha(OUT/name/"FINAL.sim")!=previous_result["checkpoint_sha256"]:
                        raise RuntimeError("Existing cycle result failed restart verification: "+name)
                    keep[name]=previous_result
            if any((OUT/name).exists() for name in ("CALM_VOF_FIXED_SEALED","CALM_VOF_FIXED_GAP","SURROGATE_PILOT")):
                raise RuntimeError("Resource restart would duplicate an existing VOF result")
            snapshot=OUT/("RESOURCE_HOLD_BEFORE_RESUME_"+dt.datetime.now().strftime("%H%M%S")+".json")
            archive(STATUS,snapshot)
            state["runs"].update(keep)
            state["resource_policy"]="Wait for measured host CPU headroom; protect fixed foreign affinity."
            cases=tuple(case for case in cases if case[0] not in keep)'''
assert s.count(old)==1
s=s.replace(old,new,1)
old='''            stage=case[0]
            state.update(status="RUNNING",active=stage)'''
new='''            stage=case[0]
            if not await_resources(state,stage):
                state["runs"][stage]={"status":"HOLD_RESOURCE_OR_DEADLINE"}
                break
            state.pop("resource_wait",None)
            state.update(status="RUNNING",active=stage)'''
assert s.count(old)==1
s=s.replace(old,new,1)
p.write_text(s)
p=p.with_name("calm_pair_ready.py")
s=p.read_text().replace("archive, coex, history", "archive, await_resources, coex, history")
s=s.replace('        mesh=pair[key]', '''        if not await_resources(state,stage):
            state["runs"][stage]={"status":"HOLD_RESOURCE_OR_DEADLINE"}
            continue
        state.pop("resource_wait",None)
        mesh=pair[key]''')
s=s.replace('    state["active"]=stage\n    coex.save(HERE/"STATUS.json",state)', '''    if not await_resources(state,stage):
        state["runs"][stage]={"status":"HOLD_RESOURCE_OR_DEADLINE"}
        return
    state.pop("resource_wait",None)
    state["active"]=stage
    coex.save(HERE/"STATUS.json",state)''')
p.write_text(s)


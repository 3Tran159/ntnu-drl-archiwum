from pathlib import Path

p=Path(__file__).with_name("night_flap.py")
src=p.read_text()
src=src.replace("import csv","import argparse\nimport csv",1)
src=src.replace("from run_active_resume_1064 import GuardResume, coex","from run_active_resume_1064 import GuardResume, coex, topology",1)
src=src.replace('        if any(value & MASK for value in values):\n            raise RuntimeError("An independent STAR compute rank overlaps the assigned Mini CPUs")',
'''        host_mask = sum(1 << item["logical_cpu"] for item in topology() if item["group"]==0)
        if any(value & MASK and value != host_mask for value in values):
            raise RuntimeError("An independent STAR compute rank overlaps the assigned Mini CPUs")
        if host_mask in values:
            utilization=query("(Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation -Filter \\"Name='_Total'\\").PercentProcessorTime | ConvertTo-Json -Compress")
            if not utilization or utilization[0] > 85:
                raise RuntimeError("Unpinned independent STAR ranks and host CPU above 85 percent")''')
src=src.replace('def main():\n    previous',
'''def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--resume-resource-hold",action="store_true")
    resume=parser.parse_args().resume_resource_hold
    previous''')
src=src.replace('    try:\n        OUT.mkdir()\n        for case in cases:',
'''    try:
        if resume:
            saved=read(STATUS)
            complete=saved["runs"].get(PLAN[0],{})
            if saved["status"]!="REVIEW" or not complete.get("cycle_complete") or sha(OUT/PLAN[0]/"FINAL.sim")!=complete["checkpoint_sha256"]:
                raise RuntimeError("Resource restart requires verified completed gap +/-2")
            if any((OUT/name).exists() for name in (PLAN[1],PLAN[2],"CALM_VOF_FIXED_SEALED","CALM_VOF_FIXED_GAP","SURROGATE_PILOT")):
                raise RuntimeError("Resource restart would duplicate an existing result")
            archive(STATUS,OUT/"RESOURCE_HOLD_BEFORE_RESUME.json")
            state["runs"][PLAN[0]]=complete
            state["resource_policy"]="Fixed foreign affinity protected. All-core foreign ranks allowed with measured host CPU headroom."
            cases=cases[1:]
        else:
            OUT.mkdir()
        for case in cases:''')
p.write_text(src)


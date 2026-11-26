from pathlib import Path
import csv
import ctypes
import json
import os
import shutil
import subprocess
import sys

D=Path(__file__).resolve().parent
P=D.parent
T=Path(r"T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104")
H=Path(r"H:/NTNU_RESEARCH_ARCHIVE/Active Flaps/URANS_Cycles_STAR2606_20261105")
sys.path.insert(0,str(P/"FLAP_EXTREMA_VOF5_20261105"))
from run_local import filtered_query, sha
sys.path.insert(0,str(P.parents[1]))
import day_chain
from run_day import CLI
from run_active_resume_1064 import topology

cases=[
 ("01_Sharp_Sealed_PlusMinus2","SHARP_SEALED_CYCLE_RESUME_1P064S","single_phase_combined.csv",1.05,False),
 ("02_Gap25_PlusMinus2","NIGHT_FLAP_20261104/GAP_PLUS_MINUS_2","cycle_full_available.csv",1.0,False),
 ("03_Sharp_Sealed_PlusMinus5","NIGHT_FLAP_20261104/SHARP_SEALED_PLUS_MINUS_5","cycle_full_available.csv",1.05,False),
 ("04_Gap25_PlusMinus5_HOLD","NIGHT_FLAP_20261104/GAP_PLUS_MINUS_5_DT020_RESUME","cycle_full_available.csv",1.0,True),
]

def setup_cpu():
    topo=topology()
    all_mask=sum(1<<item["logical_cpu"] for item in topo if item["group"]==0)
    masks=filtered_query("ConvertTo-Json -InputObject @(Get-Process -Name 'star-ccm+' -ErrorAction SilentlyContinue | ForEach-Object {$_.ProcessorAffinity.ToInt64()}) -Compress")
    busy=0
    for mask in masks:
        if mask!=all_mask:
            busy|=mask
    level=min(item["efficiency_class"] for item in topo)
    cpu=next(item["logical_cpu"] for item in topo if item["group"]==0 and item["efficiency_class"]==level and not busy&(1<<item["logical_cpu"]))
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetProcessAffinityMask.argtypes=(ctypes.c_void_p,ctypes.c_size_t)
    if not k.SetProcessAffinityMask(k.GetCurrentProcess(),1<<cpu):
        raise OSError(ctypes.get_last_error(),"Could not pin archival viewer")
    return cpu

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def render(item,cpu):
    name,folder,history,origin,hold=item
    source=T/folder
    meta=read(source/"RESULT.json")
    target=H/name
    target.mkdir(exist_ok=True)
    sim=H/(name+".sim")
    receipt=target/"RECEIPT.json"
    if sim.is_file() and receipt.is_file():
        previous=read(target/"PROVENANCE.json")
        if sha(sim)!=previous["output_sha256"]:
            raise RuntimeError("Output hash changed")
        return previous
    if sim.exists():
        raise RuntimeError("Existing output without receipt")
    if sha(source/"FINAL.sim")!=meta["checkpoint_sha256"]:
        raise RuntimeError("Source checkpoint mismatch")
    checkpoint=target/"SOURCE_COPY.sim"
    if not checkpoint.exists():
        shutil.copy2(source/"FINAL.sim",checkpoint)
    if sha(checkpoint)!=meta["checkpoint_sha256"]:
        raise RuntimeError("Copied checkpoint checksum mismatch")
    with (source/history).open(newline="") as f:
        rows=list(csv.DictReader(f))
    if abs(float(rows[-1]["time_s"])-float(meta["state"]["time_s"]))>1e-9:
        raise RuntimeError("History does not match checkpoint")
    with (target/"trajectory.csv").open("w",newline="") as f:
        write=csv.writer(f);write.writerow(("elapsed_s","physical_time_s","command_deg","measured_deg","CL","CD",
             "Mh_Nm_per_m","flap_pabs_kPa","vapor_pressure_kPa","max_CFL"))
        for row in rows:
            t=float(row["time_s"])
            write.writerow((t-origin,t,row["delta_command_deg"],row["delta_measured_deg"],row["CL"],row["CD"],
                     row["Mh_Nm"],float(row["pflap_min_Pa"])/1000,2.3392147668,row["max_CFL"]))
    env={**os.environ,**day_chain.LIC,"FLAP_POST_DIR":str(target),"FLAP_POST_TIME":str(meta["state"]["time_s"]),
         "FLAP_POST_ROWS":str(len(rows)),"FLAP_POST_OUTPUT":str(sim)}
    args=[CLI,"-power","-np","1","-cpubind","off","-printpids","-nbuserdir",str(target/"profile"),
          "-batch",str(D/"ArchiveFlapScenes.java"),str(checkpoint)]
    with (target/"star_post.log").open("w",encoding="utf-8") as log:
        cp=subprocess.run(args,cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,
                          creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    if cp.returncode or not sim.is_file() or not receipt.is_file():
        raise RuntimeError(f"STAR post-processing did not finish for {name}; log: {target/'star_post.log'}")
    result=read(receipt)
    result.update(source=str(source/"FINAL.sim"),source_sha256=meta["checkpoint_sha256"],
                  output=str(sim),output_sha256=sha(sim),angle_range_deg=meta["angle_range_deg"],
                  status=meta["status"],complete_cycle=not hold,post_cpu=cpu,source_history=str(source/history))
    (target/"PROVENANCE.json").write_text(json.dumps(result,indent=2))
    checkpoint.unlink()
    return result

if __name__=="__main__":
    H.mkdir(parents=True,exist_ok=True)
    cpu=setup_cpu()
    completed={}
    for item in cases:
        print("START",item[0],"CPU",cpu,flush=True)
        completed[item[0]]=render(item,cpu)
        (H/"MANIFEST.json").write_text(json.dumps(completed,indent=2))
        print("SAVED",item[0],flush=True)


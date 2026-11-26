import argparse
import csv
import json
import math
from pathlib import Path
import sys
import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, new_job

def run(stage,settings):
    if STOP.exists():
        raise RuntimeError("STOP present, review prior protection")
    with LOCK.open("x",encoding="ascii") as f:
        import os
        f.write(str(os.getpid()))
    coex.BASELINE_FILE=HERE/(stage+"_W06_BASELINE.json")
    coex.WATCH=HERE/(stage+"_W06_WATCH.csv")
    report=HERE/(stage+"_SPRINT.json")
    try:
        with coex.WATCH.open("x",encoding="ascii",newline="") as f:
            csv.writer(f).writerow(("time","phase","w06_step","w06_physical_s","w06_rolling_median_s","slowdown_fraction","mini_steps"))
        m=coex.W06Protection()
        m.make_baseline()
        result=new_job(stage,settings,protection=m)
        coex.save(report,{"result":result,"W06_baseline_s":m.baseline,"W06_peak_slowdown":m.peak,"W06_stop":m.stopped})
        return result
    except Exception as err:
        coex.save(report,{"error":str(err),"status":"HOLD"})
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    ramp=2*.4545374193129603
    result=run("SPRINT_A_RAMP40",dict(fresh=True,stokes=True,foil=False,amplitude=.25,old_amplitude=0,
        ramp_s=ramp,expected_time=0,steps=40,limit_seconds=720))
    print(json.dumps(result,indent=2))


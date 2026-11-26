"""One corrected ramp trial after the running single-phase stage."""
import time
from pathlib import Path
import numpy as np
from run_day import HERE, LOCK, STOP
from run_sprint import run
from sprint_followup import A, RAMP, STATE, basic, continue_after_ab, read, report
import stokes_coexistence as coex

def localize(outcome):
    if not outcome or outcome.get("status")!="HOLD_TURBULENCE_LIMIT":
        return
    d=Path(outcome["checkpoint"]).parent
    p=np.loadtxt(d/"field_end.csv",delimiter=",",skiprows=1)
    ids=np.where((p[:,8]>=99999)|(p[:,7]<=1.0001e-10)|(p[:,6]<=1.0001e-10))[0]
    out=[]
    for j in ids:
        row=p[j]
        column=p[(abs(p[:,-3]-row[-3])<1e-8)&(abs(p[:,-1]-row[-1])<1e-8)]
        lower=column[column[:,-2]<row[-2]-1e-8]
        upper=column[column[:,-2]>row[-2]+1e-8]
        below=lower[np.argmax(lower[:,-2])] if len(lower) else None
        above=upper[np.argmin(upper[:,-2])] if len(upper) else None
        gradient=None
        if below is not None and above is not None:
            gradient=list((above[3:6]-below[3:6])/(above[-2]-below[-2]))
        out.append(dict(xyz_m=list(row[-3:]),alpha_water=row[0],pABS_Pa=row[1],k_m2_s2=row[6],
                        omega_s_inv=row[7],mut_mu=row[8],d_velocity_d_y_s_inv=gradient))
    coex.save(d/"SST_LOCALIZATION.json",{"cells_triggering_gate":len(out),"cells":out})

def main():
    waiting=HERE/"SPRINT_A_RETRY_WAIT.json"
    if waiting.exists():
        raise RuntimeError("Retry already registered")
    coex.save(waiting,{"operation":"WAIT_FOR_B_RELEASE","night_authorized":False})
    deadline=time.monotonic()+2300
    while time.monotonic()<deadline and not STOP.exists():
        if not LOCK.exists() and read(STATE).get("operation")=="HOLD":
            break
        time.sleep(5)
    if LOCK.exists() or STOP.exists() or read(STATE).get("operation")!="HOLD":
        coex.save(waiting,{"operation":"HOLD","reason":"Resource ownership/STOP/time"})
        return
    old=read(A)["result"]
    if old["status"]!="HOLD_NONFINITE_interfaceCFL" or old["samples"]!=1:
        raise RuntimeError("Unexpected prior failure; refuse unqualified retry")
    state=read(STATE)
    state.update(operation="A_RAMP40_CORRECTED_CFL",A="RUNNING")
    report(state)
    try:
        result=run("SPRINT_A_RAMP40_CFL_SAFE",dict(fresh=True,stokes=True,foil=False,
            expected_time=0,amplitude=.25,old_amplitude=0,ramp_s=RAMP,ramp_origin_s=0,
            steps=40,limit_seconds=720))
        state["A_corrected_smoke"]=result
        localize(result)
        state["A"]="SMOKE_PASS" if basic(result,40) else "HOLD"
        report(state)
        if basic(result,40):
            continue_after_ab(state,result)
            localize(state.get("A_result"))
        else:
            state["operation"]="HOLD"
            report(state)
    except Exception as err:
        state.update(operation="HOLD",A="HOLD",A_retry_error=str(err))
        report(state)
    finally:
        coex.save(waiting,{"operation":"FINISHED","night_authorized":False})

if __name__=="__main__":
    main()


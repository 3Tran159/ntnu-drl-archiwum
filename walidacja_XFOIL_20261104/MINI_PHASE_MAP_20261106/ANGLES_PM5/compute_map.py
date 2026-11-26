"""Compute a viscous XFOIL polar grid for the NTNU sharp sealed section."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent))
from make_phase_map import EXE, RE, section, shape

ANGLES = np.linspace(-5, 5, 21)
TRIP = .01
PANELS = 240


def polar(work, name, direction, increment):
    path = work / f"{name}.txt"
    if not path.exists():
        alphas = direction * np.arange(0, 5.001, increment)
        commands = ["PLOP","G","","LOAD foil.dat","PPAR","N",str(PANELS),"","","PANE",
                    "OPER",f"VISC {RE}","ITER 300","VPAR",f"XTR {TRIP} {TRIP}","","PACC",path.name,"",
                    *[f"ALFA {a:.2f}" for a in alphas],"PACC","","QUIT",""]
        script = "\n".join(commands)
        (work / f"{name}.inp").write_text(script, encoding="ascii")
        with (work / f"{name}.log").open("wb") as log:
            try:
                subprocess.run([str(EXE)], input=script.encode(), cwd=work, stdout=log,
                               stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW, timeout=8)
            except subprocess.TimeoutExpired:
                log.write(b"\nTime limit: retaining only converged rows already written by XFOIL.\n")
    if not path.exists():
        return {}
    data = {}
    for line in path.read_text(encoding="ascii").splitlines():
        try:
            row = list(map(float, line.split()))
        except ValueError:
            continue
        if len(row) == 7 and np.isfinite(row).all() and row[2] > 0:
            data[row[0]] = row[1:]
    return data


def consistent_trip(row):
    return max(row[4:6]) <= TRIP + .002


def main():
    points, mesh_path = section()
    grid = []
    for delta in ANGLES:
        work = OUT / ("flap_" + f"{delta:+.1f}".replace("+","p").replace("-","m").replace(".","p"))
        work.mkdir(exist_ok=True)
        np.savetxt(work/"foil.dat", shape(points,delta), fmt="%.10f", header="NTNU sharp sealed foil", comments="")
        values = {}
        for direction, side in ((1,"positive"),(-1,"negative")):
            rows = polar(work, side, direction, .5)
            expected = ANGLES[ANGLES*direction >= 0]
            if any(a not in rows or not consistent_trip(rows[a]) for a in expected):
                retry = polar(work, side+"_refined", direction, .25)
                for alpha in expected:
                    if (alpha not in rows or not consistent_trip(rows[alpha])) and alpha in retry and consistent_trip(retry[alpha]):
                        rows[alpha] = retry[alpha]
            values.update({a: r for a,r in rows.items() if a in ANGLES and a not in values})
        for alpha in ANGLES:
            row=values.get(alpha)
            status="NO_CONVERGENCE" if row is None else "CONVERGED" if consistent_trip(row) else "TRIP_MISMATCH"
            grid.append([float(alpha),float(delta),*(row or [None]*6),status])
        print(f"flap {delta:+.1f}: {len(values)}/{len(ANGLES)}", flush=True)
    with (OUT/"XFOIL_CL_CD_ANGLES_PM5.csv").open("w", newline="",encoding="utf8") as file:
        writer=csv.writer(file)
        writer.writerow(["foil_angle_deg","flap_deflection_deg","CL","CD","CD_pressure","CM_c4","transition_top_xc","transition_bottom_xc","status"])
        writer.writerows(grid)
    missing=[[row[0],row[1]] for row in grid if row[-1]!="CONVERGED"]
    data=[row for row in grid if row[-1]=="CONVERGED"]
    summary={"solver":"XFOIL 6.99 viscous","geometry_source":mesh_path,"reynolds":RE,"mach":0,"trip_x_over_c":TRIP,
             "panels":PANELS,"hinge_x_over_c":.8,"step_deg":.5,"angle_limits_deg":[-5,5],
             "signs":{"foil_angle":"positive angle of attack relative to inflow",
                      "flap_deflection":"positive trailing edge down"},
             "attempted":len(grid),"converged":len(data),"excluded_foil_flap_deg":missing,"trip_mismatch_count":sum(r[-1]=="TRIP_MISMATCH" for r in grid),
             "CL_range":[min(r[2] for r in data),max(r[2] for r in data)],
             "CD_range":[min(r[3] for r in data),max(r[3] for r in data)]}
    (OUT/"XFOIL_ANGLES_PM5_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__":
    main()

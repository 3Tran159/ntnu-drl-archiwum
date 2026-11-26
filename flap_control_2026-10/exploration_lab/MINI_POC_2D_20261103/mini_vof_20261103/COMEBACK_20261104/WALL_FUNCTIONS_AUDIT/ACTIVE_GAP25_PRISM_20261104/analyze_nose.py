from pathlib import Path
import csv
import json
import re
import numpy as np
from plot_gap import plt

D = Path(__file__).resolve().parent
status = json.loads((D/"NOSE_READBACK_RESULT.json").read_text())
run = Path(status["run_directory"])
meta = json.loads((run/"REOPEN.json").read_text())
q = .5*1000*meta["U_m_s"]**2
reference = meta["reference_pressure_Pa"]


def read(file):
    with (run/file).open() as f:
        reader = csv.reader(f)
        names = next(reader)
        values = np.array([[float(c) for c in r] for r in reader])
    print(file, names, values.shape)
    return names, values


def column(table, matcher):
    names, arr = table
    index, = (i for i,n in enumerate(names) if re.search(matcher,n,re.I))
    return arr[:,index]


def xy(table):
    return np.column_stack([column(table,r"^X \(m\)"), column(table,r"^Y \(m\)")])


def pressure(table):
    return column(table,r"^Absolute Pressure")


def cp(table):
    return (pressure(table)-reference)/q


cell = read("cells.csv")
main = read("main_wall.csv")
flap = read("flap_wall.csv")
coords = xy(cell)
wall_xy = xy(main)
speed = np.hypot(column(cell,r"Velocity.*(?:\[[Xi]\]|X component)"),
                 column(cell,r"Velocity.*(?:\[[Yj]\]|Y component)"))
quality = column(cell,r"Least Squares")
volume = column(cell,r"^Volume")
validity = column(cell,r"Face Validity")
yplus_main = column(main,r"Wall Y\+|Wall Yplus")
yplus_flap = column(flap,r"Wall Y\+|Wall Yplus")
p_wall = pressure(main)
p_cell = pressure(cell)
n = int(np.argmin(p_wall))
c = int(np.argmin(p_cell))
point = wall_xy[n]
neighbor = np.argsort(np.linalg.norm(wall_xy-point,axis=1))[:11]
near_cell = np.linalg.norm(coords-point,axis=1)<.008
narrow = (abs(coords[:,0]-point[0])<.002) & (coords[:,1]<point[1]) & (coords[:,1]>point[1]-.008)
gap_cell = np.hypot(coords[:,0]-.952,coords[:,1]-.02128173276777)<.043


def cell_row(i):
    return dict(xy_m=coords[i].tolist(), pABS_Pa=float(p_cell[i]), Cp=float(cp(cell)[i]),
                speed_m_s=float(speed[i]), quality=float(quality[i]), face_validity=float(validity[i]),
                cell_volume=float(volume[i]))


def wall_row(i):
    return dict(xy_m=wall_xy[i].tolist(), pABS_Pa=float(p_wall[i]), Cp=float(cp(main)[i]),
                yplus=float(yplus_main[i]))


def percentile(values):
    return np.percentile(values,[10,50,90]).tolist()


report = dict(reference=meta, global_cell_min=cell_row(c), main_wall_min=wall_row(n),
              closest_wall_faces=[wall_row(i) for i in neighbor],
              flap_wall_min_Pa=float(pressure(flap).min()), hinge_cells_min_Pa=float(p_cell[gap_cell].min()),
              main_yplus_p10_50_90=percentile(yplus_main), flap_yplus_p10_50_90=percentile(yplus_flap),
              near_nose_cells=int(near_cell.sum()), near_nose_speed_peak=cell_row(int(np.argmax(np.where(near_cell,speed,-1)))),
              nose_cross_wall_profile=[cell_row(i) for i in np.flatnonzero(narrow)[np.argsort(-coords[narrow,1])]],
              region_min_quality=float(quality.min()), reference_pressure_delta_max_Pa=float(np.max(abs(
              p_cell-column(cell,r"^Pressure(?: \(|$)")-reference))))
(D/"NOSE_DIAGNOSTICS.json").write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!="nose_cross_wall_profile"},indent=2))

fig, axes = plt.subplots(1,3,figsize=(14,4.7),layout="constrained")
for label,mask,color in (("Upper side",wall_xy[:,1]>=0,"#127a92"),("Lower side",wall_xy[:,1]<0,"#c56732")):
    select = np.flatnonzero(mask&(wall_xy[:,0]<.06))
    select = select[np.argsort(wall_xy[select,0])]
    axes[0].plot(wall_xy[select,0]*1000,cp(main)[select],"o-",ms=2.5,c=color,label=label)
axes[0].scatter(point[0]*1000,cp(main)[n],marker="x",s=55,c="#273544")
axes[0].set(xlabel="Streamwise position [mm]",ylabel="$C_p$",title="Wall pressure coefficient")
axes[0].legend(frameon=False)
axes[0].grid(alpha=.2)
roi=(coords[:,0]<.045)&(coords[:,0]>-.01)&(abs(coords[:,1])<.028)
wall_roi=(wall_xy[:,0]<.05)&(abs(wall_xy[:,1])<.035)
for ax,field,label,cmap in ((axes[1],cp(cell),"$C_p$","coolwarm"),
                           (axes[2],speed,"Speed [m/s]","viridis")):
    dots=ax.scatter(*(coords[roi].T*1000),c=field[roi],s=15,cmap=cmap)
    ax.scatter(*(wall_xy[wall_roi].T*1000),c="#394b58",s=4)
    ax.scatter(*(point*1000),marker="x",s=55,c="#db582e")
    ax.set(xlabel="Streamwise position [mm]",ylabel="Vertical position [mm]",aspect="equal",
           title="Cell-centre " + label)
    fig.colorbar(dots,ax=ax,label=label,shrink=.82)
fig.suptitle("NACA 66-012 MOD | Leading-edge checkpoint at 18 m/s, flap 0°\n"
             "Steady iteration 420 | flow still developing",fontweight="bold")
fig.savefig(D/"LEADING_EDGE_CP_SPEED_EN.png",dpi=190)



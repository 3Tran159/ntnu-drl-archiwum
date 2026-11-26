"""Quasi-steady two-actuator phase map using the actual sealed section and XFOIL."""
import csv
import json
import math
from pathlib import Path
import subprocess
import numpy as np

HERE = Path(__file__).resolve().parent
EXE = HERE.parent / "MIT_XFOIL_6.99/xfoil.exe"
MINI = Path(r"F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103\mini_vof_20261103\COMEBACK_20261104\RESUME_0422200_GPU_CHECK_20261105")
WAVE = MINI.parent / "runs/PHASE_MAP_WAVE_FIXED_20261106_105755"
STATE = json.loads((MINI/"WAVE_PHASE_MAP_STATUS.json").read_text(encoding="utf-8-sig"))
GATE = STATE["fixed_gate"]
PERIOD = GATE["period_s"]
OMEGA = 2*np.pi/PERIOD
START, END = GATE["window_s"]
RE = 21_300_000
C = 1.19
HINGE = np.array([.952,.02128173276777])
DELTAS = np.linspace(-1,1,9)
ALPHAS = np.arange(-1.5,1.501,.25)


def section():
    audit = MINI.parent/"SHARP_SEALED_NATIVE_20261105/GEOMETRY_AUDIT.json"
    mesh_path = json.loads(audit.read_text(encoding="utf-8-sig"))["source"]
    mesh = np.load(mesh_path)
    points=mesh["xy"]
    graph={}
    for a,b in np.concatenate((mesh["main"],mesh["flap"])):
        graph.setdefault(a,[]).append(b)
        graph.setdefault(b,[]).append(a)
    if any(len(adj)!=2 for adj in graph.values()):
        raise RuntimeError("Sealed section is not a single closed contour")
    first=max(graph,key=lambda i:points[i,0])
    order=[first]
    nxt=max(graph[first],key=lambda i:points[i,1])
    while nxt!=first and len(order)<=len(graph):
        order.append(nxt)
        nxt=next(i for i in graph[nxt] if i!=order[-2])
    if len(order)!=len(graph):
        raise RuntimeError("Incomplete foil contour")
    return points[order+[first]],mesh_path


def shape(points, delta):
    xy=points-HINGE
    q=np.clip(xy[:,0]/.035,0,1)
    blend=q**3*(10-15*q+6*q*q)
    a=np.radians(delta)*blend
    x=xy[:,0]*np.cos(a)+xy[:,1]*np.sin(a)
    y=-xy[:,0]*np.sin(a)+xy[:,1]*np.cos(a)
    return (np.column_stack((x,y))+HINGE)/C


def polar(points, delta):
    label=f"delta_{delta:+.2f}".replace("+","p").replace("-","m").replace(".","p")
    work=HERE/label
    work.mkdir(exist_ok=True)
    np.savetxt(work/"foil.dat",shape(points,delta),fmt="%.10f",header="NTNU sealed foil "+label,comments="")
    out=work/"polar.txt"
    if not out.exists():
        cmd=["PLOP","G","","LOAD foil.dat","PPAR","N","240","","","PANE","OPER",
             f"VISC {RE}","ITER 250","VPAR","XTR 0.01 0.01","","PACC","polar.txt","",
             *[f"ALFA {a:.2f}" for a in ALPHAS],"PACC","","QUIT",""]
        script="\n".join(cmd)
        (work/"xfoil.inp").write_text(script,encoding="ascii")
        run=subprocess.run([str(EXE)],input=script.encode(),stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,cwd=work,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        (work/"xfoil.log").write_bytes(run.stdout)
    data=[]
    for line in out.read_text(encoding="ascii").splitlines():
        try:
            row=list(map(float,line.split()))
        except ValueError:
            continue
        if len(row)==7:
            data.append(row)
    arr=np.array(data)
    if len(arr)<11 or abs(arr[0,0]-ALPHAS[0])>1e-7 or abs(arr[-1,0]-ALPHAS[-1])>1e-7 or np.max(np.diff(arr[:,0]))>.50001:
        raise RuntimeError(f"Insufficient converged polar coverage for delta {delta}, alpha={arr[:,0]}")
    missing=[float(a) for a in ALPHAS if not np.any(abs(arr[:,0]-a)<1e-7)]
    if missing:
        print(f"delta={delta}: interpolated across bounded interior nonconverged samples {missing}",flush=True)
    return np.column_stack([np.interp(ALPHAS,arr[:,0],arr[:,i]) for i in (1,2)])


def wave_harmonic(path, column, x=None):
    with path.open(newline="") as file:
        rows=[(float(r["time_s"]),float(r[column])) for r in csv.DictReader(file)
              if START<=float(r["time_s"])<END and (x is None or abs(float(r["x_m"])-x)<1e-7)]
    t,y=np.array(rows).T
    if len(t)<2700:
        raise RuntimeError("Incomplete WAVE/FIXED data")
    matrix=np.column_stack((np.ones(len(t)),np.cos(OMEGA*t),np.sin(OMEGA*t)))
    mean,cos,sin=np.linalg.lstsq(matrix,y,rcond=None)[0]
    return mean,complex(cos,-sin)


def solve_alpha(lift, drag, beta, scale, cl_target):
    cl=scale*(lift*np.cos(beta)+drag*np.sin(beta))
    cd=scale*(drag*np.cos(beta)-lift*np.sin(beta))
    if np.any(np.diff(cl)<=0) or not cl[0]<=cl_target<=cl[-1]:
        return math.nan,math.nan
    alpha=np.interp(cl_target,cl,ALPHAS)
    return alpha,float(np.interp(alpha,ALPHAS,cd))


def main():
    points,mesh_path=section()
    polars=np.array([polar(points,d) for d in DELTAS])
    fine=np.linspace(-1,1,201)
    p=np.array([[np.interp(fine,DELTAS,polars[:,i,j]) for j in (0,1)]
                for i in range(len(ALPHAS))]).transpose(2,0,1)
    _,ref=wave_harmonic(WAVE/"gauges.csv","eta_actual_m",-3)
    shift=np.exp(-1j*2*np.pi/10*(.952+1.19))*np.exp(-1j*np.angle(ref))
    cl_target,_=wave_harmonic(WAVE/"history.csv","CL")
    ux0,ux1=wave_harmonic(WAVE/"history.csv","Ux_theory")
    uy0,uy1=wave_harmonic(WAVE/"history.csv","Uy_theory")
    phase=np.arange(361)
    motion=[]
    for deg in phase:
        z=np.exp(1j*np.radians(deg))*shift
        ux,uy=ux0+(ux1*z).real,uy0+(uy1*z).real
        beta=math.atan2(uy,ux)
        beta_deg=math.degrees(beta)
        scale=(ux*ux+uy*uy)/18**2
        zero=len(fine)//2
        pitch,foil_cd=solve_alpha(p[zero,:,0],p[zero,:,1],beta,scale,cl_target)
        pitch-=beta_deg
        lift=np.array([np.interp(beta_deg,ALPHAS,row[:,0]) for row in p])
        drag=np.array([np.interp(beta_deg,ALPHAS,row[:,1]) for row in p])
        cl=scale*(lift*np.cos(beta)+drag*np.sin(beta))
        cd=scale*(drag*np.cos(beta)-lift*np.sin(beta))
        if np.any(np.diff(cl)<=0) or not cl[0]<=cl_target<=cl[-1] or not abs(pitch)<=1:
            raise RuntimeError(f"Single-actuator target unreachable or nonmonotone at {deg} deg")
        flap=np.interp(cl_target,cl,fine)
        flap_cd=np.interp(flap,fine,cd)
        pairs=[(foil_cd,pitch,0.0),(flap_cd,0.0,flap)]
        for delta,section_polar in zip(fine,p):
            alpha,cd=solve_alpha(section_polar[:,0],section_polar[:,1],beta,scale,cl_target)
            theta=alpha-beta_deg
            if math.isfinite(cd) and abs(theta)<=1:
                pairs.append((cd,theta,delta))
        cd2,pitch2,flap2=min(pairs)
        motion.append([deg,ux,uy,beta_deg,pitch,flap,foil_cd,flap_cd,pitch2,flap2,cd2])
    arr=np.array(motion)
    header="phase_deg,Ux_m_s,Uy_m_s,incident_angle_deg,foil_only_pitch_deg,flap_only_delta_deg,foil_only_CD_x,flap_only_CD_x,combined_pitch_deg,combined_delta_deg,combined_CD_x"
    np.savetxt(HERE/"XFOIL_PHASE_MAP.csv",arr,delimiter=",",header=header,comments="",fmt="%.10g")
    means=arr[:-1,[6,7,10]].mean(axis=0)
    report={"status":"QUASI_STEADY_DIAGNOSTIC","geometry_mesh":mesh_path,"reynolds":RE,
            "transition_xc":[.01,.01],"phase_origin":"Measured crest at x=-3 m, phase increases with time",
            "orbital_velocities":"STAR native wave probe at x=-1.19 m shifted to hinge x=0.952 m at fixed depth",
            "target_CL_vertical":cl_target,"pitch_limits_deg":[-1,1],"flap_limits_deg":[-1,1],
            "pitch_only_range_deg":[float(arr[:,4].min()),float(arr[:,4].max())],
            "flap_only_range_deg":[float(arr[:,5].min()),float(arr[:,5].max())],
            "mean_CD_x":{"foil_only":means[0],"flap_only":means[1],"combined":means[2]},
            "combined_vs_best_single_mean_pct":100*(means[2]/min(means[:2])-1),
            "foil_lower_drag_phase_samples":int(np.sum(arr[:-1,6]<arr[:-1,7])),
            "flap_lower_drag_phase_samples":int(np.sum(arr[:-1,7]<arr[:-1,6])),
            "max_uy_m_s":float(np.max(np.abs(arr[:,2]))),"actuator_work_evaluated":False}
    (HERE/"XFOIL_PHASE_MAP.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print(json.dumps(report,indent=2))
    plot_map(arr)


def plot_map(arr):
    width,height=940,780
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="#fff"/>',
         '<g fill="#22333e" font-family="Segoe UI, sans-serif">',
         '<text x="30" y="36" font-size="23" font-weight="600">XFOIL phase map | Equal vertical lift</text>',
         '<text x="30" y="61" font-size="14">NACA 66-012 MOD · sealed flap · U = 18 m/s · λ = 10 m · H = 0.10 m · quasi-steady screening</text>']
    colours=("#1a5c86","#a45416","#26745b","#823e76")
    groups=[
        ("Incident flow angle [deg]",[(arr[:,3],"Oscillatory flow angle")]),
        ("Actuator command [deg]",[(arr[:,4],"Foil-only pitch"),(arr[:,5],"Flap-only deflection"),
          (arr[:,8],"Combined pitch"),(arr[:,9],"Combined deflection")]),
        ("Axial drag ΔCD vs foil-only [×10⁻⁵]",[(np.zeros(len(arr)),"Foil only"),
          ((arr[:,7]-arr[:,6])*1e5,"Flap only"),((arr[:,10]-arr[:,6])*1e5,"Combined")])]
    for n,(title,series) in enumerate(groups):
        top=106+n*208
        left,right,bottom=90,908,top+131
        values=np.concatenate([v for v,_ in series])
        low,high=float(values.min()),float(values.max())
        margin=max(.02,(high-low)*.09)
        low,high=low-margin,high+margin
        x=lambda v: left+(right-left)*v/360
        y=lambda v: bottom-(bottom-top)*(v-low)/(high-low)
        svg.append(f'<text x="{left}" y="{top-14}" font-size="15" font-weight="600">{title}</text>')
        for i in range(5):
            v=low+(high-low)*i/4
            py=y(v)
            svg.append(f'<path d="M {left} {py:.1f} H {right}" stroke="#e4e9ed"/>')
            svg.append(f'<text x="{left-9}" y="{py+4:.1f}" text-anchor="end" font-size="12">{v:.2f}</text>')
        for phase in range(0,361,60):
            px=x(phase)
            svg.append(f'<path d="M {px:.1f} {top} V {bottom}" stroke="#edf0f2"/>')
            svg.append(f'<text x="{px:.1f}" y="{bottom+18}" text-anchor="middle" font-size="12">{phase}°</text>')
        for i,(series_y,label) in enumerate(series):
            pts=" ".join(f"{x(phase):.2f},{y(v):.2f}" for phase,v in zip(arr[:,0],series_y))
            colour=colours[i]
            dash=' stroke-dasharray="7 4"' if n==1 and i>=2 else ""
            svg.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2.1"{dash}/>')
            px=left+200*i
            svg.append(f'<path d="M {px} {bottom+39} h 22" stroke="{colour}" stroke-width="2"{dash}/>')
            svg.append(f'<text x="{px+29}" y="{bottom+43}" font-size="12">{label}</text>')
    svg.append('<text x="90" y="745" font-size="13">Wave phase increases with time. 0° is the measured crest at x = −3 m.</text>')
    svg.append('<text x="90" y="765" font-size="12" fill="#536571">Drag comparison excludes actuator work, structural loads and unsteady effects.</text></g></svg>')
    (HERE/"XFOIL_PHASE_MAP.svg").write_text("\n".join(svg),encoding="utf-8")

if __name__=="__main__":
    main()

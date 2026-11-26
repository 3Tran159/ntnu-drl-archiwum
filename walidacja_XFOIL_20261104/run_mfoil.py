# Independent MFOIL (Fidkowski 2023 Python, repackaged as pymfoil 0.1.0) check
# Solver numerical methods are unchanged. The shipped set_coords has a known
# Python indexing bug; directly install the verified TE-to-TE geometry.
import sys, json, traceback, pathlib, datetime, time
root = pathlib.Path(r"F:\ntnu\XFOIL_validation_20261104")
sys.path.insert(0, str(root / "pymfoil_src" / "install"))
sys.path.insert(0, r"C:\Users\ThinkPad\Documents\ChatGPT\ntnu science\mesh_study_20261030\.deps")
import numpy as np
from pymfoil import mfoil_notex as mf

coords = np.loadtxt(root / "foil_66_012_a08mod_f025.dat", skiprows=1)
print("Coordinates: ", coords.shape, "LEmin=", coords[:,0].min(), "TEmax=",coords[:,0].max(), flush=True)

def run(re, ncrit=9, npanel=159):
    t0=time.monotonic()
    m=mf.mfoil(naca='0012', npanel=npanel)
    # set original CAD coordinates, preserving surface and angle orientation
    xy = coords[::-1].copy()  # MFOIL needs lower-TE to upper-TE ordering
    # MFOIL 2023 build_wake assumes finite TE gap; original foil has exactly zero gap.
    # Introduce a 1e-5 chord numerical gap only at duplicated TE endpoints.
    xy[0,1] -= 0.000005
    xy[-1,1] += 0.000005
    m.geom.xpoint = xy.T.copy()
    m.geom.npoint = len(coords)
    m.geom.chord=float(np.ptp(coords[:,0]))
    m.geom.name='NACA66-012_a08mod_f025'
    mf.make_panels(m, npanel, None)
    m.param.doplot=False
    m.param.verb=1
    m.param.niglob=65
    m.param.rtol=1e-8
    m.param.ncrit=ncrit
    m.setoper(alpha=0, Re=float(re), Ma=0)
    m.solve()
    ans={"re":re,"alpha":0,"ncrit":ncrit,"npanel":npanel,"geom_chord":m.geom.chord,
         "conv":bool(m.glob.conv),"cl":float(m.post.cl),"cd":float(m.post.cd),
         "cdf":float(m.post.cdf),"cdp":float(m.post.cdp),
         "cm":float(m.post.cm),"elapsed_s":round(time.monotonic()-t0,2)}
    try:
        ans["residual_norm"]=float(np.linalg.norm(m.glob.R))
        ans["xtr"]=m.vsol.Xt.tolist() if hasattr(m.vsol.Xt,'tolist') else str(m.vsol.Xt)
    except Exception: pass
    print("RESULT",json.dumps(ans),flush=True)
    return ans

answers=[]
for re,ncrit,npanel in [(20000000,9,159),(20000000,1,159),(5000000,9,159)]:
    try:
        answers.append(run(re,ncrit,npanel))
    except Exception as e:
        print("ERROR",repr(e),flush=True)
        traceback.print_exc()
(root / "mfoil_results.json").write_text(json.dumps(answers,indent=2),encoding="utf-8")
print("DONE",flush=True)

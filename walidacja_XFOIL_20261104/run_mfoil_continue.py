# Continuation across Reynolds numbers using MFOIL/Fidkowski (Python 2023)
import sys,json,pathlib,time
root=pathlib.Path(r"F:\ntnu\XFOIL_validation_20261104")
sys.path.insert(0,str(root/"pymfoil_src"/"install"))
sys.path.insert(0,r"C:\Users\ThinkPad\Documents\ChatGPT\ntnu science\mesh_study_20261030\.deps")
import numpy as np
from pymfoil import mfoil_notex as mf
a=np.loadtxt(root/"foil_66_012_a08mod_f025.dat",skiprows=1)[::-1].copy()
a[0,1]-=5e-6;a[-1,1]+=5e-6
m=mf.mfoil(naca='0012',npanel=159)
m.geom.xpoint=a.T
m.geom.npoint=len(a)
m.geom.chord=float(np.ptp(a[:,0]))
m.geom.name='NACA66-012_a08mod_f025'
mf.make_panels(m,159,None)
m.param.doplot=False;m.param.verb=0;m.param.niglob=120;m.param.rtol=1e-8;m.param.ncrit=9
ans=[]
for re in [5e6,7.5e6,10e6,12.5e6,15e6,20e6]:
    m.setoper(alpha=0,Re=re,Ma=0)
    t=time.monotonic()
    try:
        m.solve()
        obj={"re":re,"conv":bool(m.glob.conv),"cl":float(m.post.cl),"cd":float(m.post.cd),"residual":float(np.linalg.norm(m.glob.R)),"seconds":round(time.monotonic()-t,2)}
        ans.append(obj)
        print("RESULT",json.dumps(obj),flush=True)
        if not m.glob.conv: break
        m.oper.initbl=False
    except Exception as e:
        print("ERROR",repr(e),flush=True)
        break
(root/"mfoil_continuation.json").write_text(json.dumps(ans,indent=2))

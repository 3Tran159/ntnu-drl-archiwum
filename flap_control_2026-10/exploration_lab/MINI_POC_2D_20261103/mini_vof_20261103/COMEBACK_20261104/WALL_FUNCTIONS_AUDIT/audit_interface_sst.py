from pathlib import Path
import json
import numpy as np

CB=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent

def fields(path):
    a=np.loadtxt(path,delimiter=",",skiprows=1)
    sy=2.02128173276777
    m=a[(a[:,-2]>sy-.4)&(a[:,-2]<sy+.4)]
    nx,ny=320,64
    ix=np.rint((m[:,-3]+12-.0625)/.125).astype(int)
    iy=np.rint((m[:,-2]-(sy-.4)-.00625)/.0125).astype(int)
    if len(m)!=nx*ny or len(set(zip(iy,ix)))!=nx*ny:raise ValueError("Unexpected interface corridor mesh")
    z=np.empty((ny,nx,m.shape[1]));z[iy,ix,:]=m
    surface=sy-.4+.0125*z[:,:,0].sum(axis=0)
    uv=z[:,:,3:5]
    ddy,ddx=np.gradient(uv,.0125,.125,axis=(0,1),edge_order=2)
    vort=ddx[:,:,1]-ddy[:,:,0]
    strain=np.sqrt(2*(ddx[:,:,0]**2+ddy[:,:,1]**2+.5*(ddx[:,:,1]+ddy[:,:,0])**2))
    groups={}
    for name,cond in (("air",z[:,:,0]<.01),("interface",(z[:,:,0]>=.01)&(z[:,:,0]<=.99)),("water",z[:,:,0]>.99)):
        if not cond.any():continue
        groups[name]=dict(cells=int(cond.sum()),k_min=float(z[:,:,6][cond].min()),k_max=float(z[:,:,6][cond].max()),
            omega_min=float(z[:,:,7][cond].min()),omega_max=float(z[:,:,7][cond].max()),mut_mu_max=float(z[:,:,8][cond].max()),
            abs_vorticity_s_inv_max=float(abs(vort[cond]).max()),strain_s_inv_max=float(strain[cond].max()))
    cap=[]
    for i,j in zip(*np.where(z[:,:,8]>=99999)):
        row=z[i,j]
        cap.append(dict(xyz_m=list(row[-3:]),relative_to_volume_integrated_interface_m=float(row[-2]-surface[j]),
           alpha_water=float(row[0]),k=float(row[6]),omega=float(row[7]),mu_ratio=float(row[8]),
           vorticity_z_s_inv=float(vort[i,j]),strain_s_inv=float(strain[i,j]),
           velocity_gradient=[[float(ddx[i,j,0]),float(ddy[i,j,0])],[float(ddx[i,j,1]),float(ddy[i,j,1])]]))
    return dict(groups=groups,capped_cells=cap,gradient_method="central finite differences on existing uniform quasi-2D corridor")

def main():
    dirs=[*sorted((CB/"runs").glob("STOKES_H050_COEX25*")),*sorted((CB/"runs").glob("SPRINT_A_RAMP40_CFL_SAFE*"))]
    results={}
    for d in dirs:
        results[d.name]={f:fields(d/f) for f in ("field_start.csv","field_end.csv")}
    (OUT/"INTERFACE_SST_AUDIT.json").write_text(json.dumps(results,indent=2),encoding="utf8")
    for d in results:
        print(d)
        for f, rec in results[d].items():
            print(f,rec["groups"])
            if rec["capped_cells"]:print("caps",len(rec["capped_cells"]),"first",rec["capped_cells"][0])

if __name__=="__main__":main()

